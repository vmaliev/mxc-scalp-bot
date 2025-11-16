"""
MXC Exchange API Client
Handles all communication with the MXC exchange API
"""
import hashlib
import hmac
import json
import time
import asyncio
import websockets
from typing import Dict, Any, Optional, Callable, List
import aiohttp
import logging


class MXCClient:
    """
    Client for interacting with MXC Exchange API (REST and WebSocket)
    """
    
    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://api.mexc.com"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.session = None
        self.websocket = None
        self.websocket_url = "wss://wbs-api.mexc.com/ws"
        self.logger = logging.getLogger(__name__)
        
        # Market data callbacks
        self.market_callbacks: Dict[str, List[Callable]] = {}
        
        # Rate limit tracking
        self.last_request_time = 0
        self.request_count = 0
        self.rate_limit_window = 10  # 10 seconds
        self.rate_limit_count = 500  # 500 requests per 10 seconds
        
        # WebSocket related
        self.websocket_task = None
        self.should_reconnect = True
    
    async def initialize_session(self):
        """Initialize aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    'X-MEXC-APIKEY': self.api_key,
                    'Content-Type': 'application/json'
                }
            )

    async def update_credentials(self, api_key: str = None, secret_key: str = None):
        """Update API credentials at runtime and reset HTTP session."""
        if api_key:
            self.api_key = api_key
        if secret_key:
            self.secret_key = secret_key

        if self.session:
            try:
                await self.session.close()
            finally:
                self.session = None
    
    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC SHA256 signature for API requests."""
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _rate_limit_check(self):
        """Check if we're within rate limits."""
        current_time = time.time()
        if current_time - self.last_request_time > self.rate_limit_window:
            # Reset window
            self.last_request_time = current_time
            self.request_count = 0
        else:
            if self.request_count >= self.rate_limit_count:
                # Wait to stay within limits
                time.sleep((self.rate_limit_window - (current_time - self.last_request_time)) + 0.1)
                self.last_request_time = time.time()
                self.request_count = 0
            self.request_count += 1
    
    async def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                           signed: bool = False) -> Dict[str, Any]:
        """Make HTTP request to MXC API."""
        await self.initialize_session()
        
        # Rate limit check
        self._rate_limit_check()
        
        url = f"{self.base_url}{endpoint}"
        
        if signed:
            if params is None:
                params = {}
            params['timestamp'] = int(time.time() * 1000)
            
            # Create query string for signature
            query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self._generate_signature(query_string)
            params['signature'] = signature

        log_params = {}
        if params:
            log_params = params.copy()
            # Never log signature
            log_params.pop('signature', None)
        self.logger.info(
            "MXC request %s %s | params=%s | signed=%s | api_key_set=%s",
            method,
            endpoint,
            log_params,
            signed,
            bool(self.api_key)
        )

        try:
            if method == 'GET':
                async with self.session.get(url, params=params) as response:
                    data = await response.json()
                    self.logger.info(
                        "MXC response %s %s | status=%s | body_preview=%s",
                        method,
                        endpoint,
                        response.status,
                        str(data)[:500]
                    )
                    return data
            elif method == 'POST':
                async with self.session.post(url, json=params) as response:
                    data = await response.json()
                    self.logger.info(
                        "MXC response %s %s | status=%s | body_preview=%s",
                        method,
                        endpoint,
                        response.status,
                        str(data)[:500]
                    )
                    return data
            elif method == 'DELETE':
                async with self.session.delete(url, params=params) as response:
                    data = await response.json()
                    self.logger.info(
                        "MXC response %s %s | status=%s | body_preview=%s",
                        method,
                        endpoint,
                        response.status,
                        str(data)[:500]
                    )
                    return data
        except Exception as e:
            self.logger.error(f"Error making request to {url}: {e}")
            raise
    
    # Account and Trading Methods
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information and balances."""
        return await self._make_request('GET', '/api/v3/account', signed=True)
    
    async def get_balance(self, asset: str = None) -> Dict[str, Any]:
        """Get specific asset balance or all balances."""
        account_info = await self.get_account_info()
        balances = account_info.get('balances', [])
        
        if asset:
            for balance in balances:
                if balance['asset'] == asset:
                    return balance
        
        return balances
    
    async def place_order(self, symbol: str, side: str, order_type: str, 
                         quantity: float = None, quote_order_qty: float = None, 
                         price: float = None, time_in_force: str = 'GTC') -> Dict[str, Any]:
        """Place an order on MXC."""
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper()
        }
        
        if quantity:
            params['quantity'] = str(quantity)
        if quote_order_qty:
            params['quoteOrderQty'] = str(quote_order_qty)
        if price:
            params['price'] = str(price)
        if time_in_force:
            params['timeInForce'] = time_in_force
        
        return await self._make_request('POST', '/api/v3/order', params, signed=True)
    
    async def cancel_order(self, symbol: str, order_id: str = None, 
                          orig_client_order_id: str = None) -> Dict[str, Any]:
        """Cancel an order."""
        params = {'symbol': symbol}
        if order_id:
            params['orderId'] = order_id
        if orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
        
        return await self._make_request('DELETE', '/api/v3/order', params, signed=True)
    
    async def get_open_orders(self, symbol: str = None) -> Dict[str, Any]:
        """Get open orders for a symbol or all symbols."""
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return await self._make_request('GET', '/api/v3/openOrders', params, signed=True)
    
    async def get_order(self, symbol: str, order_id: str = None, 
                       orig_client_order_id: str = None) -> Dict[str, Any]:
        """Get order status."""
        params = {'symbol': symbol}
        if order_id:
            params['orderId'] = order_id
        if orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
        
        return await self._make_request('GET', '/api/v3/order', params, signed=True)
    
    async def get_my_trades(self, symbol: str, limit: int = 500) -> Dict[str, Any]:
        """Get trade history for a symbol."""
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        return await self._make_request('GET', '/api/v3/myTrades', params, signed=True)
    
    # Market Data Methods
    async def get_klines(self, symbol: str, interval: str, limit: int = 500) -> Dict[str, Any]:
        """Get kline/candlestick data."""
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        return await self._make_request('GET', '/api/v3/klines', params)
    
    async def get_ticker_24hr(self, symbol: str = None) -> Dict[str, Any]:
        """Get 24hr ticker statistics."""
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return await self._make_request('GET', '/api/v3/ticker/24hr', params)
    
    async def get_depth(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get order book depth."""
        params = {
            'symbol': symbol,
            'limit': min(limit, 5000)  # MXC max is 5000
        }
        
        return await self._make_request('GET', '/api/v3/depth', params)
    
    # Account and Trading Related Methods
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information and balances."""
        try:
            # Ensure we have API credentials
            if not self.api_key or not self.secret_key:
                raise ValueError("API Key and Secret Key are required for authenticated requests")
            
            timestamp = int(time.time() * 1000)
            params_str = f"timestamp={timestamp}"
            signature = self._generate_signature(params_str)
            
            params = {
                'timestamp': timestamp,
                'signature': signature
            }
            
            return await self._make_request('GET', '/api/v3/account', params, signed=True)
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}")
            return {}

    async def get_balance(self) -> Dict[str, Any]:
        """Get account balances."""
        try:
            # Get account info and return just the balance portion
            account_info = await self.get_account_info()
            return account_info.get('balances', [])
        except Exception as e:
            self.logger.error(f"Error getting balance: {e}")
            return []

    async def get_open_orders(self, symbol: str = None) -> Dict[str, Any]:
        """Get open orders for all or specific symbol."""
        try:
            # Ensure we have API credentials
            if not self.api_key or not self.secret_key:
                raise ValueError("API Key and Secret Key are required for authenticated requests")
            
            timestamp = int(time.time() * 1000)
            params = {'timestamp': timestamp}
            if symbol:
                params['symbol'] = symbol

            # Construct the request string for signature
            params_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self._generate_signature(params_str)
            params['signature'] = signature

            return await self._make_request('GET', '/api/v3/openOrders', params, signed=True)
        except Exception as e:
            self.logger.error(f"Error getting open orders: {e}")
            return {}

    async def get_all_orders(self, symbol: str, limit: int = 500, start_time: int = None, end_time: int = None) -> Dict[str, Any]:
        """Get all orders (including completed/cancelled) for a symbol."""
        try:
            # Ensure we have API credentials
            if not self.api_key or not self.secret_key:
                raise ValueError("API Key and Secret Key are required for authenticated requests")
            
            timestamp = int(time.time() * 1000)
            
            params = {
                'timestamp': timestamp,
                'symbol': symbol,
                'limit': min(limit, 1000)  # Max 1000 orders
            }
            
            if start_time:
                params['startTime'] = start_time
            if end_time:
                params['endTime'] = end_time

            # Construct the request string for signature
            params_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self._generate_signature(params_str)
            params['signature'] = signature

            return await self._make_request('GET', '/api/v3/allOrders', params, signed=True)
        except Exception as e:
            self.logger.error(f"Error getting all orders: {e}")
            return {}

    async def get_my_trades(self, symbol: str, limit: int = 500) -> Dict[str, Any]:
        """Get user's trade history."""
        try:
            # Ensure we have API credentials
            if not self.api_key or not self.secret_key:
                raise ValueError("API Key and Secret Key are required for authenticated requests")
            
            timestamp = int(time.time() * 1000)
            
            params = {
                'timestamp': timestamp,
                'symbol': symbol,
                'limit': min(limit, 1000)  # Max 1000 trades
            }

            # Construct the request string for signature
            params_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self._generate_signature(params_str)
            params['signature'] = signature

            return await self._make_request('GET', '/api/v3/myTrades', params, signed=True)
        except Exception as e:
            self.logger.error(f"Error getting my trades: {e}")
            return {}

    async def get_position_info(self) -> Dict[str, Any]:
        """Get position information (for futures)."""
        try:
            # Note: MXC futures API might be different
            # This is for spot accounts - for futures, use futures-specific endpoints
            timestamp = int(time.time() * 1000)
            params = {'timestamp': timestamp}

            # Construct the request string for signature
            params_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self._generate_signature(params_str)
            params['signature'] = signature

            # For spot trading, we can get positions from account info
            account_info = await self._make_request('GET', '/api/v3/account', params, signed=True)
            
            # Extract position-like data from account (holdings)
            positions = []
            if 'balances' in account_info:
                for balance in account_info['balances']:
                    if float(balance['free']) + float(balance['locked']) > 0:
                        # This is simplified - in reality, position info comes from different endpoints
                        positions.append({
                            'asset': balance['asset'],
                            'free': balance['free'],
                            'locked': balance['locked']
                        })
            
            return {'positions': positions}
        except Exception as e:
            self.logger.error(f"Error getting position info: {e}")
            return {}

    async def get_open_orders(self, symbol: str = None) -> Dict[str, Any]:
        """Get open orders for all or specific symbol."""
        try:
            timestamp = int(time.time() * 1000)
            params = {'timestamp': timestamp}
            if symbol:
                params['symbol'] = symbol

            # Construct the request string for signature
            params_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self._generate_signature(params_str)
            params['signature'] = signature

            return await self._make_request('GET', '/api/v3/openOrders', params, signed=True)
        except Exception as e:
            self.logger.error(f"Error getting open orders: {e}")
            return {}

    async def get_all_orders(self, symbol: str, limit: int = 500, start_time: int = None, end_time: int = None) -> Dict[str, Any]:
        """Get all orders (including completed/cancelled) for a symbol."""
        try:
            timestamp = int(time.time() * 1000)
            
            params = {
                'timestamp': timestamp,
                'symbol': symbol,
                'limit': min(limit, 1000)  # Max 1000 orders
            }
            
            if start_time:
                params['startTime'] = start_time
            if end_time:
                params['endTime'] = end_time

            # Construct the request string for signature
            params_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self._generate_signature(params_str)
            params['signature'] = signature

            return await self._make_request('GET', '/api/v3/allOrders', params, signed=True)
        except Exception as e:
            self.logger.error(f"Error getting all orders: {e}")
            return {}

    async def get_my_trades(self, symbol: str, limit: int = 500) -> Dict[str, Any]:
        """Get user's trade history."""
        try:
            timestamp = int(time.time() * 1000)
            
            params = {
                'timestamp': timestamp,
                'symbol': symbol,
                'limit': min(limit, 1000)  # Max 1000 trades
            }

            # Construct the request string for signature
            params_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self._generate_signature(params_str)
            params['signature'] = signature

            return await self._make_request('GET', '/api/v3/myTrades', params, signed=True)
        except Exception as e:
            self.logger.error(f"Error getting my trades: {e}")
            return {}

    async def get_position_info(self) -> Dict[str, Any]:
        """Derive spot "positions" from account balances (fallback when futures API unavailable)."""
        try:
            account_info = await self.get_account_info()
            balances = account_info.get('balances', []) if account_info else []

            positions = []
            for balance in balances:
                try:
                    free = float(balance.get('free', 0))
                    locked = float(balance.get('locked', 0))
                except (TypeError, ValueError):
                    free = locked = 0.0

                total = free + locked
                if total > 0:
                    positions.append({
                        'asset': balance.get('asset'),
                        'free': balance.get('free'),
                        'locked': balance.get('locked'),
                        'total': total
                    })

            return {'positions': positions}
        except Exception as e:
            self.logger.error(f"Error getting position info: {e}")
            return {'positions': []}
    
    # WebSocket Methods
    async def start_websocket(self):
        """Start WebSocket connection for real-time market data."""
        self.should_reconnect = True
        self.websocket_task = asyncio.create_task(self._websocket_handler())
    
    async def stop_websocket(self):
        """Stop WebSocket connection."""
        self.should_reconnect = False
        if self.websocket:
            await self.websocket.close()
        if self.websocket_task:
            self.websocket_task.cancel()
    
    async def _websocket_handler(self):
        """Handle WebSocket connection and messages."""
        while self.should_reconnect:
            try:
                async with websockets.connect(self.websocket_url) as ws:
                    self.websocket = ws
                    self.logger.info("Connected to MXC WebSocket")
                    
                    # Subscribe to necessary streams
                    await self._subscribe_to_streams()
                    
                    # Listen for messages
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            await self._handle_websocket_message(data)
                        except json.JSONDecodeError:
                            self.logger.error(f"Invalid JSON received: {message}")
                        except Exception as e:
                            self.logger.error(f"Error handling websocket message: {e}")
            
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("WebSocket connection closed, reconnecting...")
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
            
            if self.should_reconnect:
                self.logger.info(f"Reconnecting in {5} seconds...")
                await asyncio.sleep(5)
    
    async def _subscribe_to_streams(self):
        """Subscribe to necessary WebSocket streams for scalping."""
        # Subscribe to ticker data for default symbol
        ticker_stream = f"spot@public.deals.v3.api.pb@10ms@BTCUSDT"  # 10ms updates for scalping
        subscribe_msg = {
            "method": "sub.public.deal",
            "param": {
                "symbol": "BTCUSDT",
                "limit": 1
            }
        }
        
        await self.websocket.send(json.dumps(subscribe_msg))
        self.logger.info(f"Subscribed to ticker stream: {ticker_stream}")
    
    async def _handle_websocket_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket messages."""
        # Example: process trade updates
        if 'channel' in data and 'data' in data:
            channel = data['channel']
            message_data = data['data']
            
            # Notify registered callbacks
            if channel in self.market_callbacks:
                for callback in self.market_callbacks[channel]:
                    try:
                        await callback(message_data)
                    except Exception as e:
                        self.logger.error(f"Error in market callback: {e}")
    
    def register_market_callback(self, symbol: str, callback: Callable):
        """Register a callback for market data updates."""
        channel = f"spot@public.deal@{symbol}"
        if channel not in self.market_callbacks:
            self.market_callbacks[channel] = []
        self.market_callbacks[channel].append(callback)
    
    async def close(self):
        """Close the API client."""
        if self.session:
            await self.session.close()
        await self.stop_websocket()