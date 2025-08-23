"""
Enhanced EMA Calculator with Signal Strength and Momentum Filters

This module extends the basic EMA calculator with advanced filtering
capabilities to improve signal quality and reduce false positives.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from data.ema_calculator import EMACalculator, EMAData, CrossoverSignal
from data.signal_filters import (
    SignalContext, FilterResult,
    EMASeparationFilter, PriceAlignmentFilter, SignalPersistenceFilter,
    PriceMomentumFilter, EMASlopeFilter, MarketStructureFilter
)


@dataclass
class EnhancedSignalResult:
    """Enhanced signal result with filtering details"""
    ema_data: EMAData
    raw_signal: CrossoverSignal
    filtered_signal: CrossoverSignal
    filter_approved: bool
    confidence_score: float
    strength_score: float
    momentum_score: float
    filter_results: Dict[str, FilterResult]
    recommendation: str
    
    
@dataclass
class FilterConfig:
    """Configuration for signal filters"""
    # Strength filter settings
    min_ema_separation: float = 0.5
    max_price_distance: float = 2.0
    confirmation_bars: int = 2
    
    # Momentum filter settings
    min_price_momentum: float = 1.0
    momentum_lookback: int = 5
    min_slope_ratio: float = 1.5
    slope_lookback: int = 3
    structure_lookback: int = 10
    min_swings: int = 2
    
    # Scoring thresholds
    minimum_confidence: float = 0.7
    high_confidence: float = 0.85
    reject_below: float = 0.3
    
    # Filter weights
    strength_weight: float = 0.6
    momentum_weight: float = 0.4


class SignalFilterManager:
    """
    Manages all signal filters and provides comprehensive signal analysis
    """
    
    def __init__(self, config: FilterConfig = None):
        self.config = config or FilterConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize filters
        self.strength_filters = [
            EMASeparationFilter(
                min_separation=self.config.min_ema_separation,
                optimal_separation=self.config.min_ema_separation * 4
            ),
            PriceAlignmentFilter(
                max_distance=self.config.max_price_distance
            ),
            SignalPersistenceFilter(
                confirmation_bars=self.config.confirmation_bars
            )
        ]
        
        self.momentum_filters = [
            PriceMomentumFilter(
                lookback_periods=self.config.momentum_lookback,
                min_momentum=self.config.min_price_momentum
            ),
            EMASlopeFilter(
                min_slope_ratio=self.config.min_slope_ratio,
                lookback_periods=self.config.slope_lookback
            ),
            MarketStructureFilter(
                lookback_periods=self.config.structure_lookback,
                min_swings=self.config.min_swings
            )
        ]
        
    def evaluate_signal(self, context: SignalContext) -> EnhancedSignalResult:
        """
        Evaluate signal through all filters and provide comprehensive analysis
        """
        ema_data = context.ema_data
        raw_signal = ema_data.signal
        
        if raw_signal == CrossoverSignal.NO_SIGNAL:
            return self._create_no_signal_result(ema_data)
        
        # Run strength filters
        strength_results = {}
        strength_scores = []
        
        for filter_obj in self.strength_filters:
            try:
                result = filter_obj.evaluate(context)
                strength_results[filter_obj.name] = result
                strength_scores.append(result.score)
            except Exception as e:
                self.logger.error(f"Error in strength filter {filter_obj.name}: {e}")
                strength_results[filter_obj.name] = FilterResult(False, 0.0, f"Error: {e}", {})
                strength_scores.append(0.0)
        
        # Run momentum filters
        momentum_results = {}
        momentum_scores = []
        
        for filter_obj in self.momentum_filters:
            try:
                result = filter_obj.evaluate(context)
                momentum_results[filter_obj.name] = result
                momentum_scores.append(result.score)
            except Exception as e:
                self.logger.error(f"Error in momentum filter {filter_obj.name}: {e}")
                momentum_results[filter_obj.name] = FilterResult(False, 0.0, f"Error: {e}", {})
                momentum_scores.append(0.0)
        
        # Calculate composite scores
        strength_score = sum(strength_scores) / len(strength_scores) if strength_scores else 0.0
        momentum_score = sum(momentum_scores) / len(momentum_scores) if momentum_scores else 0.0
        
        # Weighted confidence score
        confidence_score = (
            strength_score * self.config.strength_weight +
            momentum_score * self.config.momentum_weight
        )
        
        # Determine if signal is approved
        filter_approved = confidence_score >= self.config.minimum_confidence
        
        # Final signal determination
        if not filter_approved:
            filtered_signal = CrossoverSignal.NO_SIGNAL
        else:
            filtered_signal = raw_signal
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            confidence_score, filtered_signal, strength_score, momentum_score
        )
        
        # Combine all filter results
        all_filter_results = {**strength_results, **momentum_results}
        
        return EnhancedSignalResult(
            ema_data=ema_data,
            raw_signal=raw_signal,
            filtered_signal=filtered_signal,
            filter_approved=filter_approved,
            confidence_score=confidence_score,
            strength_score=strength_score,
            momentum_score=momentum_score,
            filter_results=all_filter_results,
            recommendation=recommendation
        )
    
    def _create_no_signal_result(self, ema_data: EMAData) -> EnhancedSignalResult:
        """Create result for when there's no signal to evaluate"""
        return EnhancedSignalResult(
            ema_data=ema_data,
            raw_signal=CrossoverSignal.NO_SIGNAL,
            filtered_signal=CrossoverSignal.NO_SIGNAL,
            filter_approved=False,
            confidence_score=0.0,
            strength_score=0.0,
            momentum_score=0.0,
            filter_results={},
            recommendation="HOLD - No crossover signal detected"
        )
    
    def _generate_recommendation(self, confidence: float, signal: CrossoverSignal, 
                                strength: float, momentum: float) -> str:
        """Generate trading recommendation based on analysis"""
        if signal == CrossoverSignal.NO_SIGNAL:
            return "HOLD - Signal filtered out"
        
        signal_type = "BUY" if signal == CrossoverSignal.GOLDEN_CROSS else "SELL"
        
        if confidence >= self.config.high_confidence:
            return f"STRONG {signal_type} - High confidence signal"
        elif confidence >= self.config.minimum_confidence:
            if strength > momentum:
                return f"MODERATE {signal_type} - Good signal strength"
            else:
                return f"MODERATE {signal_type} - Good momentum"
        else:
            return f"WEAK {signal_type} - Consider waiting for better setup"


