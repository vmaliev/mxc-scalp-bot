"""
Base Strategy Class

Abstract base class for all trading strategies
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.
    All specific strategies should inherit from this class.
    """
    
    def __init__(self, name: str, settings: Dict[str, Any]):
        self.name = name
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
        self.is_running = False
    
    @abstractmethod
    async def analyze(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze market data and return trading decision.
        
        Returns: Dict with trade decision or None if no trade
        Example: {
            'action': 'BUY' or 'SELL',
            'symbol': 'BTCUSDT',
            'quantity': 0.01,
            'price': 40000.0,
            'target_price': 40100.0,
            'stop_price': 39900.0
        }
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get current strategy status.
        """
        pass
    
    def start(self):
        """Start the strategy."""
        self.is_running = True
        self.logger.info(f"Strategy {self.name} started")
    
    def stop(self):
        """Stop the strategy."""
        self.is_running = False
        self.logger.info(f"Strategy {self.name} stopped")
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """Update strategy settings."""
        self.settings.update(new_settings)
        self.logger.info(f"Strategy {self.name} settings updated")