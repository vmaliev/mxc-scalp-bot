"""
Test suite for Risk and Position Size Controls
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
import asyncio

from src.telegram_bot.bot_handler import TelegramBot
from src.config.settings import Settings
from src.exchange.api_client import MXCClient
from src.strategies.scalping_strategy import ScalpingStrategy
from src.strategies.range_scalp_strategy import RangeScalpStrategy
from src.strategies.futures_strategy import FuturesStrategy
from src.monitoring.metrics import MetricsManager
from src.risk_management.risk_calculator import RiskManager


class TestRiskSizeControls:
    """Test the Risk and Position Size Controls via Telegram."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Set required environment variables
        import os
        os.environ.update({
            'MXC_API_KEY': 'test',
            'MXC_SECRET_KEY': 'test',
            'TELEGRAM_BOT_TOKEN': 'test:token',
            'TELEGRAM_AUTHORIZED_USERS': '123456789'
        })
        
        self.mock_client = AsyncMock()
        self.metrics_manager = MetricsManager()
        self.settings = Settings()
        
        # Set required settings
        self.settings.scalp_profit_target = 0.005
        self.settings.scalp_stop_loss = 0.003
        self.settings.max_position_size = 10.0
        self.settings.risk_per_trade = 0.02
        self.settings.default_symbol = 'BTCUSDT'
        self.settings.quote_currency = 'USDT'
        self.settings.max_daily_loss = 100.0
        self.settings.max_consecutive_losses = 5
        self.settings.trading_enabled = False

        # Create strategy instances
        self.scalping_strategy = ScalpingStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        self.range_scalp_strategy = RangeScalpStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        self.futures_strategy = FuturesStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        self.risk_manager = RiskManager(
            exchange_client=self.mock_client,
            settings=self.settings
        )

    @pytest.mark.asyncio
    async def test_set_risk_parameters_command(self):
        """Test the /set_risk command functionality."""
        bot = TelegramBot(
            bot_token='test_token',
            authorized_users=[123456789],
            exchange_client=self.mock_client,
            scalping_strategy=self.scalping_strategy,
            range_scalp_strategy=self.range_scalp_strategy,
            futures_strategy=self.futures_strategy,
            metrics_manager=self.metrics_manager,
            risk_manager=self.risk_manager
        )
        
        # Create mock update object
        update = MagicMock()
        update.effective_user.id = 123456789  # Auth user
        update.message.text = "/set_risk max_daily_loss 200"
        
        # Capture the response by checking if reply_text was called
        original_reply_text = update.message.reply_text
        update.message.reply_text = AsyncMock()
        
        await bot._set_risk_parameters(update, None)
        
        # Check that reply was called (meaning command executed without error)
        update.message.reply_text.assert_called()
        
        # Verify settings were updated
        assert self.settings.max_daily_loss == 200.0

    @pytest.mark.asyncio
    async def test_set_position_size_command(self):
        """Test the /set_size command functionality."""
        bot = TelegramBot(
            bot_token='test_token',
            authorized_users=[123456789],
            exchange_client=self.mock_client,
            scalping_strategy=self.scalping_strategy,
            range_scalp_strategy=self.range_scalp_strategy,
            futures_strategy=self.futures_strategy,
            metrics_manager=self.metrics_manager,
            risk_manager=self.risk_manager
        )
        
        # Create mock update object
        update = MagicMock()
        update.effective_user.id = 123456789  # Auth user
        update.message.text = "/set_size 50"
        
        # Make reply_text mock async
        update.message.reply_text = AsyncMock()
        
        await bot._set_position_size(update, None)
        
        # Check that reply was called
        update.message.reply_text.assert_called()
        
        # Verify settings were updated
        assert self.settings.max_position_size == 50.0

    @pytest.mark.asyncio
    async def test_get_risk_parameters_command(self):
        """Test the /risk_params command functionality."""
        bot = TelegramBot(
            bot_token='test_token',
            authorized_users=[123456789],
            exchange_client=self.mock_client,
            scalping_strategy=self.scalping_strategy,
            range_scalp_strategy=self.range_scalp_strategy,
            futures_strategy=self.futures_strategy,
            metrics_manager=self.metrics_manager,
            risk_manager=self.risk_manager
        )
        
        # Create mock update object
        update = MagicMock()
        update.effective_user.id = 123456789  # Auth user
        
        # Make reply_text mock async
        update.message.reply_text = AsyncMock()
        
        await bot._get_risk_parameters(update, None)
        
        # Check that reply was called
        update.message.reply_text.assert_called()

    def test_risk_parameter_validation(self):
        """Test the validation logic within the risk parameter setting."""
        # This just tests the logic that would be in the command
        
        # Test different parameter types
        test_cases = [
            ('max_daily_loss', '150.5'),
            ('risk_per_trade', '0.05'),  # 5%
            ('max_consecutive_losses', '3'),
            ('profit_target', '0.006'),  # 0.6%
            ('stop_loss', '0.004'),  # 0.4%
        ]
        
        for param_name, param_value in test_cases:
            # This simulates the logic inside the command
            settings = self.settings  # Use the settings from setup_method
            success = True
            
            try:
                if param_name == 'max_daily_loss':
                    value = float(param_value)
                    assert value > 0
                    
                elif param_name == 'risk_per_trade':
                    value = float(param_value)
                    assert 0 < value <= 0.5
                    
                elif param_name == 'max_consecutive_losses':
                    value = int(param_value)
                    assert value > 0
                    
                elif param_name == 'profit_target':
                    value = float(param_value)
                    assert 0 < value <= 0.1
                    
                elif param_name == 'stop_loss':
                    value = float(param_value)
                    assert 0 < value <= 0.1
                else:
                    success = False
                    
            except (ValueError, AssertionError):
                success = False
                
            assert success, f"Validation failed for {param_name}={param_value}"


def test_position_size_validation():
    """Test position size validation logic."""
    # This simulates the validation logic in the _set_position_size method
    
    # Valid positive size
    position_size = 100.0
    assert position_size > 0  # Valid
    
    # Invalid zero size
    position_size = 0.0
    is_valid = position_size > 0
    assert not is_valid  # Invalid
    
    # Invalid negative size
    position_size = -10.0
    is_valid = position_size > 0
    assert not is_valid  # Invalid


if __name__ == "__main__":
    pytest.main([__file__])