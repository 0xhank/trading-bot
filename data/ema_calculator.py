import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime


class CrossoverSignal(Enum):
    """EMA crossover signals"""
    GOLDEN_CROSS = "buy"      # EMA20 crosses above EMA50
    DEATH_CROSS = "sell"      # EMA20 crosses below EMA50
    NO_SIGNAL = "hold"        # No crossover detected


@dataclass
class EMAData:
    """Container for EMA calculation results"""
    timestamp: datetime
    price: float
    ema_20: Optional[float] = None
    ema_50: Optional[float] = None
    signal: CrossoverSignal = CrossoverSignal.NO_SIGNAL
    signal_strength: float = 0.0  # 0-1, how strong the signal is


class EMACalculator:
    """
    Specialized EMA calculator focused on 20/50 period crossover strategy
    
    Features:
    - Real-time EMA calculations
    - Crossover detection with confirmation
    - Signal strength analysis
    - Memory-efficient rolling calculations
    """
    
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.logger = logging.getLogger(__name__)
        
        # EMA multipliers (alpha)
        self.fast_alpha = 2 / (fast_period + 1)
        self.slow_alpha = 2 / (slow_period + 1)
        
        # Current EMA values
        self.fast_ema = None  # EMA 20
        self.slow_ema = None  # EMA 50
        
        # Historical data for analysis
        self.price_history = []
        self.ema_history = []
        self.max_history = 200  # Keep last 200 data points
        
        # Crossover tracking
        self.last_signal = CrossoverSignal.NO_SIGNAL
        self.signal_confirmed = False
        self.confirmation_bars = 2  # Require 2 bars to confirm signal
        self.bars_since_signal = 0
        
        # Statistics
        self.total_updates = 0
        self.golden_crosses = 0
        self.death_crosses = 0
        
    def add_price(self, price: float, timestamp: datetime = None) -> EMAData:
        """
        Add new price and calculate EMAs
        
        Args:
            price: Current price
            timestamp: Optional timestamp, uses current time if None
            
        Returns:
            EMAData object with calculated values and signals
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
            
        # Update EMA values
        self._update_emas(price)
        
        # Detect crossover signals
        signal, strength = self._detect_crossover()
        
        # Create result object
        ema_data = EMAData(
            timestamp=timestamp,
            price=price,
            ema_20=self.fast_ema,
            ema_50=self.slow_ema,
            signal=signal,
            signal_strength=strength
        )
        
        # Store in history
        self._update_history(ema_data)
        
        # Update statistics
        self.total_updates += 1
        if signal == CrossoverSignal.GOLDEN_CROSS:
            self.golden_crosses += 1
        elif signal == CrossoverSignal.DEATH_CROSS:
            self.death_crosses += 1
            
        self.logger.debug(f"EMA Update: Price={price:.2f}, EMA20={self.fast_ema:.2f}, EMA50={self.slow_ema:.2f}, Signal={signal.value}")
        
        return ema_data
    
    def _update_emas(self, price: float):
        """Update EMA values using exponential smoothing"""
        if self.fast_ema is None:
            # Initialize EMAs with first price
            self.fast_ema = price
            self.slow_ema = price
        else:
            # Calculate new EMAs
            self.fast_ema = (price * self.fast_alpha) + (self.fast_ema * (1 - self.fast_alpha))
            self.slow_ema = (price * self.slow_alpha) + (self.slow_ema * (1 - self.slow_alpha))
    
    def _detect_crossover(self) -> Tuple[CrossoverSignal, float]:
        """
        Detect EMA crossovers and calculate signal strength
        
        Returns:
            Tuple of (signal, strength)
        """
        if self.fast_ema is None or self.slow_ema is None:
            return CrossoverSignal.NO_SIGNAL, 0.0
            
        # Check if we have enough history for crossover detection
        if len(self.ema_history) < 2:
            return CrossoverSignal.NO_SIGNAL, 0.0
            
        # Get previous EMA values
        prev_data = self.ema_history[-1]
        prev_fast = prev_data.ema_20
        prev_slow = prev_data.ema_50
        
        # Current EMA relationship
        fast_above_slow = self.fast_ema > self.slow_ema
        prev_fast_above_slow = prev_fast > prev_slow
        
        signal = CrossoverSignal.NO_SIGNAL
        strength = 0.0
        
        # Detect crossovers
        if not prev_fast_above_slow and fast_above_slow:
            # Golden Cross: EMA20 crossed above EMA50
            signal = CrossoverSignal.GOLDEN_CROSS
            strength = self._calculate_signal_strength(True)
            self.logger.info(f"🟢 GOLDEN CROSS detected! EMA20({self.fast_ema:.2f}) > EMA50({self.slow_ema:.2f})")
            
        elif prev_fast_above_slow and not fast_above_slow:
            # Death Cross: EMA20 crossed below EMA50
            signal = CrossoverSignal.DEATH_CROSS
            strength = self._calculate_signal_strength(False)
            self.logger.info(f"🔴 DEATH CROSS detected! EMA20({self.fast_ema:.2f}) < EMA50({self.slow_ema:.2f})")
        
        # Update signal tracking
        if signal != CrossoverSignal.NO_SIGNAL:
            self.last_signal = signal
            self.bars_since_signal = 0
            self.signal_confirmed = False
        else:
            self.bars_since_signal += 1
            # Confirm signal after required bars
            if self.bars_since_signal >= self.confirmation_bars:
                self.signal_confirmed = True
        
        return signal, strength
    
    def _calculate_signal_strength(self, is_bullish: bool) -> float:
        """
        Calculate signal strength based on EMA separation and trend
        
        Args:
            is_bullish: True for golden cross, False for death cross
            
        Returns:
            Signal strength from 0.0 to 1.0
        """
        if self.fast_ema is None or self.slow_ema is None:
            return 0.0
            
        # Calculate EMA separation as percentage
        ema_diff = abs(self.fast_ema - self.slow_ema)
        avg_ema = (self.fast_ema + self.slow_ema) / 2
        separation_pct = (ema_diff / avg_ema) * 100
        
        # Base strength on separation (more separation = stronger signal)
        strength = min(separation_pct / 2.0, 1.0)  # Cap at 1.0, normalize by 2%
        
        # Boost strength if trend is consistent
        if len(self.ema_history) >= 5:
            recent_prices = [data.price for data in self.ema_history[-5:]]
            trend_strength = self._calculate_trend_strength(recent_prices, is_bullish)
            strength = min(strength * (1 + trend_strength), 1.0)
        
        return round(strength, 3)
    
    def _calculate_trend_strength(self, prices: List[float], is_bullish: bool) -> float:
        """Calculate trend strength from recent price action"""
        if len(prices) < 3:
            return 0.0
            
        # Calculate price momentum
        price_change = (prices[-1] - prices[0]) / prices[0]
        
        # Check if momentum aligns with signal
        if (is_bullish and price_change > 0) or (not is_bullish and price_change < 0):
            return min(abs(price_change) * 10, 0.5)  # Max 50% boost
        
        return 0.0
    
    def _update_history(self, ema_data: EMAData):
        """Update historical data with memory management"""
        self.price_history.append(ema_data.price)
        self.ema_history.append(ema_data)
        
        # Trim history to manage memory
        if len(self.price_history) > self.max_history:
            self.price_history.pop(0)
        if len(self.ema_history) > self.max_history:
            self.ema_history.pop(0)
    
    def get_current_status(self) -> Dict:
        """Get current EMA status and statistics"""
        return {
            'fast_ema': self.fast_ema,
            'slow_ema': self.slow_ema,
            'trend': 'bullish' if self.fast_ema and self.slow_ema and self.fast_ema > self.slow_ema else 'bearish',
            'last_signal': self.last_signal.value,
            'signal_confirmed': self.signal_confirmed,
            'bars_since_signal': self.bars_since_signal,
            'total_updates': self.total_updates,
            'golden_crosses': self.golden_crosses,
            'death_crosses': self.death_crosses,
            'data_points': len(self.ema_history)
        }
    
    def initialize_from_historical_data(self, df: pd.DataFrame, price_column: str = 'close'):
        """
        Initialize EMAs from historical price data
        
        Args:
            df: DataFrame with historical price data
            price_column: Column name containing prices
        """
        if df.empty:
            self.logger.warning("Empty DataFrame provided for initialization")
            return
            
        self.logger.info(f"Initializing EMAs from {len(df)} historical data points")
        
        for _, row in df.iterrows():
            price = float(row[price_column])
            timestamp = row.name if isinstance(row.name, datetime) else datetime.utcnow()
            self.add_price(price, timestamp)
            
        self.logger.info(f"EMA initialization complete. EMA20: {self.fast_ema:.2f}, EMA50: {self.slow_ema:.2f}")
    
    def get_trading_signal(self) -> Dict:
        """
        Get actionable trading signal with context
        
        Returns:
            Dictionary with signal information
        """
        if not self.ema_history:
            return {
                'action': 'wait',
                'signal': 'insufficient_data',
                'confidence': 0.0,
                'message': 'Not enough data for signal generation'
            }
        
        latest = self.ema_history[-1]
        
        # Check for recent crossover
        if latest.signal != CrossoverSignal.NO_SIGNAL and not self.signal_confirmed:
            return {
                'action': latest.signal.value,
                'signal': 'crossover_detected',
                'confidence': latest.signal_strength,
                'message': f'{"Golden" if latest.signal == CrossoverSignal.GOLDEN_CROSS else "Death"} cross detected, awaiting confirmation',
                'ema_20': self.fast_ema,
                'ema_50': self.slow_ema
            }
        
        # Check for confirmed signal
        if self.signal_confirmed and self.bars_since_signal <= 5:  # Signal valid for 5 bars
            action = self.last_signal.value if self.last_signal != CrossoverSignal.NO_SIGNAL else 'hold'
            return {
                'action': action,
                'signal': 'confirmed_crossover',
                'confidence': 0.8,  # High confidence for confirmed signals
                'message': f'Confirmed {"bullish" if self.last_signal == CrossoverSignal.GOLDEN_CROSS else "bearish"} signal',
                'ema_20': self.fast_ema,
                'ema_50': self.slow_ema
            }
        
        # Default: hold position
        trend = 'bullish' if self.fast_ema > self.slow_ema else 'bearish'
        return {
            'action': 'hold',
            'signal': 'no_crossover',
            'confidence': 0.5,
            'message': f'No crossover signal, trend is {trend}',
            'ema_20': self.fast_ema,
            'ema_50': self.slow_ema
        }
    
    def reset(self):
        """Reset calculator to initial state"""
        self.fast_ema = None
        self.slow_ema = None
        self.price_history.clear()
        self.ema_history.clear()
        self.last_signal = CrossoverSignal.NO_SIGNAL
        self.signal_confirmed = False
        self.bars_since_signal = 0
        self.total_updates = 0
        self.golden_crosses = 0
        self.death_crosses = 0
        self.logger.info("EMA calculator reset")
