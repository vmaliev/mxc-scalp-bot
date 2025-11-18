"""
Range Scalping Strategy

This strategy implements range trading by placing orders at support (long) 
and resistance (short) levels based on 1-hour min/max values.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from src.strategies.base_strategy import BaseStrategy
from src.exchange.api_client import MXCClient
from src.monitoring.metrics import MetricsManager
from src.strategies.indicators import Indicators
from src.config.settings import Settings


class RangeScalpStrategy(BaseStrategy):
    """
    Range scalping strategy that places both long and short orders based on 
    1-hour min/max levels with 10% stop loss risk.
    """
    
    def __init__(self, exchange_client: MXCClient, metrics_manager: MetricsManager, 
                 settings: Settings):
        # Initialize with initial settings
        initial_settings = {
            'profit_target': settings.scalp_profit_target,
            'stop_loss_pct': 0.10,  # 10% stop loss
            'max_position_size': settings.max_position_size,
            'risk_per_trade': settings.risk_per_trade
        }
        
        super().__init__("RangeScalpStrategy", initial_settings)
        
        self.exchange_client = exchange_client
        self.metrics_manager = metrics_manager
        self.settings = settings  # This is the global Settings object
        self.logger = logging.getLogger(__name__)
        
        # Range scalping specific variables
        self.support_level = None
        self.resistance_level = None
        self.active_range_orders = {}  # Track range orders
        self.trading_pairs = [settings.default_symbol]
        
        # Register callbacks for market data
        for pair in self.trading_pairs:
            self.exchange_client.register_market_callback(pair, self._on_market_update)
    
    async def analyze(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze market data for range scalping opportunities.
        This method is required by the BaseStrategy abstract class.
        """
        # This will be used internally by the range scalping logic
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the range scalping strategy."""
        return {
            'is_running': self.is_running,
            'support_level': self.support_level,
            'resistance_level': self.resistance_level,
            'active_range_orders_count': len(self.active_range_orders),
            'trading_pairs': self.trading_pairs,
            'strategy_name': self.name
        }
    
    async def _on_market_update(self, data: Dict[str, Any]):
        """Handle incoming market data updates."""
        # Process trade data from WebSocket
        if isinstance(data, list) and len(data) > 0:
            trade = data[0]  # Get the latest trade
            if isinstance(trade, list) and len(trade) > 0:
                # Handle the common data format from MXC WebSocket
                if len(trade) >= 2:
                    symbol = self.settings.default_symbol  # Use default symbol
                    price = float(trade[1]) if isinstance(trade[1], (str, int, float)) else float(trade[0])
                else:
                    price = float(trade[0]) if isinstance(trade[0], (str, int, float)) else float(trade[1])
                    symbol = self.settings.default_symbol
            else:
                symbol = trade.get('symbol', self.settings.default_symbol)
                price = float(trade.get('price', 0))
            
            # Update support and resistance levels if needed
            await self._update_support_resistance_levels(symbol)
            
            # Check if we should place range orders based on current price
            if self.is_running and self.settings.trading_enabled:
                await self._check_range_scalp_opportunities(symbol, price)
    
    async def _update_support_resistance_levels(self, symbol: str):
        """Update support and resistance levels based on 1-hour min/max values."""
        try:
            # Get 1-hour klines for the last 24 hours to determine strong support/resistance
            klines = await self.exchange_client.get_klines(
                symbol, 
                interval='1h', 
                limit=24  # Last 24 hours of 1-hour candles
            )
            
            if not klines or len(klines) < 2:
                self.logger.warning(f"Not enough klines data to calculate support/resistance for {symbol}")
                return
            
            # Extract high and low prices
            highs = [float(k[2]) for k in klines]  # High prices
            lows = [float(k[3]) for k in klines]   # Low prices
            
            # Calculate support as the lowest low (rounded)
            support = min(lows)
            # Calculate resistance as the highest high (rounded) 
            resistance = max(highs)
            
            # Update levels if they've changed significantly
            if (self.support_level is None or 
                abs(support - self.support_level) / self.support_level > 0.005):  # 0.5% change
                self.logger.info(f"Updated support level for {symbol}: {support}")
                self.support_level = support
            
            if (self.resistance_level is None or 
                abs(resistance - self.resistance_level) / self.resistance_level > 0.005):  # 0.5% change
                self.logger.info(f"Updated resistance level for {symbol}: {resistance}")
                self.resistance_level = resistance
                
        except Exception as e:
            self.logger.error(f"Error updating support/resistance levels: {e}")
    
    async def _check_range_scalp_opportunities(self, symbol: str, current_price: float):
        """Check for opportunities to place range scalping orders at min/max levels."""
        if not self.support_level or not self.resistance_level:
            return
        
        try:
            # Check if price is approaching support or resistance
            # Allow for some buffer (e.g., 0.2% from levels)
            support_buffer = self.support_level * 0.002
            resistance_buffer = self.resistance_level * 0.002
            
            # Place long order if price is near support (but not too close to avoid whipsaw)
            if (self.support_level + support_buffer <= current_price <= 
                self.support_level + (support_buffer * 3)):  # Within 0.2% to 0.6% above support
                
                # Check if we already have a long order at this level
                long_order_key = f"{symbol}_long_at_support"
                if long_order_key not in self.active_range_orders:
                    await self._place_range_order(symbol, 'LONG', current_price)
            
            # Place short order if price is near resistance (but not too close to avoid whipsaw)
            elif (self.resistance_level - (resistance_buffer * 3) <= current_price <= 
                  self.resistance_level - resistance_buffer):  # Within 0.6% to 0.2% below resistance
                
                # Check if we already have a short order at this level
                short_order_key = f"{symbol}_short_at_resistance"
                if short_order_key not in self.active_range_orders:
                    await self._place_range_order(symbol, 'SHORT', current_price)
                    
        except Exception as e:
            self.logger.error(f"Error checking range scalping opportunities: {e}")
    
    async def _place_range_order(self, symbol: str, order_type: str, current_price: float):
        """Place a range scalping order at support or resistance level."""
        try:
            # Calculate position size based on risk management
            quantity = await self._calculate_position_size(symbol, current_price)
            if quantity <= 0:
                self.logger.warning(f"Could not calculate valid position size for {symbol}")
                return
            
            # Determine entry price and order direction based on type
            if order_type == 'LONG':
                # Place buy order slightly above support (for breakout confirmation)
                entry_price = self.support_level * 1.0005  # 0.05% above support
                side = 'BUY'
                # Calculate stop loss below support
                stop_price = self.support_level * (1 - self.strategy_settings['stop_loss_pct'])
                # Calculate take profit at a reasonable target
                target_price = entry_price * (1 + self.strategy_settings['profit_target'])
                
            elif order_type == 'SHORT':
                # Place sell order slightly below resistance (for breakdown confirmation)
                entry_price = self.resistance_level * 0.9995  # 0.05% below resistance
                side = 'SELL'
                # Calculate stop loss above resistance
                stop_price = self.resistance_level * (1 + self.strategy_settings['stop_loss_pct'])
                # Calculate take profit at a reasonable target
                target_price = entry_price * (1 - self.strategy_settings['profit_target'])
            else:
                self.logger.error(f"Invalid order type: {order_type}")
                return
            
            # Place the entry order
            order_result = await self.exchange_client.place_order(
                symbol=symbol,
                side=side,
                order_type='LIMIT',
                quantity=quantity,
                price=entry_price,
                time_in_force='GTC'  # Good till canceled
            )
            
            if 'orderId' in order_result:
                # Track the range order 
                order_key = f"{symbol}_{order_type.lower()}_at_{'support' if order_type == 'LONG' else 'resistance'}"
                
                order_info = {
                    'order_id': order_result['orderId'],
                    'symbol': symbol,
                    'order_type': order_type,
                    'side': side,
                    'entry_price': entry_price,
                    'quantity': quantity,
                    'stop_price': stop_price,
                    'target_price': target_price,
                    'placed_time': datetime.now()
                }
                
                self.active_range_orders[order_key] = order_info
                self.logger.info(f"Range {order_type} order placed: {order_result['orderId']} at {entry_price}")
                
                # Start monitoring this order
                asyncio.create_task(self._monitor_range_order(order_key))
                
            else:
                self.logger.error(f"Failed to place range {order_type} order: {order_result}")
                
        except Exception as e:
            self.logger.error(f"Error placing range order: {e}")
    
    async def _monitor_range_order(self, order_key: str):
        """Monitor a range order and manage stop loss/profit taking."""
        if order_key not in self.active_range_orders:
            return
        
        order_info = self.active_range_orders[order_key]
        symbol = order_info['symbol']
        order_type = order_info['order_type']
        entry_price = order_info['entry_price']
        quantity = order_info['quantity']
        stop_price = order_info['stop_price']
        target_price = order_info['target_price']
        
        try:
            # Wait for the order to fill
            filled = False
            while order_key in self.active_range_orders and not filled:
                order_status = await self.exchange_client.get_order(
                    symbol=symbol,
                    order_id=order_info['order_id']
                )
                
                if order_status and order_status.get('status') == 'FILLED':
                    filled = True
                    self.logger.info(f"Range order {order_info['order_id']} filled for {symbol}")
                    
                    # Now we need to place stop loss and take profit orders
                    await self._place_exit_orders(order_info)
                    
                elif order_status and order_status.get('status') in ['CANCELED', 'REJECTED', 'EXPIRED']:
                    self.logger.info(f"Range order {order_info['order_id']} status: {order_status.get('status')}")
                    # Remove the order from tracking if it's no longer active
                    if order_key in self.active_range_orders:
                        del self.active_range_orders[order_key]
                    return
                
                await asyncio.sleep(2)  # Check every 2 seconds
                
        except Exception as e:
            self.logger.error(f"Error monitoring range order {order_key}: {e}")
    
    async def _place_exit_orders(self, order_info: Dict[str, Any]):
        """Place stop loss and take profit orders after entry order is filled."""
        try:
            symbol = order_info['symbol']
            quantity = order_info['quantity']
            stop_price = order_info['stop_price']
            target_price = order_info['target_price']
            
            # Determine order sides based on the original order type
            if order_info['order_type'] == 'LONG':
                # For long positions, place stop loss sell and take profit sell orders
                stop_side = 'SELL'
                target_side = 'SELL'
            else:  # SHORT
                # For short positions, place stop loss buy and take profit buy orders
                stop_side = 'BUY'
                target_side = 'BUY'
            
            # Place stop loss order
            stop_order = await self.exchange_client.place_order(
                symbol=symbol,
                side=stop_side,
                order_type='STOP_LOSS',
                quantity=quantity,
                price=stop_price,
                stopPrice=stop_price
            )
            
            # Place take profit order
            profit_order = await self.exchange_client.place_order(
                symbol=symbol,
                side=target_side,
                order_type='TAKE_PROFIT',
                quantity=quantity,
                price=target_price,
                stopPrice=target_price
            )
            
            if 'orderId' in stop_order and 'orderId' in profit_order:
                self.logger.info(f"Exit orders placed for {symbol}: SL: {stop_order['orderId']}, TP: {profit_order['orderId']}")
            else:
                self.logger.error(f"Failed to place exit orders. SL: {stop_order}, TP: {profit_order}")
                
        except Exception as e:
            self.logger.error(f"Error placing exit orders: {e}")
    
    async def _calculate_position_size(self, symbol: str, price: float) -> float:
        """
        Calculate position size based on risk management rules.
        """
        try:
            # Get account balance
            balances = await self.exchange_client.get_balance()
            
            quote_balance = 0.0
            for balance in balances:
                if balance['asset'] == self.settings.quote_currency:
                    quote_balance = float(balance['free'])
                    break
            
            # Calculate position size based on risk per trade
            risk_amount = quote_balance * self.settings.risk_per_trade
            
            # Ensure position size doesn't exceed maximum
            max_size = min(
                self.settings.max_position_size,
                risk_amount  # Don't risk more than the calculated risk amount
            )
            
            # Calculate size in terms of quantity
            quantity = min(max_size / price, max_size)
            
            return quantity
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def start(self):
        """Start the range scalping strategy."""
        super().start()
        self.logger.info("Range Scalp Strategy started")
        
        # Support and resistance levels will be updated via market updates
        # Initialize support and resistance levels asynchronously if possible
        # But don't do it directly from the start() method to avoid asyncio issues
        # This will be handled in the strategy's operation
    
    def stop(self):
        """Stop the range scalping strategy."""
        super().stop()
        self.logger.info("Range Scalp Strategy stopped")