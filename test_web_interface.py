"""
Test to verify the web interface works
"""
import pytest
from src.web.web_interface import WebBotController
from unittest.mock import MagicMock


def test_web_controller_initialization():
    """Test that WebBotController can be initialized."""
    controller = WebBotController()
    assert controller is not None
    assert controller.app is not None
    

def test_web_controller_with_components():
    """Test WebBotController with mocked components."""
    # Create mock components to pass to web controller
    mock_scalping_strategy = MagicMock()
    mock_range_strategy = MagicMock()
    mock_futures_strategy = MagicMock()
    mock_metrics = MagicMock()
    mock_risk = MagicMock()
    mock_settings = MagicMock()
    mock_client = MagicMock()
    
    controller = WebBotController(
        scalping_strategy=mock_scalping_strategy,
        range_scalp_strategy=mock_range_strategy,
        futures_strategy=mock_futures_strategy,
        metrics_manager=mock_metrics,
        risk_manager=mock_risk,
        settings=mock_settings,
        mxc_client=mock_client
    )
    
    assert controller is not None
    assert controller.scalping_strategy == mock_scalping_strategy
    assert controller.range_scalp_strategy == mock_range_strategy
    assert controller.futures_strategy == mock_futures_strategy
    assert controller.metrics_manager == mock_metrics
    assert controller.risk_manager == mock_risk
    assert controller.settings == mock_settings
    assert controller.mxc_client == mock_client


def test_get_status_method():
    """Test the get_status method."""
    controller = WebBotController()
    status = controller.get_status()
    
    assert 'scalping_running' in status
    assert 'range_running' in status
    assert 'futures_running' in status
    assert 'trading_pairs' in status
    assert 'active_strategies' in status


def test_get_risk_parameters_method():
    """Test the get_risk_parameters method."""
    controller = WebBotController()
    params = controller.get_risk_parameters()
    
    # May return empty dict if settings is None, which is expected
    assert isinstance(params, dict)


if __name__ == "__main__":
    test_web_controller_initialization()
    test_web_controller_with_components()
    test_get_status_method()
    test_get_risk_parameters_method()
    print("All web interface tests passed!")