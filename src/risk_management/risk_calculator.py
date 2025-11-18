"""
Risk Management System

Implements risk controls and management for the scalping bot
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from src.exchange.api_client import MXCClient
from src.config.settings import Settings


class RiskManager:
    """
    Manages risk controls for the trading bot.
    """
    
    def __init__(self, exchange_client: MXCClient, settings: Settings):
        self.exchange_client = exchange_client
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Track trading statistics
        self.daily_pnl = 0.0
        self.daily_trades_count = 0
        self.consecutive_losses = 0
        self.daily_start_time = datetime.now()
        
        # Track positions and orders
        self.active_positions = {}
        self.daily_trade_history = []
        
    def reset_daily_stats(self):
        """Reset daily statistics at the start of a new day."""
        today = datetime.now().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        
        if datetime.now() - self.daily_start_time >= timedelta(days=1):
            self.daily_pnl = 0.0
            self.daily_trades_count = 0
            self.consecutive_losses = 0
            self.daily_trade_history = []
            self.daily_start_time = datetime.now()
            self.logger.info("Daily statistics reset")
    
    async def check_risk_limits(self, symbol: str, side: str, size: float, 
                               price: float) -> Dict[str, Any]:
        """
        Check if a trade violates any risk limits.
        
        Returns a dictionary with 'allowed' (bool) and 'reason' (str) if not allowed.
        """
        # Reset daily stats if needed
        self.reset_daily_stats()
        
        # Check daily loss limit
        if self.daily_pnl <= -abs(self.settings.max_daily_loss):
            return {
                'allowed': False,
                'reason': f"Daily loss limit exceeded: ${self.daily_pnl:.2f} <= -${self.settings.max_daily_loss}"
            }
        
        # Check consecutive losses
        if self.consecutive_losses >= self.settings.max_consecutive_losses:
            return {
                'allowed': False,
                'reason': f"Maximum consecutive losses reached: {self.consecutive_losses}"
            }
        
        # Check position size
        if size * price > self.settings.max_position_size:
            return {
                'allowed': False,
                'reason': f"Position size too large: ${size * price:.2f} > ${self.settings.max_position_size}"
            }
        
        # Check account balance
        try:
            balances = await self.exchange_client.get_balance()
            quote_balance = 0.0
            
            for balance in balances:
                if balance['asset'] == self.settings.quote_currency:
                    quote_balance = float(balance['free'])
                    break
            
            if quote_balance < (size * price):
                return {
                    'allowed': False,
                    'reason': f"Insufficient balance: ${quote_balance:.2f} < ${size * price:.2f}"
                }
        except Exception as e:
            self.logger.error(f"Error checking account balance: {e}")
            return {
                'allowed': False,
                'reason': f"Error checking balance: {str(e)}"
            }
        
        # All checks passed
        return {
            'allowed': True,
            'reason': 'All risk checks passed'
        }
    
    def record_trade(self, symbol: str, profit: float, size: float, price: float):
        """
        Record a trade in the risk management system.
        """
        trade_record = {
            'symbol': symbol,
            'profit': profit,
            'size': size,
            'price': price,
            'timestamp': datetime.now(),
        }
        
        self.daily_trade_history.append(trade_record)
        self.daily_pnl += profit
        self.daily_trades_count += 1
        
        # Update consecutive losses counter
        if profit < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        self.logger.info(
            f"Recorded trade: {symbol}, P&L: ${profit:.4f}, "
            f"Daily P&L: ${self.daily_pnl:.4f}, Consecutive losses: {self.consecutive_losses}"
        )
    
    def get_risk_status(self) -> Dict[str, Any]:
        """
        Get current risk management status.
        """
        return {
            'daily_pnl': self.daily_pnl,
            'daily_trades_count': self.daily_trades_count,
            'consecutive_losses': self.consecutive_losses,
            'max_daily_loss': self.settings.max_daily_loss,
            'max_consecutive_losses': self.settings.max_consecutive_losses,
            'position_size_limit': self.settings.max_position_size,
            'risk_per_trade': self.settings.risk_per_trade
        }
    
    def update_position(self, symbol: str, size: float, side: str, entry_price: float):
        """
        Update position tracking.
        """
        self.active_positions[symbol] = {
            'size': size,
            'side': side,
            'entry_price': entry_price,
            'current_value': size * entry_price,
            'timestamp': datetime.now()
        }
    
    def remove_position(self, symbol: str):
        """
        Remove a position when closed.
        """
        if symbol in self.active_positions:
            del self.active_positions[symbol]
    
    def get_total_position_value(self) -> float:
        """
        Get total value of all active positions.
        """
        total_value = 0.0
        for pos in self.active_positions.values():
            total_value += pos['current_value']
        return total_value