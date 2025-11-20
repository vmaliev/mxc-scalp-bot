"""
Test suite specifically for the Range Scalp Trading Strategy
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
import asyncio

from src.strategies.range_scalp_strategy import RangeScalpStrategy
from src.monitoring.metrics import MetricsManager
from src.config.settings import Settings


class TestRangeScalpStrategy:
    """Test the Range Scalp Trading Strategy."""
    
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

    def test_range_scalp_strategy_initialization(self):
        """Test that RangeScalpStrategy can be initialized properly."""
        strategy = RangeScalpStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        assert strategy is not None
        assert strategy.name == "RangeScalpStrategy"
        assert not strategy.is_running
        assert strategy.support_level is None
        assert strategy.resistance_level is None
        assert len(strategy.active_range_orders) == 0
        assert strategy.trading_pairs == ['BTCUSDT']

    def test_range_scalp_strategy_start_stop(self):
        """Test starting and stopping the range scalping strategy."""
        strategy = RangeScalpStrategy(
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

    def test_range_scalp_strategy_status(self):
        """Test getting strategy status."""
        strategy = RangeScalpStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        status = strategy.get_status()
        
        assert 'is_running' in status
        assert 'support_level' in status
        assert 'resistance_level' in status
        assert 'active_range_orders_count' in status
        assert 'trading_pairs' in status
        assert 'strategy_name' in status
        assert status['strategy_name'] == 'RangeScalpStrategy'

    @pytest.mark.asyncio
    async def test_range_scalp_strategy_analyze(self):
        """Test the analyze method (required by base class)."""
        strategy = RangeScalpStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        result = await strategy.analyze({'price': 40000})
        # Should return None as implemented in the range scalping strategy
        assert result is None

    @pytest.mark.asyncio
    async def test_update_support_resistance_levels(self):
        """Test updating support and resistance levels."""
        strategy = RangeScalpStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        # Mock klines response
        mock_klines = [
            [1634567890000, "40000.00", "40100.00", "39900.00", "40050.00", "10.00", 1634567891000, "400500.00", 50, "5.00", "200250.00", "0"],
            [1634567891000, "40050.00", "40150.00", "39950.00", "40100.00", "15.00", 1634567892000, "401000.00", 55, "5.50", "220275.00", "0"],
            [1634567892000, "40100.00", "40200.00", "40000.00", "40150.00", "20.00", 1634567893000, "401500.00", 60, "6.00", "240300.00", "0"],
        ] * 8  # Create 24 klines
        
        self.mock_client.get_klines = AsyncMock(return_value=mock_klines)
        
        # Update support and resistance levels
        await strategy._update_support_resistance_levels('BTCUSDT')
        
        # Check that support and resistance were updated
        assert strategy.support_level is not None
        assert strategy.resistance_level is not None
        assert strategy.resistance_level > strategy.support_level

    @pytest.mark.asyncio
    async def test_calculate_position_size(self):
        """Test position size calculation."""
        strategy = RangeScalpStrategy(
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
    async def test_on_market_update(self):
        """Test market update handling."""
        strategy = RangeScalpStrategy(
            exchange_client=self.mock_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        # Mock market data - this would normally come from the exchange
        market_data = [
            [1634567890000, "40000.00", "40100.00", "39900.00", "40050.00", "10.00", 1634567891000, "400500.00", 50, "5.00", "200250.00", "0"]
        ]
        
        # The strategy should handle the market update without errors
        await strategy._on_market_update(market_data)
        
        # The strategy should be able to process the update
        assert True  # If we reach here, no exception occurred


if __name__ == "__main__":
    pytest.main([__file__])