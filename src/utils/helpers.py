"""
Utility functions for the MXC Scalp Trading Bot
"""
import re
from typing import Union


def validate_symbol(symbol: str) -> bool:
    """
    Validate that a symbol is in proper format (e.g., BTCUSDT).
    """
    # Check if symbol matches the pattern: uppercase letters, followed by uppercase letters (quote currency)
    pattern = r'^[A-Z]+[A-Z]+$'
    return bool(re.match(pattern, symbol)) and len(symbol) >= 6


def calculate_profit(entry_price: float, exit_price: float, quantity: float, is_long: bool = True) -> float:
    """
    Calculate profit/loss for a trade.
    
    Args:
        entry_price: Price at which position was opened
        exit_price: Price at which position was closed
        quantity: Quantity of the asset traded
        is_long: True if it was a BUY trade, False if SELL
    
    Returns:
        Profit (positive) or loss (negative) amount
    """
    if is_long:
        return (exit_price - entry_price) * quantity
    else:
        return (entry_price - exit_price) * quantity


def format_currency(amount: Union[float, int], currency: str = 'USDT') -> str:
    """
    Format currency amounts with appropriate decimal places.
    """
    if currency in ['USDT', 'BUSD', 'USDC', 'DAI']:
        # Stablecoins - show 4 decimal places
        return f"{amount:.4f} {currency}"
    elif currency in ['BTC']:
        # Bitcoin - show 8 decimal places
        return f"{amount:.8f} {currency}"
    else:
        # Other currencies - show 4 decimal places
        return f"{amount:.4f} {currency}"


def percent_to_decimal(percent: Union[float, str]) -> float:
    """
    Convert percentage string or value to decimal.
    
    Args:
        percent: Percentage value as float (0.5 for 0.5%) or string ("0.5%")
    """
    if isinstance(percent, str):
        # Remove % sign if present and convert to float
        percent = percent.replace('%', '')
        return float(percent) / 100
    return percent / 100


def decimal_to_percent(decimal: float) -> float:
    """
    Convert decimal to percentage.
    """
    return decimal * 100


def safe_float(value: Union[str, int, float, None], default: float = 0.0) -> float:
    """
    Safely convert a value to float, returning a default if conversion fails.
    """
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def truncate_float(value: float, decimals: int = 8) -> float:
    """
    Truncate a float to specified number of decimal places without rounding.
    """
    multiplier = 10 ** decimals
    return int(value * multiplier) / multiplier