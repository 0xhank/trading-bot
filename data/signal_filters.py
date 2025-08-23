"""
Signal Strength and Momentum Filters for EMA Trading Strategy

This module provides advanced filtering capabilities to improve signal quality
by analyzing signal strength and momentum characteristics.
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
from datetime import datetime

from data.ema_calculator import EMAData, CrossoverSignal


@dataclass
class FilterResult:
    """Result from a signal filter"""
    passed: bool
    score: float  # 0.0 to 1.0
    reason: str
    details: Dict


@dataclass
class SignalContext:
    """Enhanced context for signal analysis"""
    ema_data: EMAData
    price_history: List[float]
    ema20_history: List[float]
    ema50_history: List[float]
    timestamps: List[datetime]


class BaseFilter(ABC):
    """Base class for all signal filters"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def evaluate(self, context: SignalContext) -> FilterResult:
        """Evaluate the filter against signal context"""
        pass


class EMASeparationFilter(BaseFilter):
    """
    Filter based on EMA separation strength
    
    Stronger signals have larger separation between EMA20 and EMA50
    """
    
    def __init__(self, min_separation: float = 0.5, optimal_separation: float = 2.0):
        super().__init__("EMA Separation")
        self.min_separation = min_separation  # Minimum separation %
        self.optimal_separation = optimal_separation  # Optimal separation %
    
    def evaluate(self, context: SignalContext) -> FilterResult:
        ema_data = context.ema_data
        
        if not ema_data.ema_20 or not ema_data.ema_50:
            return FilterResult(False, 0.0, "EMAs not available", {})
        
        # Calculate separation percentage
        avg_ema = (ema_data.ema_20 + ema_data.ema_50) / 2
        separation = abs(ema_data.ema_20 - ema_data.ema_50)
        separation_pct = (separation / avg_ema) * 100
        
        # Score based on separation strength
        if separation_pct < self.min_separation:
            score = 0.0
            passed = False
            reason = f"Separation too weak: {separation_pct:.2f}% < {self.min_separation}%"
        else:
            # Linear score from min to optimal separation
            score = min(separation_pct / self.optimal_separation, 1.0)
            passed = True
            reason = f"Good separation: {separation_pct:.2f}%"
        
        details = {
            'separation_pct': separation_pct,
            'ema20': ema_data.ema_20,
            'ema50': ema_data.ema_50,
            'min_required': self.min_separation
        }
        
        return FilterResult(passed, score, reason, details)


class PriceAlignmentFilter(BaseFilter):
    """
    Filter based on price alignment with signal direction
    
    For bullish signals: price should be above both EMAs
    For bearish signals: price should be below both EMAs
    """
    
    def __init__(self, max_distance: float = 2.0):
        super().__init__("Price Alignment")
        self.max_distance = max_distance  # Maximum distance from EMA20 %
    
    def evaluate(self, context: SignalContext) -> FilterResult:
        ema_data = context.ema_data
        
        if not ema_data.ema_20 or not ema_data.ema_50:
            return FilterResult(False, 0.0, "EMAs not available", {})
        
        price = ema_data.price
        ema20 = ema_data.ema_20
        ema50 = ema_data.ema_50
        signal = ema_data.signal
        
        # Calculate price distance from EMA20
        distance_from_ema20 = abs(price - ema20) / ema20 * 100
        
        # Check alignment based on signal type
        if signal == CrossoverSignal.GOLDEN_CROSS:
            # Bullish: price should be above both EMAs
            above_ema20 = price > ema20
            above_ema50 = price > ema50
            properly_aligned = above_ema20 and above_ema50
            expected_position = "above both EMAs"
        elif signal == CrossoverSignal.DEATH_CROSS:
            # Bearish: price should be below both EMAs
            below_ema20 = price < ema20
            below_ema50 = price < ema50
            properly_aligned = below_ema20 and below_ema50
            expected_position = "below both EMAs"
        else:
            return FilterResult(True, 0.5, "No signal to evaluate", {})
        
        # Check if price is too far from EMA20
        too_extended = distance_from_ema20 > self.max_distance
        
        # Scoring
        if not properly_aligned:
            score = 0.0
            passed = False
            reason = f"Price not {expected_position}"
        elif too_extended:
            score = 0.3
            passed = False
            reason = f"Price too far from EMA20: {distance_from_ema20:.2f}%"
        else:
            # Score inversely related to distance (closer = better)
            distance_score = 1.0 - (distance_from_ema20 / self.max_distance)
            score = max(distance_score, 0.5)
            passed = True
            reason = f"Price properly aligned, distance: {distance_from_ema20:.2f}%"
        
        details = {
            'price': price,
            'ema20': ema20,
            'ema50': ema50,
            'distance_from_ema20': distance_from_ema20,
            'properly_aligned': properly_aligned,
            'too_extended': too_extended
        }
        
        return FilterResult(passed, score, reason, details)


