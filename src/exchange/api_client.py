"""
MXC Exchange API Client using CCXT
Handles all communication with the MXC exchange API
"""
import json
import asyncio
import websockets
from typing import Dict, Any, Optional, Callable, List
import logging
import ccxt.async_support as ccxt


class MXCClient:
    """
    Client for interacting with MXC Exchange API (REST via CCXT and WebSocket)
    """
    
    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://api.mexc.com"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
        
        # Initialize CCXT exchange
        self.exchange = ccxt.mexc({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })
        
        # WebSocket related
        self.websocket = None
        self.websocket_url = "wss://wbs-api.mexc.com/ws"
        self.websocket_task = None
        self.should_reconnect = True
        
        # Market data callbacks
        self.market_callbacks: Dict[str, List[Callable]] = {}
    
    async def update_credentials(self, api_key: str = None, secret_key: str = None):
        """Update API credentials at runtime."""
        if api_key:
            self.api_key = api_key
            self.exchange.apiKey = api_key
        if secret_key:
            self.secret_key = secret_key
            self.exchange.secret = secret_key
    
    # Account and Trading Methods (using CCXT)
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information and balances."""
        try:
            if not self.api_key or not self.secret_key:
                raise ValueError("API Key and Secret Key are required for authenticated requests")
            
            # CCXT's fetch_balance returns account info
            balance = await self.exchange.fetch_balance()
            
            self.logger.info(f"CCXT balance response keys: {list(balance.keys())}")
            self.logger.info(f"CCXT balance total: {balance.get('total', {})}")
            
            # Convert to MXC API format for compatibility
            balances = []
            for currency, amounts in balance.items():
                if currency not in ['info', 'free', 'used', 'total', 'debt', 'timestamp', 'datetime']:
                    # Include all currencies, even with zero balance
                    balances.append({
                        'asset': currency,
                        'free': str(amounts.get('free', 0)),
                        'locked': str(amounts.get('used', 0))
                    })
            
            self.logger.info(f"Converted {len(balances)} balance entries")
            
            return {
                'balances': balances,
                'canTrade': True,
                'canWithdraw': True,
                'canDeposit': True
            }
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}")
            self.logger.exception("Full exception:")
            return {'code': getattr(e, 'code', 'ERROR'), 'msg': str(e)}
    
    async def get_balance(self) -> List[Dict[str, Any]]:
        """Get account balances."""
        try:
            account_info = await self.get_account_info()
            balances = account_info.get('balances', [])
            self.logger.info(f"Returning {len(balances)} balances to web interface")
            return balances
        except Exception as e:
            self.logger.error(f"Error getting balance: {e}")
            return []
    
    async def place_order(self, symbol: str, side: str, order_type: str, 
                         quantity: float = None, quote_order_qty: float = None, 
                         price: float = None, time_in_force: str = 'GTC') -> Dict[str, Any]:
        """Place an order on MXC."""
        try:
            # CCXT unified API
            params = {}
            if time_in_force:
                params['timeInForce'] = time_in_force
            if quote_order_qty:
                params['quoteOrderQty'] = quote_order_qty
            
            order = await self.exchange.create_order(
                symbol=symbol,
                type=order_type.lower(),
                side=side.lower(),
                amount=quantity,
                price=price,
                params=params
            )
            return order
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return {'code': getattr(e, 'code', 'ERROR'), 'msg': str(e)}
    
    async def cancel_order(self, symbol: str, order_id: str = None, 
                          orig_client_order_id: str = None) -> Dict[str, Any]:
        """Cancel an order."""
        try:
            order = await self.exchange.cancel_order(order_id, symbol)
            return order
        except Exception as e:
            self.logger.error(f"Error cancelling order: {e}")
            return {'code': getattr(e, 'code', 'ERROR'), 'msg': str(e)}
    
    async def get_open_orders(self, symbol: str = None) -> Dict[str, Any]:
        """Get open orders for a symbol or all symbols."""
        try:
            if not self.api_key or not self.secret_key:
                raise ValueError("API Key and Secret Key are required for authenticated requests")
            
            orders = await self.exchange.fetch_open_orders(symbol)
            return orders if isinstance(orders, list) else []
        except Exception as e:
            self.logger.error(f"Error getting open orders: {e}")
            return {'code': getattr(e, 'code', 'ERROR'), 'msg': str(e)}
    
    async def get_order(self, symbol: str, order_id: str = None, 
                       orig_client_order_id: str = None) -> Dict[str, Any]:
        """Get order status."""
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            self.logger.error(f"Error getting order: {e}")
            return {'code': getattr(e, 'code', 'ERROR'), 'msg': str(e)}
    
    async def get_my_trades(self, symbol: str, limit: int = 500) -> Dict[str, Any]:
        """Get trade history for a symbol."""
        try:
            if not self.api_key or not self.secret_key:
                raise ValueError("API Key and Secret Key are required for authenticated requests")
            
            trades = await self.exchange.fetch_my_trades(symbol, limit=limit)
            return trades if isinstance(trades, list) else []
        except Exception as e:
            self.logger.error(f"Error getting my trades: {e}")
            return {'code': getattr(e, 'code', 'ERROR'), 'msg': str(e)}
    
    async def get_all_orders(self, symbol: str, limit: int = 500, start_time: int = None, end_time: int = None) -> Dict[str, Any]:
        """Get all orders (including completed/cancelled) for a symbol."""
        try:
            params = {}
            if start_time:
                params['startTime'] = start_time
            if end_time:
                params['endTime'] = end_time
            
            orders = await self.exchange.fetch_orders(symbol, limit=limit, params=params)
            return orders if isinstance(orders, list) else []
        except Exception as e:
            self.logger.error(f"Error getting all orders: {e}")
            return {'code': getattr(e, 'code', 'ERROR'), 'msg': str(e)}
    
    async def get_position_info(self) -> Dict[str, Any]:
        """Derive spot 'positions' from account balances."""
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
    
    # Market Data Methods
    async def get_klines(self, symbol: str, interval: str, limit: int = 500) -> Dict[str, Any]:
        """Get kline/candlestick data."""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, interval, limit=limit)
            return ohlcv
        except Exception as e:
            self.logger.error(f"Error getting klines: {e}")
            return []
    
    async def get_ticker_24hr(self, symbol: str = None) -> Dict[str, Any]:
        """Get 24hr ticker statistics."""
        try:
            if symbol:
                ticker = await self.exchange.fetch_ticker(symbol)
                return ticker
            else:
                tickers = await self.exchange.fetch_tickers()
                return tickers
        except Exception as e:
            self.logger.error(f"Error getting ticker: {e}")
            return {}
    
    async def get_depth(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get order book depth."""
        try:
            orderbook = await self.exchange.fetch_order_book(symbol, limit=limit)
            return orderbook
        except Exception as e:
            self.logger.error(f"Error getting depth: {e}")
            return {}
    
    # Helper method for web interface
    async def _make_request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Dict[str, Any]:
        """
        Compatibility method for existing code that uses _make_request.
        Maps to appropriate CCXT methods.
        """
        # This is a compatibility shim - CCXT handles requests internally
        if endpoint == '/api/v3/time':
            # Server time request
            try:
                time = await self.exchange.fetch_time()
                return {'serverTime': time}
            except Exception as e:
                return {'code': 'ERROR', 'msg': str(e)}
        
        # For other endpoints, return a note that CCXT is being used
        return {'note': 'Using CCXT unified API'}
    
    # WebSocket Methods (kept from original implementation)
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
                self.logger.info(f"Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
    
    async def _subscribe_to_streams(self):
        """Subscribe to necessary WebSocket streams for scalping."""
        ticker_stream = f"spot@public.deals.v3.api.pb@10ms@BTCUSDT"
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
        await self.exchange.close()
        await self.stop_websocket()