"""
Futures Trading Strategy

This strategy implements futures trading with leverage and position management.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from strategies.base_strategy import BaseStrategy
from exchange.api_client import MXCClient
from monitoring.metrics import MetricsManager
from strategies.indicators import Indicators
from config.settings import Settings


class FuturesStrategy(BaseStrategy):
    """
    Futures trading strategy with leverage and position management.
    """
    
    def __init__(self, exchange_client: MXCClient, metrics_manager: MetricsManager, 
                 settings: Settings):
        super().__init__("FuturesStrategy", {
            'profit_target': settings.scalp_profit_target,
            'stop_loss_pct': 0.05,  # 5% stop loss for futures
            'leverage': 10,  # Default leverage
            'max_position_size': settings.max_position_size,
            'risk_per_trade': settings.risk_per_trade
        })
        
        self.exchange_client = exchange_client
        self.metrics_manager = metrics_manager
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Futures specific variables
        self.leverage = 10
        self.position_mode = 'ONEWAY'  # ONEWAY or HEDGE
        self.active_positions = {}  # Track active futures positions
        self.trading_pairs = [settings.default_symbol]
        
        # Register callbacks for market data
        for pair in self.trading_pairs:
            self.exchange_client.register_market_callback(pair, self._on_market_update)
    
    async def analyze(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze market data for futures opportunities.
        This method is required by the BaseStrategy abstract class.
        """
        return None  # Implementation depends on specific futures signals
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the futures strategy."""
        return {
            'is_running': self.is_running,
            'leverage': self.leverage,
            'position_mode': self.position_mode,
            'active_positions_count': len(self.active_positions),
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
            
            # Check for futures trading opportunities based on current price
            if self.is_running and self.settings.trading_enabled:
                await self._check_futures_opportunities(symbol, price)
    
    async def _check_futures_opportunities(self, symbol: str, current_price: float):
        """Check for futures trading opportunities based on technical indicators."""
        try:
            # Get recent price data for analysis
            klines = await self.exchange_client.get_klines(
                symbol, 
                interval='1m',  # 1-minute candles for scalping
                limit=20
            )
            
            if not klines or len(klines) < 20:
                return
            
            # Convert kline data to more usable format
            closes = [float(k[4]) for k in klines]  # Close prices
            highs = [float(k[2]) for k in klines]   # High prices
            lows = [float(k[3]) for k in klines]    # Low prices
            
            # Calculate indicators using our Indicators class
            sma_20 = Indicators.simple_moving_average(closes, 20)
            rsi = Indicators.relative_strength_index(closes, 14)
            
            current_close = closes[-1]
            
            # Simple futures strategy logic
            # Long opportunity: price above SMA and RSI not overbought
            if current_close > sma_20 and rsi < 70:
                # Only enter if no active position or in different direction
                if not self._has_position(symbol, 'SHORT'):
                    await self._enter_position(symbol, 'LONG', current_price)
            
            # Short opportunity: price below SMA and RSI not oversold
            elif current_close < sma_20 and rsi > 30:
                # Only enter if no active position or in different direction
                if not self._has_position(symbol, 'LONG'):
                    await self._enter_position(symbol, 'SHORT', current_price)
            
        except Exception as e:
            self.logger.error(f"Error checking futures opportunities: {e}")
    
    def _has_position(self, symbol: str, side: str) -> bool:
        """Check if there's an active position for a symbol in a specific direction."""
        position_key = f"{symbol}_{side.upper()}"
        return position_key in self.active_positions
    
    async def _enter_position(self, symbol: str, side: str, entry_price: float):
        """Enter a futures position."""
        try:
            # Calculate position size based on risk management
            quantity = await self._calculate_position_size(symbol, entry_price)
            if quantity <= 0:
                self.logger.warning(f"Could not calculate valid position size for {symbol}")
                return
            
            # Set leverage for the symbol
            # Note: This is a simplified approach, in practice you might call an API to set leverage
            self.logger.info(f"Setting leverage for {symbol} to {self.leverage}x")
            
            # Place the futures order
            # Note: MXC futures API may have different endpoints
            order_result = await self.exchange_client.place_order(
                symbol=symbol,
                side='BUY' if side == 'LONG' else 'SELL',
                order_type='MARKET',
                quantity=quantity
            )
            
            if 'orderId' in order_result:
                # Track the position
                position_key = f"{symbol}_{side.upper()}"
                position_info = {
                    'order_id': order_result['orderId'],
                    'symbol': symbol,
                    'side': side,
                    'entry_price': entry_price,
                    'quantity': quantity,
                    'leverage': self.leverage,
                    'entry_time': datetime.now(),
                    'stop_loss': entry_price * (0.95 if side == 'LONG' else 1.05),  # 5% stop
                    'take_profit': entry_price * (1.02 if side == 'LONG' else 0.98)  # 2% target
                }
                
                self.active_positions[position_key] = position_info
                self.logger.info(f"Futures {side} position opened: {order_result['orderId']} at {entry_price}")
                
                # Start monitoring this position
                asyncio.create_task(self._monitor_position(position_key))
                
            else:
                self.logger.error(f"Failed to enter futures position: {order_result}")
                
        except Exception as e:
            self.logger.error(f"Error entering futures position: {e}")
    
    async def _monitor_position(self, position_key: str):
        """Monitor a futures position and manage stop loss/profit taking."""
        if position_key not in self.active_positions:
            return
        
        position = self.active_positions[position_key]
        symbol = position['symbol']
        side = position['side']
        entry_price = position['entry_price']
        stop_loss = position['stop_loss']
        take_profit = position['take_profit']
        
        try:
            # Get real-time price updates
            while position_key in self.active_positions:
                # In a real implementation, you'd get mark price for futures
                ticker = await self.exchange_client.get_ticker_24hr(symbol)
                current_price = float(ticker[0]['lastPrice']) if isinstance(ticker, list) else float(ticker['lastPrice'])
                
                # Check stop loss
                should_stop = (
                    (side == 'LONG' and current_price <= stop_loss) or
                    (side == 'SHORT' and current_price >= stop_loss)
                )
                
                # Check take profit
                should_take_profit = (
                    (side == 'LONG' and current_price >= take_profit) or
                    (side == 'SHORT' and current_price <= take_profit)
                )
                
                if should_stop or should_take_profit:
                    # Close position
                    close_side = 'SELL' if side == 'LONG' else 'BUY'
                    close_result = await self.exchange_client.place_order(
                        symbol=symbol,
                        side=close_side,
                        order_type='MARKET',
                        quantity=position['quantity']
                    )
                    
                    if 'orderId' in close_result:
                        self.logger.info(f"Futures position closed: {close_result['orderId']}")
                        
                        # Calculate profit
                        if side == 'LONG':
                            profit = (current_price - entry_price) * position['quantity'] * position['leverage']
                        else:  # SHORT
                            profit = (entry_price - current_price) * position['quantity'] * position['leverage']
                        
                        # Record metrics
                        self.metrics_manager.record_trade(symbol, profit, position['quantity'])
                        
                        # Remove from active positions
                        del self.active_positions[position_key]
                        break
                    else:
                        self.logger.error(f"Failed to close futures position: {close_result}")
                
                await asyncio.sleep(1)  # Check every second
                
        except Exception as e:
            self.logger.error(f"Error monitoring futures position {position_key}: {e}")
    
    async def _calculate_position_size(self, symbol: str, price: float) -> float:
        """
        Calculate position size for futures trading based on risk management rules.
        """
        try:
            # Get account balance
            balances = await self.exchange_client.get_balance()
            
            quote_balance = 0.0
            for balance in balances:
                if balance['asset'] == self.settings.quote_currency:
                    quote_balance = float(balance['free'])
                    break
            
            # For futures, risk is based on margin required
            risk_amount = quote_balance * self.settings.risk_per_trade
            
            # Calculate position size based on leverage
            max_size = min(
                self.settings.max_position_size,
                risk_amount / price  # Use risk amount to determine size
            )
            
            return max_size
            
        except Exception as e:
            self.logger.error(f"Error calculating futures position size: {e}")
            return 0.0
    
    def set_leverage(self, leverage: int):
        """Set the leverage for futures trading."""
        if 1 <= leverage <= 125:  # MXC futures leverage range
            self.leverage = leverage
            # Update the strategy's settings dictionary (inherited from BaseStrategy)
            if hasattr(self, 'settings_dict'):
                self.settings_dict['leverage'] = leverage
            else:
                # Initialize if not already set
                self.settings_dict = {'leverage': leverage}
            self.logger.info(f"Futures leverage set to {leverage}x")
        else:
            self.logger.error(f"Leverage must be between 1 and 125, got {leverage}")
    
    def set_trading_pairs(self, pairs: List[str]):
        """Set the trading pairs for futures strategy."""
        self.trading_pairs = pairs
        self.logger.info(f"Futures trading pairs set to: {pairs}")
    
    def start(self):
        """Start the futures strategy."""
        super().start()
        self.logger.info("Futures Strategy started")
    
    def stop(self):
        """Stop the futures strategy."""
        super().stop()
        self.logger.info("Futures Strategy stopped")