class SignalPersistenceFilter(BaseFilter):
    """
    Filter based on signal persistence over multiple bars
    
    Requires signal to persist for specified number of bars
    """
    
    def __init__(self, confirmation_bars: int = 2):
        super().__init__("Signal Persistence")
        self.confirmation_bars = confirmation_bars
    
    def evaluate(self, context: SignalContext) -> FilterResult:
        ema_data = context.ema_data
        ema20_history = context.ema20_history
        ema50_history = context.ema50_history
        
        if len(ema20_history) < self.confirmation_bars + 1:
            return FilterResult(False, 0.0, "Insufficient history for persistence check", {})
        
        signal = ema_data.signal
        if signal == CrossoverSignal.NO_SIGNAL:
            return FilterResult(True, 0.5, "No signal to evaluate", {})
        
        # Check if signal direction has persisted
        persistent_bars = 0
        expected_relationship = signal == CrossoverSignal.GOLDEN_CROSS  # True if EMA20 should be > EMA50
        
        for i in range(1, min(len(ema20_history), self.confirmation_bars + 1)):
            ema20_past = ema20_history[-i]
            ema50_past = ema50_history[-i]
            
            if ema20_past and ema50_past:
                current_relationship = ema20_past > ema50_past
                if current_relationship == expected_relationship:
                    persistent_bars += 1
                else:
                    break
        
        # Score based on persistence
        persistence_ratio = persistent_bars / self.confirmation_bars
        
        if persistence_ratio >= 1.0:
            score = 1.0
            passed = True
            reason = f"Signal persisted for {persistent_bars} bars"
        elif persistence_ratio >= 0.5:
            score = persistence_ratio
            passed = True
            reason = f"Partial persistence: {persistent_bars}/{self.confirmation_bars} bars"
        else:
            score = 0.0
            passed = False
            reason = f"Insufficient persistence: {persistent_bars}/{self.confirmation_bars} bars"
        
        details = {
            'required_bars': self.confirmation_bars,
            'persistent_bars': persistent_bars,
            'persistence_ratio': persistence_ratio
        }
        
        return FilterResult(passed, score, reason, details)


class PriceMomentumFilter(BaseFilter):
    """
    Filter based on recent price momentum
    
    Bullish signals should have positive momentum
    Bearish signals should have negative momentum
    """
    
    def __init__(self, lookback_periods: int = 5, min_momentum: float = 1.0):
        super().__init__("Price Momentum")
        self.lookback_periods = lookback_periods
        self.min_momentum = min_momentum  # Minimum momentum %
    
    def evaluate(self, context: SignalContext) -> FilterResult:
        ema_data = context.ema_data
        price_history = context.price_history
        signal = ema_data.signal
        
        if len(price_history) < self.lookback_periods + 1:
            return FilterResult(False, 0.0, "Insufficient price history", {})
        
        if signal == CrossoverSignal.NO_SIGNAL:
            return FilterResult(True, 0.5, "No signal to evaluate", {})
        
        # Calculate momentum over lookback period
        current_price = price_history[-1]
        past_price = price_history[-(self.lookback_periods + 1)]
        momentum_pct = (current_price - past_price) / past_price * 100
        
        # Expected momentum direction based on signal
        if signal == CrossoverSignal.GOLDEN_CROSS:
            expected_positive = True
            required_momentum = self.min_momentum
        else:  # DEATH_CROSS
            expected_positive = False
            required_momentum = -self.min_momentum
        
        # Check momentum alignment
        momentum_aligned = (momentum_pct > 0) == expected_positive
        momentum_sufficient = abs(momentum_pct) >= self.min_momentum
        
        # Scoring
        if not momentum_aligned:
            score = 0.0
            passed = False
            reason = f"Momentum misaligned: {momentum_pct:.2f}% (expected {'positive' if expected_positive else 'negative'})"
        elif not momentum_sufficient:
            score = 0.3
            passed = False
            reason = f"Momentum too weak: {momentum_pct:.2f}% (need {required_momentum:.1f}%)"
        else:
            # Score based on momentum strength
            momentum_strength = abs(momentum_pct) / (self.min_momentum * 2)  # Normalize to 2x minimum
            score = min(momentum_strength, 1.0)
            passed = True
            reason = f"Good momentum: {momentum_pct:.2f}%"
        
        details = {
            'momentum_pct': momentum_pct,
            'lookback_periods': self.lookback_periods,
            'min_required': required_momentum,
            'momentum_aligned': momentum_aligned,
            'momentum_sufficient': momentum_sufficient
        }
        
        return FilterResult(passed, score, reason, details)


