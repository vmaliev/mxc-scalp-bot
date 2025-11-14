"""
Risk and Position Size Management Strategy

This demonstrates how risk and size controls can be integrated with strategies.
"""
from strategies.base_strategy import BaseStrategy
from exchange.api_client import MXCClient
from monitoring.metrics import MetricsManager
from config.settings import Settings


class RiskSizeControl:
    """
    Risk and position size control interface
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings

    def set_risk_parameters(self, max_daily_loss: float = None, 
                           risk_per_trade: float = None,
                           max_consecutive_losses: int = None,
                           scalp_profit_target: float = None,
                           scalp_stop_loss: float = None):
        """Set risk management parameters."""
        updates = {}
        
        if max_daily_loss is not None:
            self.settings.max_daily_loss = max_daily_loss
            updates['max_daily_loss'] = max_daily_loss
        
        if risk_per_trade is not None:
            self.settings.risk_per_trade = risk_per_trade
            updates['risk_per_trade'] = risk_per_trade
            
        if max_consecutive_losses is not None:
            self.settings.max_consecutive_losses = max_consecutive_losses
            updates['max_consecutive_losses'] = max_consecutive_losses
            
        if scalp_profit_target is not None:
            self.settings.scalp_profit_target = scalp_profit_target
            updates['scalp_profit_target'] = scalp_profit_target
            
        if scalp_stop_loss is not None:
            self.settings.scalp_stop_loss = scalp_stop_loss
            updates['scalp_stop_loss'] = scalp_stop_loss
            
        return updates

    def set_position_size(self, max_position_size: float = None):
        """Set position sizing parameters."""
        if max_position_size is not None:
            self.settings.max_position_size = max_position_size
            return {'max_position_size': max_position_size}
        
        return {}

    def get_current_risk_settings(self):
        """Get current risk management settings."""
        return {
            'max_daily_loss': self.settings.max_daily_loss,
            'risk_per_trade': self.settings.risk_per_trade,
            'max_consecutive_losses': self.settings.max_consecutive_losses,
            'scalp_profit_target': self.settings.scalp_profit_target,
            'scalp_stop_loss': self.settings.scalp_stop_loss,
            'max_position_size': self.settings.max_position_size
        }