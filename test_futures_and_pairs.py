"""
Test suite for Futures Strategy and Pair Selection features
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
import asyncio

from src.strategies.futures_strategy import FuturesStrategy
from src.monitoring.metrics import MetricsManager
from src.config.settings import Settings


class TestFuturesStrategy:
    """Test the Futures Trading Strategy."""
    
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
        self.mock_client.register_market_callback = MagicMock()
        self.metrics_manager = MetricsManager()
        self.settings = Settings()
        
        # Set required settings
        self.settings.scalp_profit_target = 0.005
        self.settings.max_position_size = 10.0
        self.settings.risk_per_trade = 0.02
        self.settings.default_symbol = 'BTCUSDT'
        self.settings.quote_currency = 'USDT'
        self.settings.trading_enabled = False

    def test_futures_strategy_initialization(self):
        """Test that FuturesStrategy can be initialized properly."""
        strategy = FuturesStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        assert strategy is not None
        assert strategy.name == "FuturesStrategy"
        assert not strategy.is_running
        assert strategy.leverage == 10
        assert len(strategy.active_positions) == 0
        assert strategy.trading_pairs == ['BTCUSDT']

    def test_futures_strategy_start_stop(self):
        """Test starting and stopping the futures strategy."""
        strategy = FuturesStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        # Initially not running
        assert not strategy.is_running
        
        # Start the strategy
        strategy.start()
        assert strategy.is_running
        
        # Stop the strategy
        strategy.stop()
        assert not strategy.is_running

    def test_futures_strategy_status(self):
        """Test getting strategy status."""
        strategy = FuturesStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        status = strategy.get_status()
        
        assert 'is_running' in status
        assert 'leverage' in status
        assert 'position_mode' in status
        assert 'active_positions_count' in status
        assert 'trading_pairs' in status
        assert 'strategy_name' in status
        assert status['strategy_name'] == 'FuturesStrategy'

    def test_set_leverage(self):
        """Test setting leverage for futures strategy."""
        strategy = FuturesStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        # Test valid leverage
        strategy.set_leverage(20)
        assert strategy.leverage == 20
        
        # Test invalid leverage (too high)
        initial_leverage = strategy.leverage
        strategy.set_leverage(200)  # Above max of 125
        assert strategy.leverage == initial_leverage  # Should remain unchanged
        
        # Test invalid leverage (negative)
        strategy.set_leverage(-5)
        assert strategy.leverage == initial_leverage  # Should remain unchanged

    def test_set_trading_pairs(self):
        """Test setting trading pairs for futures strategy."""
        strategy = FuturesStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        # Test setting new pairs
        new_pairs = ['BTCUSDT', 'ETHUSDT']
        strategy.set_trading_pairs(new_pairs)
        
        assert strategy.trading_pairs == new_pairs

    @pytest.mark.asyncio
    async def test_futures_strategy_analyze(self):
        """Test the analyze method (required by base class)."""
        strategy = FuturesStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        result = await strategy.analyze({'price': 40000})
        # Should return None as implemented in the futures strategy
        assert result is None

    @pytest.mark.asyncio
    async def test_calculate_position_size(self):
        """Test futures position size calculation."""
        strategy = FuturesStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        # Mock balance
        self.mock_client.get_balance = AsyncMock(return_value=[
            {'asset': 'USDT', 'free': '1000.0', 'locked': '0.0'}
        ])
        
        position_size = await strategy._calculate_position_size('BTCUSDT', 40000.0)
        
        # Should calculate based on risk parameters
        assert isinstance(position_size, float)
        assert position_size >= 0

    @pytest.mark.asyncio
    async def test_has_position(self):
        """Test position checking functionality."""
        strategy = FuturesStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        # Initially should have no positions
        assert not strategy._has_position('BTCUSDT', 'LONG')
        assert not strategy._has_position('BTCUSDT', 'SHORT')
        
        # Add a mock position
        strategy.active_positions['BTCUSDT_LONG'] = {
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'entry_price': 40000.0,
            'quantity': 0.1
        }
        
        assert strategy._has_position('BTCUSDT', 'LONG')
        assert not strategy._has_position('BTCUSDT', 'SHORT')
        assert not strategy._has_position('ETHUSDT', 'LONG')


def test_pair_validation_logic():
    """Test the pair validation logic that would be used in the Telegram bot."""
    # This simulates the logic used in the _set_trading_pairs method
    pairs_str = "BTCUSDT,ETHUSDT"
    pairs = [pair.strip().upper() for pair in pairs_str.split(',')]
    assert pairs == ['BTCUSDT', 'ETHUSDT']
    
    # Test validation
    valid_pairs = []
    for pair in pairs:
        if len(pair) >= 6 and pair.endswith('USDT'):
            valid_pairs.append(pair)
    
    assert valid_pairs == ['BTCUSDT', 'ETHUSDT']
    
    # Test invalid pair
    invalid_pairs_str = "BTCTRY,ETHUSD"
    invalid_pairs = [pair.strip().upper() for pair in invalid_pairs_str.split(',')]
    valid_invalid_pairs = []
    for pair in invalid_pairs:
        if len(pair) >= 6 and pair.endswith('USDT'):
            valid_invalid_pairs.append(pair)
    
    assert valid_invalid_pairs == []  # No valid pairs


if __name__ == "__main__":
    pytest.main([__file__])