class EMASlopeFilter(BaseFilter):
    """
    Filter based on EMA slope analysis
    
    EMAs should have proper directional slope for strong signals
    """
    
    def __init__(self, min_slope_ratio: float = 1.5, lookback_periods: int = 3):
        super().__init__("EMA Slope")
        self.min_slope_ratio = min_slope_ratio
        self.lookback_periods = lookback_periods
    
    def evaluate(self, context: SignalContext) -> FilterResult:
        ema_data = context.ema_data
        ema20_history = context.ema20_history
        ema50_history = context.ema50_history
        signal = ema_data.signal
        
        if len(ema20_history) < self.lookback_periods + 1:
            return FilterResult(False, 0.0, "Insufficient EMA history", {})
        
        if signal == CrossoverSignal.NO_SIGNAL:
            return FilterResult(True, 0.5, "No signal to evaluate", {})
        
        # Calculate EMA slopes
        ema20_current = ema20_history[-1]
        ema20_past = ema20_history[-(self.lookback_periods + 1)]
        ema50_current = ema50_history[-1]
        ema50_past = ema50_history[-(self.lookback_periods + 1)]
        
        if not all([ema20_current, ema20_past, ema50_current, ema50_past]):
            return FilterResult(False, 0.0, "Invalid EMA data", {})
        
        ema20_slope = (ema20_current - ema20_past) / ema20_past * 100
        ema50_slope = (ema50_current - ema50_past) / ema50_past * 100
        
        # Expected slope characteristics
        if signal == CrossoverSignal.GOLDEN_CROSS:
            # Bullish: both slopes should be positive, EMA20 slope > EMA50 slope
            expected_ema20_positive = True
            expected_ema50_positive = True
            expected_diverging = ema20_slope > ema50_slope
        else:  # DEATH_CROSS
            # Bearish: both slopes should be negative, EMA20 slope < EMA50 slope
            expected_ema20_positive = False
            expected_ema50_positive = False
            expected_diverging = ema20_slope < ema50_slope
        
        # Check slope conditions
        ema20_correct = (ema20_slope > 0) == expected_ema20_positive
        ema50_correct = (ema50_slope > 0) == expected_ema50_positive
        slopes_diverging = expected_diverging
        
        # Calculate slope ratio
        if ema50_slope != 0:
            slope_ratio = abs(ema20_slope / ema50_slope)
        else:
            slope_ratio = float('inf') if ema20_slope != 0 else 1.0
        
        # Scoring
        conditions_met = sum([ema20_correct, ema50_correct, slopes_diverging])
        
        if conditions_met == 0:
            score = 0.0
            passed = False
            reason = "No slope conditions met"
        elif conditions_met == 1:
            score = 0.2
            passed = False
            reason = "Only 1/3 slope conditions met"
        elif conditions_met == 2:
            score = 0.6
            passed = True
            reason = "2/3 slope conditions met"
        else:  # conditions_met == 3
            # Bonus for strong slope ratio
            ratio_bonus = min(slope_ratio / self.min_slope_ratio, 2.0) * 0.2
            score = min(0.8 + ratio_bonus, 1.0)
            passed = True
            reason = f"All slope conditions met, ratio: {slope_ratio:.2f}"
        
        details = {
            'ema20_slope': ema20_slope,
            'ema50_slope': ema50_slope,
            'slope_ratio': slope_ratio,
            'ema20_correct': ema20_correct,
            'ema50_correct': ema50_correct,
            'slopes_diverging': slopes_diverging,
            'conditions_met': conditions_met
        }
        
        return FilterResult(passed, score, reason, details)


