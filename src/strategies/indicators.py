"""
Technical Indicators for Trading Strategies

Implements various technical indicators used in trading strategies
"""
from typing import List, Tuple
import statistics


class Indicators:
    """
    Class containing various technical indicators used in trading strategies.
    """
    
    @staticmethod
    def simple_moving_average(values: List[float], period: int) -> float:
        """
        Calculate Simple Moving Average (SMA).
        """
        if len(values) < period:
            return sum(values) / len(values) if values else 0
        return sum(values[-period:]) / period
    
    @staticmethod
    def exponential_moving_average(values: List[float], period: int) -> float:
        """
        Calculate Exponential Moving Average (EMA).
        """
        if not values:
            return 0
        
        if len(values) == 1:
            return values[0]
        
        # For periods >= length of data, fall back to SMA
        if len(values) <= period:
            return Indicators.simple_moving_average(values, len(values))
        
        # Calculate multiplier
        multiplier = 2 / (period + 1)
        
        # Start with SMA for the first value
        ema = Indicators.simple_moving_average(values[:period], period)
        
        # Calculate EMA for remaining values
        for value in values[period:]:
            ema = (value * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    @staticmethod
    def bollinger_bands(values: List[float], period: int, std_dev: float = 2.0) -> Tuple[float, float, float]:
        """
        Calculate Bollinger Bands (upper, middle, lower).
        """
        if len(values) < period:
            return 0, 0, 0
        
        sma = Indicators.simple_moving_average(values[-period:], period)
        std = statistics.stdev(values[-period:])
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return upper_band, sma, lower_band
    
    @staticmethod
    def relative_strength_index(values: List[float], period: int = 14) -> float:
        """
        Calculate Relative Strength Index (RSI).
        """
        if len(values) < period + 1:
            return 50.0  # Neutral RSI value
        
        # Calculate gains and losses
        gains = []
        losses = []
        
        for i in range(1, len(values[-(period+1):])):
            change = values[-(period+1)+i] - values[-(period+1)+i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        # Calculate average gain and loss
        if len(gains) < period:
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
        else:
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
        
        # Calculate RSI
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def moving_average_convergence_divergence(values: List[float], 
                                            fast_period: int = 12, 
                                            slow_period: int = 26, 
                                            signal_period: int = 9) -> Tuple[float, float, float]:
        """
        Calculate MACD (Line, Signal, Histogram).
        """
        if len(values) < slow_period + signal_period:
            return 0, 0, 0
        
        # Calculate EMAs
        slow_ema = Indicators.exponential_moving_average(values[-slow_period:], slow_period)
        fast_ema = Indicators.exponential_moving_average(values[-fast_period:], fast_period)
        
        # Calculate MACD line
        macd_line = fast_ema - slow_ema
        
        # Calculate signal line
        # For simplicity, we'll calculate it from the current MACD line
        # This is simplified - in practice, you'd track MACD line over time
        if len(values) >= slow_period + signal_period + fast_period:
            # This is a simplified approach - a full implementation would maintain historical MACD values
            signal_line = macd_line  # Placeholder
        else:
            signal_line = macd_line  # Placeholder
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def average_true_range(highs: List[float], lows: List[float], closes: List[float], 
                          period: int = 14) -> float:
        """
        Calculate Average True Range (ATR).
        """
        if len(highs) < period or len(lows) < period or len(closes) < period:
            return 0
            
        true_ranges = []
        for i in range(1, len(closes)):
            high = highs[-i]
            low = lows[-i]
            prev_close = closes[-i-1] if i < len(closes) - 1 else closes[-i]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        # Only consider up to period values
        true_ranges = true_ranges[-period:] if len(true_ranges) >= period else true_ranges
        
        if not true_ranges:
            return 0
            
        return sum(true_ranges) / len(true_ranges)
    
    @staticmethod
    def momentum(closes: List[float], period: int = 10) -> float:
        """
        Calculate Momentum indicator.
        """
        if len(closes) < period + 1:
            return 0
            
        return closes[-1] - closes[-period - 1]