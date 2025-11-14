"""
MXC Scalp Bot - Strategies Package
"""
from .base_strategy import BaseStrategy
from .scalping_strategy import ScalpingStrategy
from .range_scalp_strategy import RangeScalpStrategy
from .futures_strategy import FuturesStrategy
from .indicators import Indicators

__all__ = ['BaseStrategy', 'ScalpingStrategy', 'RangeScalpStrategy', 'FuturesStrategy', 'Indicators']