class MarketStructureFilter(BaseFilter):
    """
    Filter based on market structure analysis
    
    Analyzes higher highs/lower lows pattern for trend confirmation
    """
    
    def __init__(self, lookback_periods: int = 10, min_swings: int = 2):
        super().__init__("Market Structure")
        self.lookback_periods = lookback_periods
        self.min_swings = min_swings
    
    def evaluate(self, context: SignalContext) -> FilterResult:
        ema_data = context.ema_data
        price_history = context.price_history
        signal = ema_data.signal
        
        if len(price_history) < self.lookback_periods:
            return FilterResult(False, 0.0, "Insufficient price history for structure analysis", {})
        
        if signal == CrossoverSignal.NO_SIGNAL:
            return FilterResult(True, 0.5, "No signal to evaluate", {})
        
        # Get recent price data
        recent_prices = price_history[-self.lookback_periods:]
        
        # Find swing highs and lows
        swing_highs = self._find_swing_highs(recent_prices)
        swing_lows = self._find_swing_lows(recent_prices)
        
        if len(swing_highs) < self.min_swings or len(swing_lows) < self.min_swings:
            return FilterResult(False, 0.0, f"Insufficient swings found (need {self.min_swings})", {})
        
        # Analyze structure
        structure_bullish = self._is_structure_bullish(swing_highs, swing_lows)
        structure_bearish = self._is_structure_bearish(swing_highs, swing_lows)
        
        # Expected structure based on signal
        if signal == CrossoverSignal.GOLDEN_CROSS:
            structure_aligned = structure_bullish
            expected_structure = "bullish"
        else:  # DEATH_CROSS
            structure_aligned = structure_bearish
            expected_structure = "bearish"
        
        # Scoring
        if structure_aligned:
            score = 0.8
            passed = True
            reason = f"Market structure is {expected_structure}"
        elif signal == CrossoverSignal.GOLDEN_CROSS and structure_bearish:
            score = 0.0
            passed = False
            reason = "Market structure is bearish (conflicts with bullish signal)"
        elif signal == CrossoverSignal.DEATH_CROSS and structure_bullish:
            score = 0.0
            passed = False
            reason = "Market structure is bullish (conflicts with bearish signal)"
        else:
            score = 0.4
            passed = True
            reason = "Market structure is neutral/unclear"
        
        details = {
            'swing_highs': swing_highs,
            'swing_lows': swing_lows,
            'structure_bullish': structure_bullish,
            'structure_bearish': structure_bearish,
            'structure_aligned': structure_aligned
        }
        
        return FilterResult(passed, score, reason, details)
    
    def _find_swing_highs(self, prices: List[float]) -> List[Tuple[int, float]]:
        """Find swing high points in price series"""
        highs = []
        for i in range(2, len(prices) - 2):
            if (prices[i] > prices[i-1] and prices[i] > prices[i-2] and
                prices[i] > prices[i+1] and prices[i] > prices[i+2]):
                highs.append((i, prices[i]))
        return highs
    
    def _find_swing_lows(self, prices: List[float]) -> List[Tuple[int, float]]:
        """Find swing low points in price series"""
        lows = []
        for i in range(2, len(prices) - 2):
            if (prices[i] < prices[i-1] and prices[i] < prices[i-2] and
                prices[i] < prices[i+1] and prices[i] < prices[i+2]):
                lows.append((i, prices[i]))
        return lows
    
    def _is_structure_bullish(self, highs: List[Tuple[int, float]], lows: List[Tuple[int, float]]) -> bool:
        """Check for higher highs and higher lows pattern"""
        if len(highs) < 2 or len(lows) < 2:
            return False
        
        # Check for higher highs
        higher_highs = highs[-1][1] > highs[-2][1]
        
        # Check for higher lows
        higher_lows = lows[-1][1] > lows[-2][1]
        
        return higher_highs and higher_lows
    
    def _is_structure_bearish(self, highs: List[Tuple[int, float]], lows: List[Tuple[int, float]]) -> bool:
        """Check for lower highs and lower lows pattern"""
        if len(highs) < 2 or len(lows) < 2:
            return False
        
        # Check for lower highs
        lower_highs = highs[-1][1] < highs[-2][1]
        
        # Check for lower lows
        lower_lows = lows[-1][1] < lows[-2][1]
        
        return lower_highs and lower_lows
