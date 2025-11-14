"""
Validation utilities for the MXC Scalp Trading Bot
"""
from typing import Union, Dict, Any
import re


def validate_api_key(api_key: str) -> bool:
    """Validate MXC API key format."""
    if not api_key or not isinstance(api_key, str):
        return False
    
    # MXC API keys are typically long alphanumeric strings
    # Common format is 32 or 64 characters with mixed case
    return len(api_key) >= 20 and api_key.replace('_', '').replace('-', '').isalnum()


def validate_secret_key(secret_key: str) -> bool:
    """Validate MXC secret key format."""
    if not secret_key or not isinstance(secret_key, str):
        return False
    
    # MXC secret keys are typically long alphanumeric strings with possible special characters
    return len(secret_key) >= 30


def validate_telegram_token(token: str) -> bool:
    """Validate Telegram bot token format."""
    if not token or not isinstance(token, str):
        return False
    
    # Telegram tokens follow the format: digits:letters (e.g., 123456789:ABCdefGhIjKlmnopqr)
    pattern = r'^\d+:[\w-]+$'
    return bool(re.match(pattern, token))


def validate_risk_parameters(settings: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate risk management parameters.
    
    Returns a dictionary of validation errors.
    """
    errors = {}
    
    try:
        # Profit target validation
        profit_target = float(settings.get('scalp_profit_target', 0))
        if profit_target <= 0 or profit_target > 0.1:  # Max 10% target
            errors['scalp_profit_target'] = "Profit target must be between 0 and 0.1 (0% to 10%)"
    except (ValueError, TypeError):
        errors['scalp_profit_target'] = "Profit target must be a valid number"
    
    try:
        # Stop loss validation
        stop_loss = float(settings.get('scalp_stop_loss', 0))
        if stop_loss <= 0 or stop_loss > 0.1:  # Max 10% stop
            errors['scalp_stop_loss'] = "Stop loss must be between 0 and 0.1 (0% to 10%)"
    except (ValueError, TypeError):
        errors['scalp_stop_loss'] = "Stop loss must be a valid number"
    
    try:
        # Position size validation
        max_position_size = float(settings.get('max_position_size', 0))
        if max_position_size <= 0:
            errors['max_position_size'] = "Max position size must be positive"
    except (ValueError, TypeError):
        errors['max_position_size'] = "Max position size must be a valid number"
    
    try:
        # Daily loss validation
        max_daily_loss = float(settings.get('max_daily_loss', 0))
        if max_daily_loss <= 0:
            errors['max_daily_loss'] = "Max daily loss must be positive"
    except (ValueError, TypeError):
        errors['max_daily_loss'] = "Max daily loss must be a valid number"
    
    try:
        # Risk per trade validation
        risk_per_trade = float(settings.get('risk_per_trade', 0))
        if risk_per_trade <= 0 or risk_per_trade > 0.5:  # Max 50% risk
            errors['risk_per_trade'] = "Risk per trade must be between 0 and 0.5 (0% to 50%)"
    except (ValueError, TypeError):
        errors['risk_per_trade'] = "Risk per trade must be a valid number"
    
    return errors


def validate_trade_parameters(symbol: str, side: str, quantity: float, price: float) -> Dict[str, str]:
    """
    Validate trade parameters before execution.
    
    Returns a dictionary of validation errors.
    """
    errors = {}
    
    # Symbol validation
    if not isinstance(symbol, str) or len(symbol) < 6:
        errors['symbol'] = "Invalid symbol format"
    elif not re.match(r'^[A-Z]+[A-Z]+$', symbol):
        errors['symbol'] = "Symbol must be in format like BTCUSDT"
    
    # Side validation
    if side.upper() not in ['BUY', 'SELL']:
        errors['side'] = "Side must be either 'BUY' or 'SELL'"
    
    # Quantity validation
    try:
        quantity = float(quantity)
        if quantity <= 0:
            errors['quantity'] = "Quantity must be positive"
    except (ValueError, TypeError):
        errors['quantity'] = "Quantity must be a valid number"
    
    # Price validation
    try:
        price = float(price)
        if price <= 0:
            errors['price'] = "Price must be positive"
    except (ValueError, TypeError):
        errors['price'] = "Price must be a valid number"
    
    return errors


def validate_percentage(value: Union[str, float, int]) -> bool:
    """Validate that a value is a valid percentage (0 to 1 or 0 to 100)."""
    try:
        if isinstance(value, str):
            value = value.replace('%', '')
            numeric_value = float(value)
        else:
            numeric_value = float(value)
        
        # If value is greater than 1, assume it's in percentage format (0-100)
        # Otherwise assume it's in decimal format (0-1)
        if numeric_value > 1:
            return 0 <= numeric_value <= 100
        else:
            return 0 <= numeric_value <= 1
    except (ValueError, TypeError):
        return False


def validate_positive_number(value: Union[str, float, int]) -> bool:
    """Validate that a value is a positive number."""
    try:
        numeric_value = float(value)
        return numeric_value > 0
    except (ValueError, TypeError):
        return False