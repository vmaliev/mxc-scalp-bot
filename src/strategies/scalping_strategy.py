"""
Scalping Strategy Implementation

This strategy implements high-frequency trading for small profits
with tight stop losses, optimized for the MXC exchange.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from exchange.api_client import MXCClient
from exchange.order_manager import OrderManager
from monitoring.metrics import MetricsManager
from config.settings import Settings
from strategies.base_strategy import BaseStrategy
from strategies.indicators import Indicators


class ScalpingStrategy(BaseStrategy):
    """
    Implements a scalping strategy for high-frequency trading with small profits.
    """
    
    def __init__(self, exchange_client: MXCClient, metrics_manager: MetricsManager, 
                 settings: Settings):
        super().__init__("ScalpingStrategy", {
            'profit_target': settings.scalp_profit_target,
            'stop_loss': settings.scalp_stop_loss,
            'max_position_size': settings.max_position_size,
            'risk_per_trade': settings.risk_per_trade
        })
        
        self.exchange_client = exchange_client
        self.metrics_manager = metrics_manager
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        self.active_positions = {}
        self.trading_pairs = [settings.default_symbol]
        self.last_trade_time = {}
        
        # Register callbacks for market data
        for pair in self.trading_pairs:
            self.exchange_client.register_market_callback(pair, self._on_market_update)
    
    def start(self):
        """Start the scalping strategy."""
        self.is_running = True
        self.logger.info("Scalping strategy started")
        
    def stop(self):
        """Stop the scalping strategy."""
        self.is_running = False
        self.logger.info("Scalping strategy stopped")
    
    def _on_market_update(self, data: Dict[str, Any]):
        """Handle incoming market data updates."""
        # Process trade data from WebSocket
        if isinstance(data, list) and len(data) > 0:
            trade = data[0]  # Get the latest trade
            symbol = trade.get('symbol', self.settings.default_symbol)
            price = float(trade.get('price', 0))
            quantity = float(trade.get('quantity', 0))
            trade_time = int(trade.get('tradeTime', 0))
            
            # Analyze price action and decide if to trade
            if self.is_running and self.settings.trading_enabled:
                asyncio.create_task(self._analyze_and_trade(symbol, price, quantity, trade_time))
    
    async def _analyze_and_trade(self, symbol: str, price: float, quantity: float, 
                                trade_time: int):
        """Analyze market conditions and execute trades if conditions are met."""
        try:
            # Check if we can trade this symbol
            if symbol not in self.trading_pairs:
                return
            
            # Check if we've traded recently (to avoid over-trading)
            if symbol in self.last_trade_time:
                time_since_last = trade_time - self.last_trade_time[symbol]
                # Don't trade more than once every 2 seconds
                if time_since_last < 2000:
                    return
            
            # Calculate if there's a scalping opportunity
            opportunity = await self._find_scalping_opportunity(symbol, price)
            
            if opportunity:
                side, size, target_price, stop_price = opportunity
                await self._execute_trade(symbol, side, size, target_price, stop_price)
                self.last_trade_time[symbol] = trade_time
                
        except Exception as e:
            self.logger.error(f"Error in analysis and trading: {e}")
    
    async def _find_scalping_opportunity(self, symbol: str, current_price: float) -> Optional[tuple]:
        """
        Find scalping opportunities based on technical analysis.
        
        Returns: (side, size, target_price, stop_price) or None if no opportunity
        """
        try:
            # Get recent price data for analysis
            klines = await self.exchange_client.get_klines(
                symbol, 
                interval='1m',  # 1-minute candles for scalping
                limit=50  # Increased for more data points
            )
            
            if not klines or len(klines) < 20:
                return None
            
            # Convert kline data to more usable format
            closes = [float(k[4]) for k in klines]  # Close prices
            highs = [float(k[2]) for k in klines]   # High prices
            lows = [float(k[3]) for k in klines]    # Low prices
            
            # Calculate indicators using our Indicators class
            sma_20 = Indicators.simple_moving_average(closes, 20)
            sma_50 = Indicators.simple_moving_average(closes, 50)
            rsi = Indicators.relative_strength_index(closes, 14)
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = Indicators.bollinger_bands(closes, 20)
            
            # Momentum indicator
            momentum = Indicators.momentum(closes, 10)
            
            current_close = closes[-1]
            previous_close = closes[-2]
            
            # Look for price action signals
            is_bullish = (
                current_close > sma_20 and  # Price above short-term MA
                sma_20 > sma_50 and  # Short-term MA above long-term MA (golden cross)
                30 < rsi < 70 and  # RSI in normal range (not overbought/oversold)
                previous_close <= bb_middle and  # Previous close below middle band
                current_close > bb_middle  # Current close above middle band
            )
            
            is_bearish = (
                current_close < sma_20 and  # Price below short-term MA
                sma_20 < sma_50 and  # Short-term MA below long-term MA (death cross)
                30 < rsi < 70 and  # RSI in normal range
                previous_close >= bb_middle and  # Previous close above middle band
                current_close < bb_middle  # Current close below middle band
            )
            
            # Additional confirmation: momentum direction
            has_momentum = abs(momentum) > (sum(abs(closes[i] - closes[i-1]) for i in range(1, min(5, len(closes)))) / min(4, len(closes)-1)) * 0.5
            
            # Check for long opportunity
            if is_bullish and has_momentum and momentum > 0:
                # Calculate position size based on risk management
                size = await self._calculate_position_size(symbol, current_price)
                if size > 0:
                    target_price = current_price * (1 + self.settings.scalp_profit_target)
                    stop_price = current_price * (1 - self.settings.scalp_stop_loss)
                    self.logger.debug(f"Bullish signal detected for {symbol}: BUY at {current_price}, target {target_price}, stop {stop_price}")
                    return ('BUY', size, target_price, stop_price)
            
            # Check for short opportunity
            elif is_bearish and has_momentum and momentum < 0:
                # Calculate position size based on risk management
                size = await self._calculate_position_size(symbol, current_price)
                if size > 0:
                    target_price = current_price * (1 - self.settings.scalp_profit_target)
                    stop_price = current_price * (1 + self.settings.scalp_stop_loss)
                    self.logger.debug(f"Bearish signal detected for {symbol}: SELL at {current_price}, target {target_price}, stop {stop_price}")
                    return ('SELL', size, target_price, stop_price)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding scalping opportunity: {e}")
            return None
    
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
            
            # Ensure we have enough balance
            if quote_balance < max_size:
                max_size = min(quote_balance * 0.9, self.settings.max_position_size)
            
            # Calculate size in terms of quantity
            quantity = min(max_size / price, max_size)
            
            return quantity
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    async def _execute_trade(self, symbol: str, side: str, size: float, 
                           target_price: float, stop_price: float):
        """
        Execute a trade and set up stop loss/profit taking.
        """
        try:
            self.logger.info(f"Executing {side} trade for {symbol}, size: {size}, "
                           f"target: {target_price}, stop: {stop_price}")
            
            # Place the main trade order
            order_result = await self.exchange_client.place_order(
                symbol=symbol,
                side=side,
                order_type='LIMIT',
                quantity=size,
                price=target_price,
                time_in_force='GTC'
            )
            
            if 'orderId' in order_result:
                # Track this position for stop loss/profit taking
                position_info = {
                    'symbol': symbol,
                    'side': side,
                    'entry_price': target_price if side == 'BUY' else stop_price,
                    'size': size,
                    'target_price': target_price,
                    'stop_price': stop_price,
                    'order_id': order_result['orderId'],
                    'entry_time': datetime.now()
                }
                
                self.active_positions[order_result['orderId']] = position_info
                self.logger.info(f"Trade executed successfully: {order_result['orderId']}")
                
                # Start monitoring for stop loss/profit taking
                asyncio.create_task(self._monitor_position(order_result['orderId']))
            else:
                self.logger.error(f"Failed to execute trade: {order_result}")
                
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
    
    async def _monitor_position(self, order_id: str):
        """
        Monitor a position and execute stop loss/profit taking.
        """
        if order_id not in self.active_positions:
            return
        
        position = self.active_positions[order_id]
        symbol = position['symbol']
        side = position['side']
        target_price = position['target_price']
        stop_price = position['stop_price']
        
        try:
            # Get real-time price updates
            while order_id in self.active_positions:
                ticker = await self.exchange_client.get_ticker_24hr(symbol)
                current_price = float(ticker[0]['lastPrice']) if isinstance(ticker, list) else float(ticker['lastPrice'])
                
                # Check profit target
                should_take_profit = (
                    (side == 'BUY' and current_price >= target_price) or
                    (side == 'SELL' and current_price <= target_price)
                )
                
                # Check stop loss
                should_stop_loss = (
                    (side == 'BUY' and current_price <= stop_price) or
                    (side == 'SELL' and current_price >= stop_price)
                )
                
                if should_take_profit or should_stop_loss:
                    # Close position
                    close_side = 'SELL' if side == 'BUY' else 'BUY'
                    close_result = await self.exchange_client.place_order(
                        symbol=symbol,
                        side=close_side,
                        order_type='MARKET',
                        quantity=position['size']
                    )
                    
                    if 'orderId' in close_result:
                        self.logger.info(f"Position closed: {close_result['orderId']}")
                        
                        # Record metrics
                        profit = (
                            (current_price - position['entry_price']) * position['size'] 
                            if side == 'BUY' 
                            else (position['entry_price'] - current_price) * position['size']
                        )
                        
                        self.metrics_manager.record_trade(symbol, profit, position['size'])
                        
                        # Remove from active positions
                        del self.active_positions[order_id]
                        break
                    else:
                        self.logger.error(f"Failed to close position: {close_result}")
                
                await asyncio.sleep(1)  # Check every second
                
        except Exception as e:
            self.logger.error(f"Error monitoring position {order_id}: {e}")
    
    async def analyze(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze market data and return trading decision.
        This method is required by the BaseStrategy abstract class.
        For scalping, we have a separate _find_scalping_opportunity method that's used internally.
        """
        # This is a simplified implementation that can be extended
        # The actual scalping logic is implemented in _analyze_and_trade and _find_scalping_opportunity
        return None  # The scalping logic is handled in the internal methods

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the strategy."""
        return {
            'is_running': self.is_running,
            'active_positions_count': len(self.active_positions),
            'trading_pairs': self.trading_pairs,
            'last_trade_times': {k: v for k, v in self.last_trade_time.items()}
        }