"""
Metrics and Performance Tracking

Tracks trading performance and metrics
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import deque
import statistics


class MetricsManager:
    """
    Manages metrics and performance tracking for the trading bot.
    """
    
    def __init__(self, max_trades_history: int = 1000):
        self.logger = logging.getLogger(__name__)
        
        # Trade tracking
        self.trade_history = deque(maxlen=max_trades_history)
        self.win_count = 0
        self.loss_count = 0
        
        # Performance metrics
        self.total_profit = 0.0
        self.total_trades = 0
        self.best_trade = float('-inf')
        self.worst_trade = float('inf')
        self.profit_history = deque(maxlen=max_trades_history)
        
        # Timing and performance
        self.start_time = datetime.now()
        self.trade_execution_times = deque(maxlen=100)  # Last 100 execution times
        
    def record_trade(self, symbol: str, profit: float, size: float, 
                     execution_time: float = None) -> None:
        """
        Record a completed trade.
        """
        trade_record = {
            'symbol': symbol,
            'profit': profit,
            'size': size,
            'timestamp': datetime.now().isoformat(),
            'execution_time': execution_time
        }
        
        self.trade_history.append(trade_record)
        self.total_trades += 1
        self.total_profit += profit
        self.profit_history.append(profit)
        
        # Update win/loss count
        if profit > 0:
            self.win_count += 1
        elif profit < 0:
            self.loss_count += 1
        
        # Update best and worst trades
        self.best_trade = max(self.best_trade, profit)
        self.worst_trade = min(self.worst_trade, profit)
        
        # Record execution time if provided
        if execution_time is not None:
            self.trade_execution_times.append(execution_time)
        
        self.logger.info(
            f"Trade recorded: {symbol}, P&L: {profit:+.4f}, "
            f"Total P&L: {self.total_profit:+.4f}, Total trades: {self.total_trades}"
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current trading statistics.
        """
        win_rate = self.win_count / max(self.total_trades, 1)
        
        # Calculate profit factor (gross profit / gross loss)
        gross_profit = sum(p for p in self.profit_history if p > 0)
        gross_loss = abs(sum(p for p in self.profit_history if p < 0))
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        
        # Calculate Sharpe ratio (simplified)
        if len(self.profit_history) > 1:
            returns_std = statistics.stdev(self.profit_history) if len(self.profit_history) > 1 else 0
            expected_return = statistics.mean(self.profit_history) if self.profit_history else 0
            sharpe_ratio = expected_return / returns_std if returns_std != 0 else 0
        else:
            sharpe_ratio = 0
        
        # Average trade execution time
        avg_execution_time = statistics.mean(self.trade_execution_times) if self.trade_execution_times else 0
        
        return {
            'total_profit': round(self.total_profit, 4),
            'total_trades': self.total_trades,
            'win_count': self.win_count,
            'loss_count': self.loss_count,
            'win_rate': win_rate,
            'best_trade': round(self.best_trade, 4) if self.best_trade != float('-inf') else 0,
            'worst_trade': round(self.worst_trade, 4) if self.worst_trade != float('inf') else 0,
            'profit_factor': round(profit_factor, 3),
            'sharpe_ratio': round(sharpe_ratio, 3),
            'avg_execution_time': round(avg_execution_time, 4),
            'uptime': str(datetime.now() - self.start_time),
            'win_loss_ratio': self.win_count / max(self.loss_count, 1)
        }
    
    def get_recent_trades(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent trades.
        """
        return list(self.trade_history)[-count:]
    
    def get_profit_by_symbol(self, symbol: str) -> float:
        """
        Get total profit for a specific symbol.
        """
        return sum(
            trade['profit'] 
            for trade in self.trade_history 
            if trade['symbol'] == symbol
        )
    
    def get_daily_performance(self) -> Dict[str, Any]:
        """
        Get performance for the current day.
        """
        today = datetime.now().date()
        today_trades = [
            trade for trade in self.trade_history
            if datetime.fromisoformat(trade['timestamp']).date() == today
        ]
        
        daily_profit = sum(trade['profit'] for trade in today_trades)
        daily_trades = len(today_trades)
        
        return {
            'daily_profit': round(daily_profit, 4),
            'daily_trades': daily_trades,
            'daily_win_rate': len([t for t in today_trades if t['profit'] > 0]) / max(daily_trades, 1)
        }
    
    def reset_metrics(self):
        """
        Reset all metrics (use with caution).
        """
        self.trade_history.clear()
        self.win_count = 0
        self.loss_count = 0
        self.total_profit = 0.0
        self.total_trades = 0
        self.best_trade = float('-inf')
        self.worst_trade = float('inf')
        self.profit_history.clear()
        self.trade_execution_times.clear()
        self.start_time = datetime.now()
        
        self.logger.info("Metrics reset")
    
    def get_performance_summary(self) -> str:
        """
        Get a formatted performance summary string.
        """
        stats = self.get_statistics()
        daily_stats = self.get_daily_performance()
        
        summary = (
            f"📊 *Performance Summary*\n\n"
            f"Total Profit: {stats['total_profit']:+.4f}\n"
            f"Total Trades: {stats['total_trades']}\n"
            f"Win Rate: {stats['win_rate']:.2%}\n"
            f"Best Trade: {stats['best_trade']:+.4f}\n"
            f"Worst Trade: {stats['worst_trade']:+.4f}\n"
            f"Profit Factor: {stats['profit_factor']:.2f}\n\n"
            f"Today's Profit: {daily_stats['daily_profit']:+.4f}\n"
            f"Today's Trades: {daily_stats['daily_trades']}\n"
            f"Uptime: {stats['uptime'][:10]}"
        )
        
        return summary