class EnhancedEMACalculator:
    """
    Enhanced EMA Calculator with integrated signal filtering
    
    Combines the basic EMA calculation with advanced filtering
    to provide high-quality trading signals.
    """
    
    def __init__(self, fast_period: int = 20, slow_period: int = 50, 
                 filter_config: FilterConfig = None):
        self.ema_calculator = EMACalculator(fast_period, slow_period)
        self.filter_manager = SignalFilterManager(filter_config)
        self.logger = logging.getLogger(__name__)
        
        # Enhanced history tracking
        self.enhanced_results: List[EnhancedSignalResult] = []
        self.max_history = 200
        
        # Statistics
        self.total_raw_signals = 0
        self.total_filtered_signals = 0
        self.false_positives_filtered = 0
        
    def add_price(self, price: float, timestamp: datetime = None) -> EnhancedSignalResult:
        """
        Add new price and get enhanced signal analysis
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Get basic EMA calculation
        ema_data = self.ema_calculator.add_price(price, timestamp)
        
        # Build context for filtering
        context = self._build_signal_context(ema_data)
        
        # Run enhanced analysis
        enhanced_result = self.filter_manager.evaluate_signal(context)
        
        # Update statistics
        if ema_data.signal != CrossoverSignal.NO_SIGNAL:
            self.total_raw_signals += 1
            
        if enhanced_result.filtered_signal != CrossoverSignal.NO_SIGNAL:
            self.total_filtered_signals += 1
        elif ema_data.signal != CrossoverSignal.NO_SIGNAL:
            self.false_positives_filtered += 1
        
        # Store result
        self._update_history(enhanced_result)
        
        # Log significant signals
        if enhanced_result.filtered_signal != CrossoverSignal.NO_SIGNAL:
            self.logger.info(
                f"Enhanced Signal: {enhanced_result.filtered_signal.value.upper()} "
                f"Confidence: {enhanced_result.confidence_score:.1%} "
                f"Price: ${price:.2f}"
            )
        
        return enhanced_result
    
    def _build_signal_context(self, ema_data: EMAData) -> SignalContext:
        """Build context for signal filtering"""
        # Get price history from base calculator
        price_history = self.ema_calculator.price_history.copy()
        
        # Get EMA histories
        ema20_history = [data.ema_20 for data in self.ema_calculator.ema_history if data.ema_20]
        ema50_history = [data.ema_50 for data in self.ema_calculator.ema_history if data.ema_50]
        
        # Get timestamps
        timestamps = [data.timestamp for data in self.ema_calculator.ema_history]
        
        return SignalContext(
            ema_data=ema_data,
            price_history=price_history,
            ema20_history=ema20_history,
            ema50_history=ema50_history,
            timestamps=timestamps
        )
    
    def _update_history(self, result: EnhancedSignalResult):
        """Update enhanced results history"""
        self.enhanced_results.append(result)
        
        # Trim history
        if len(self.enhanced_results) > self.max_history:
            self.enhanced_results.pop(0)
    
    def get_current_analysis(self) -> Optional[EnhancedSignalResult]:
        """Get the most recent enhanced analysis"""
        return self.enhanced_results[-1] if self.enhanced_results else None
    
    def get_filter_performance(self) -> Dict:
        """Get filtering performance statistics"""
        if self.total_raw_signals == 0:
            return {
                'total_raw_signals': 0,
                'total_filtered_signals': 0,
                'false_positives_filtered': 0,
                'filter_rate': 0.0,
                'signal_quality_improvement': 0.0
            }
        
        filter_rate = self.false_positives_filtered / self.total_raw_signals
        signal_quality = self.total_filtered_signals / self.total_raw_signals if self.total_raw_signals > 0 else 0
        
        return {
            'total_raw_signals': self.total_raw_signals,
            'total_filtered_signals': self.total_filtered_signals,
            'false_positives_filtered': self.false_positives_filtered,
            'filter_rate': filter_rate,
            'signal_quality_improvement': filter_rate,
            'signal_approval_rate': signal_quality
        }
    
    def get_recent_signals(self, count: int = 10) -> List[EnhancedSignalResult]:
        """Get recent enhanced signals"""
        signals = [r for r in self.enhanced_results if r.filtered_signal != CrossoverSignal.NO_SIGNAL]
        return signals[-count:] if signals else []
    
    def get_trading_recommendation(self) -> Dict:
        """Get current trading recommendation with enhanced analysis"""
        latest = self.get_current_analysis()
        
        if not latest:
            return {
                'action': 'wait',
                'signal': 'insufficient_data',
                'confidence': 0.0,
                'message': 'Insufficient data for analysis'
            }
        
        # Get base recommendation
        base_recommendation = self.ema_calculator.get_trading_signal()
        
        # Enhanced recommendation
        if latest.filtered_signal != CrossoverSignal.NO_SIGNAL:
            action = latest.filtered_signal.value
            confidence = latest.confidence_score
            
            # Enhanced message with filter details
            strength_info = f"Strength: {latest.strength_score:.1%}"
            momentum_info = f"Momentum: {latest.momentum_score:.1%}"
            
            message = f"{latest.recommendation} ({strength_info}, {momentum_info})"
            
        else:
            action = 'hold'
            confidence = latest.confidence_score
            message = latest.recommendation
        
        return {
            'action': action,
            'signal': 'enhanced_analysis',
            'confidence': confidence,
            'message': message,
            'raw_signal': latest.raw_signal.value,
            'filtered_signal': latest.filtered_signal.value,
            'strength_score': latest.strength_score,
            'momentum_score': latest.momentum_score,
            'filter_details': {name: result.reason for name, result in latest.filter_results.items()}
        }
    
    def reset(self):
        """Reset calculator and filters"""
        self.ema_calculator.reset()
        self.enhanced_results.clear()
        self.total_raw_signals = 0
        self.total_filtered_signals = 0
        self.false_positives_filtered = 0
        self.logger.info("Enhanced EMA calculator reset")
    
    def initialize_from_historical_data(self, df, price_column: str = 'close'):
        """Initialize with historical data"""
        self.logger.info("Initializing enhanced EMA calculator with historical data")
        self.ema_calculator.initialize_from_historical_data(df, price_column)
        
        # Process recent data through filters to build context
        for _, row in df.tail(50).iterrows():  # Process last 50 points through filters
            price = float(row[price_column])
            timestamp = row.name if hasattr(row.name, 'strftime') else datetime.utcnow()
            self.add_price(price, timestamp)
        
        self.logger.info("Enhanced EMA initialization complete")
