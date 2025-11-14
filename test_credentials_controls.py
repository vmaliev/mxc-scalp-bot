"""
Test API credential controls
"""
import pytest
from unittest.mock import MagicMock


def test_web_controller_with_credentials():
    """Test the WebBotController with credential functionality."""
    from src.web.web_interface import WebBotController
    
    # Create mock components to pass to web controller
    mock_scalping_strategy = MagicMock()
    mock_range_strategy = MagicMock()
    mock_futures_strategy = MagicMock()
    mock_metrics = MagicMock()
    mock_risk = MagicMock()
    mock_settings = MagicMock()
    mock_client = MagicMock()
    
    # Set up mock settings attributes
    mock_settings.max_daily_loss = 100.0
    mock_settings.risk_per_trade = 0.02
    mock_settings.max_consecutive_losses = 5
    mock_settings.scalp_profit_target = 0.005
    mock_settings.scalp_stop_loss = 0.003
    mock_settings.max_position_size = 10.0
    mock_settings.api_key = ""
    mock_settings.secret_key = ""
    mock_settings.telegram_bot_token = ""
    mock_settings.telegram_authorized_users = []
    
    controller = WebBotController(
        scalping_strategy=mock_scalping_strategy,
        range_scalp_strategy=mock_range_strategy,
        futures_strategy=mock_futures_strategy,
        metrics_manager=mock_metrics,
        risk_manager=mock_risk,
        settings=mock_settings,
        mxc_client=mock_client
    )
    
    # Test the get_credentials_status method
    creds_status = controller.get_credentials_status()
    assert 'api_key_set' in creds_status
    assert 'secret_key_set' in creds_status
    assert 'bot_token_set' in creds_status
    assert 'authorized_users_count' in creds_status
    
    print("API Credential controls test passed!")


if __name__ == "__main__":
    test_web_controller_with_credentials()
    print("All credential control tests passed!")