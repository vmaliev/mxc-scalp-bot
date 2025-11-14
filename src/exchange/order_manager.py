"""
Order Manager for MXC Exchange

Manages the lifecycle of orders including placement, monitoring and cancellation
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from exchange.api_client import MXCClient


class OrderManager:
    """
    Manages the lifecycle of orders on MXC exchange
    """
    
    def __init__(self, exchange_client: MXCClient):
        self.client = exchange_client
        self.logger = logging.getLogger(__name__)
        
        # Track active orders
        self.active_orders: Dict[str, Dict[str, Any]] = {}
        
        # Rate limiting
        self.order_request_times = []
        self.max_orders_per_second = 5  # Conservative limit to avoid rate limiting
    
    async def place_order(self, symbol: str, side: str, order_type: str,
                         quantity: float = None, quote_order_qty: float = None,
                         price: float = None, time_in_force: str = 'GTC',
                         client_order_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Place an order on MXC exchange with rate limiting.
        """
        # Enforce rate limiting
        await self._enforce_rate_limit()
        
        try:
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': order_type
            }
            
            if quantity is not None:
                order_params['quantity'] = quantity
            if quote_order_qty is not None:
                order_params['quoteOrderQty'] = quote_order_qty
            if price is not None:
                order_params['price'] = price
            if time_in_force:
                order_params['timeInForce'] = time_in_force
            if client_order_id:
                order_params['newClientOrderId'] = client_order_id
            
            result = await self.client.place_order(**order_params)
            
            if 'orderId' in result:
                # Track the order
                order_info = {
                    'order_id': result['orderId'],
                    'symbol': symbol,
                    'side': side,
                    'type': order_type,
                    'quantity': quantity or quote_order_qty,
                    'price': price,
                    'status': result.get('status', 'NEW'),
                    'timestamp': datetime.now(),
                    'client_order_id': client_order_id
                }
                
                self.active_orders[result['orderId']] = order_info
                self.logger.info(f"Order placed: {result['orderId']} for {symbol}")
                
                return result
            else:
                self.logger.error(f"Failed to place order: {result}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None
    
    async def cancel_order(self, symbol: str, order_id: str = None,
                          orig_client_order_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Cancel an order on MXC exchange.
        """
        # Enforce rate limiting
        await self._enforce_rate_limit()
        
        try:
            result = await self.client.cancel_order(
                symbol=symbol,
                order_id=order_id,
                orig_client_order_id=orig_client_order_id
            )
            
            # Remove from active orders if successful
            if 'orderId' in result:
                order_id = result['orderId']
                if order_id in self.active_orders:
                    del self.active_orders[order_id]
                    self.logger.info(f"Order cancelled: {order_id}")
            
            return result
        except Exception as e:
            self.logger.error(f"Error cancelling order: {e}")
            return None
    
    async def get_order_status(self, symbol: str, order_id: str = None,
                              orig_client_order_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Get the status of an order.
        """
        try:
            result = await self.client.get_order(
                symbol=symbol,
                order_id=order_id,
                orig_client_order_id=orig_client_order_id
            )
            return result
        except Exception as e:
            self.logger.error(f"Error getting order status: {e}")
            return None
    
    async def get_open_orders(self, symbol: str = None) -> Optional[Dict[str, Any]]:
        """
        Get all open orders.
        """
        try:
            result = await self.client.get_open_orders(symbol)
            return result
        except Exception as e:
            self.logger.error(f"Error getting open orders: {e}")
            return None
    
    async def _enforce_rate_limit(self):
        """
        Enforce rate limiting for order-related API calls.
        """
        now = datetime.now()
        # Clean old requests (older than 1 second)
        self.order_request_times = [
            req_time for req_time in self.order_request_times
            if (now - req_time).total_seconds() < 1
        ]
        
        # If we're at the limit, wait
        if len(self.order_request_times) >= self.max_orders_per_second:
            sleep_time = 1.0 - (now - self.order_request_times[0]).total_seconds()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Add current request time
        self.order_request_times.append(now)
    
    def get_active_orders_count(self) -> int:
        """
        Get the count of active orders.
        """
        return len(self.active_orders)
    
    def get_active_orders(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active orders.
        """
        return self.active_orders.copy()
    
    async def refresh_active_orders(self):
        """
        Refresh status of all tracked active orders.
        """
        for order_id, order_info in list(self.active_orders.items()):
            try:
                status = await self.get_order_status(
                    symbol=order_info['symbol'],
                    order_id=order_id
                )
                
                if status:
                    # Update status
                    order_info['status'] = status.get('status', order_info['status'])
                    
                    # If order is no longer active, remove from tracking
                    if status.get('status') in ['FILLED', 'CANCELED', 'REJECTED', 'EXPIRED']:
                        del self.active_orders[order_id]
                        self.logger.info(f"Order {order_id} no longer active, removed from tracking")
            except Exception as e:
                self.logger.error(f"Error refreshing order {order_id}: {e}")
    
    async def cancel_all_orders(self, symbol: str = None):
        """
        Cancel all active orders for a symbol or all symbols.
        """
        orders_to_cancel = []
        
        for order_id, order_info in self.active_orders.items():
            if symbol is None or order_info['symbol'] == symbol:
                orders_to_cancel.append((order_info['symbol'], order_id))
        
        for symbol, order_id in orders_to_cancel:
            await self.cancel_order(symbol=symbol, order_id=order_id)