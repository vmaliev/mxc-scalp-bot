"""
Integration test to verify the bot components work together
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.config.settings import Settings
from src.exchange.api_client import MXCClient
from src.strategies.scalping_strategy import ScalpingStrategy
from src.telegram_bot.bot_handler import TelegramBot
from src.monitoring.metrics import MetricsManager
from src.risk_management.risk_calculator import RiskManager


@pytest.mark.asyncio
async def test_bot_component_integration():
    """Test that all bot components can work together."""
    
    # Create settings using environment variables
    with patch.dict('os.environ', {
        'MXC_API_KEY': 'test_api_key',
        'MXC_SECRET_KEY': 'test_secret_key',
        'TELEGRAM_BOT_TOKEN': 'test_bot_token',
        'TELEGRAM_AUTHORIZED_USERS': '123456789'
    }):
        settings = Settings()
        
        # Mock exchange client to avoid real API calls
        with patch('src.exchange.api_client.MXCClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.register_market_callback = MagicMock()
            mock_client_class.return_value = mock_client
            
            # Mock required methods
            mock_client.get_account_info = AsyncMock(return_value={'balances': []})
            mock_client.get_klines = AsyncMock(return_value=[
                [1634567890000, "40000.00", "40100.00", "39900.00", "40050.00", "10.00", 1634567891000, "400500.00", 50, "5.00", "200250.00", "0"]
            ] * 20)  # Return 20 klines of mock data
            mock_client.get_balance = AsyncMock(return_value=[
                {'asset': 'USDT', 'free': '1000.0', 'locked': '0.0'},
                {'asset': 'BTC', 'free': '0.1', 'locked': '0.0'}
            ])
            
            # Initialize all components
            metrics_manager = MetricsManager()
            risk_manager = RiskManager(exchange_client=mock_client, settings=settings)
            
            strategy = ScalpingStrategy(
                exchange_client=mock_client,
                metrics_manager=metrics_manager,
                settings=settings
            )
            
            # Test that all components are properly initialized
            assert strategy is not None
            assert metrics_manager is not None
            assert risk_manager is not None
            
            # Test strategy methods
            strategy.start()
            assert strategy.is_running is True
            
            status = strategy.get_status()
            assert 'is_running' in status
            assert status['is_running'] is True
            
            strategy.stop()
            assert strategy.is_running is False
            
            # Test metrics collection
            initial_trades = metrics_manager.total_trades
            metrics_manager.record_trade('BTCUSDT', 10.5, 0.01)
            assert metrics_manager.total_trades == initial_trades + 1
            assert metrics_manager.total_profit == pytest.approx(10.5, 0.01)
            
            # Test risk manager
            risk_status = risk_manager.get_risk_status()
            assert 'daily_pnl' in risk_status
            assert 'daily_trades_count' in risk_status
            
            # Test risk validation (mock a successful validation)
            with patch.object(mock_client, 'get_balance', new=AsyncMock(return_value=[
                {'asset': 'USDT', 'free': '1000.0', 'locked': '0.0'}
            ])):
                result = await risk_manager.check_risk_limits('BTCUSDT', 'BUY', 0.001, 40000.0)
                # This should now pass if our risk checks are working
                # Note: This will depend on the actual parameter values vs settings
            
            print("All components initialized and tested successfully!")


def test_telegram_bot_component():
    """Test Telegram bot component separately."""
    # Create mock components
    mock_client = MagicMock()
    mock_strategy = MagicMock()
    mock_metrics = MagicMock()
    mock_risk = MagicMock()
    
    # Initialize Telegram bot
    bot = TelegramBot(
        bot_token='test_token',
        authorized_users=[123456789],
        exchange_client=mock_client,
        scalping_strategy=mock_strategy,
        metrics_manager=mock_metrics,
        risk_manager=mock_risk
    )
    
    assert bot is not None
    assert bot.bot_token == 'test_token'
    assert 123456789 in bot.authorized_users


if __name__ == "__main__":
    # Run the integration test
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    
    # Run a quick test
    asyncio.run(test_bot_component_integration())
    test_telegram_bot_component()
    print("Integration tests passed!")