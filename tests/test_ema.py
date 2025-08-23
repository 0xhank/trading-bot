#!/usr/bin/env python3
"""
Test EMA Calculator with Sample Data
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.ema_calculator import EMACalculator, CrossoverSignal


def test_ema_calculations():
    """Test EMA calculations with sample price data"""
    print("🧪 Testing EMA Calculator")
    print("=" * 40)
    
    # Create sample price data that should generate signals
    prices = [
        100, 101, 99, 102, 101, 103, 104, 102, 105, 106,  # Initial prices
        107, 109, 108, 110, 112, 111, 113, 115, 114, 116,  # Uptrend
        118, 117, 119, 121, 120, 122, 124, 123, 125, 127,  # Continued up
        126, 128, 130, 129, 131, 133, 132, 134, 136, 135,  # More uptrend
        137, 139, 138, 140, 142, 141, 143, 145, 144, 146,  # Peak
        145, 143, 144, 142, 140, 141, 139, 137, 138, 136,  # Start decline
        134, 135, 133, 131, 132, 130, 128, 129, 127, 125   # Downtrend
    ]
    
    calculator = EMACalculator()
    
    print(f"📊 Processing {len(prices)} price points...")
    
    signals_detected = []
    
    for i, price in enumerate(prices):
        timestamp = datetime.utcnow() + timedelta(minutes=i)
        ema_data = calculator.add_price(price, timestamp)
        
        # Print key data points
        if i % 10 == 0 or ema_data.signal != CrossoverSignal.NO_SIGNAL:
            status = "📈" if ema_data.ema_20 and ema_data.ema_50 and ema_data.ema_20 > ema_data.ema_50 else "📉"
            
            print(f"Point {i:2d}: ${price:6.2f} | "
                  f"EMA20: {ema_data.ema_20:6.2f} | "
                  f"EMA50: {ema_data.ema_50:6.2f} | "
                  f"{status}")
            
            if ema_data.signal != CrossoverSignal.NO_SIGNAL:
                signal_emoji = "🟢" if ema_data.signal == CrossoverSignal.GOLDEN_CROSS else "🔴"
                print(f"         {signal_emoji} SIGNAL: {ema_data.signal.value.upper()} "
                      f"(Strength: {ema_data.signal_strength:.1%})")
                signals_detected.append((i, ema_data.signal.value, price))
    
    # Final status
    status = calculator.get_current_status()
    signal_info = calculator.get_trading_signal()
    
    print("\n📋 FINAL RESULTS")
    print("-" * 40)
    print(f"Total Updates: {status['total_updates']}")
    print(f"Golden Crosses: {status['golden_crosses']}")
    print(f"Death Crosses: {status['death_crosses']}")
    print(f"Current EMA20: ${status['fast_ema']:.2f}")
    print(f"Current EMA50: ${status['slow_ema']:.2f}")
    print(f"Current Trend: {status['trend'].upper()}")
    print(f"Trading Action: {signal_info['action'].upper()}")
    print(f"Confidence: {signal_info['confidence']:.1%}")
    
    print(f"\n🎯 Signals Detected: {len(signals_detected)}")
    for i, (point, signal, price) in enumerate(signals_detected, 1):
        signal_emoji = "🟢" if signal == "buy" else "🔴"
        print(f"  {i}. {signal_emoji} {signal.upper()} at point {point} (${price:.2f})")
    
    return len(signals_detected) > 0


def test_real_time_integration():
    """Test integration with real-time price feeds"""
    print("\n🌐 Testing Real-time Integration")
    print("=" * 40)
    
    try:
        from data.real_time_ema import RealTimeEMATracker
        
        # Create tracker
        tracker = RealTimeEMATracker(coins=["BTC"])
        
        def test_signal_handler(coin, ema_data, signal_info):
            print(f"✅ Signal handler working for {coin}")
            print(f"   Signal: {ema_data.signal.value}")
            print(f"   Price: ${ema_data.price:.2f}")
        
        # Add handler
        tracker.add_signal_callback("BTC", test_signal_handler)
        
        print("✅ Real-time EMA tracker created successfully")
        print("✅ Signal callback registered")
        print("✅ Integration test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


def test_historical_initialization():
    """Test initialization with historical data"""
    print("\n📈 Testing Historical Data Initialization")
    print("=" * 40)
    
    # Create sample historical DataFrame
    dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
    
    # Generate realistic price data with trend
    np.random.seed(42)
    base_price = 45000
    trend = np.linspace(0, 2000, 100)  # Upward trend
    noise = np.random.normal(0, 500, 100)  # Random noise
    prices = base_price + trend + noise
    
    df = pd.DataFrame({
        'timestamp': dates,
        'close': prices
    }).set_index('timestamp')
    
    print(f"📊 Created sample data: {len(df)} hourly candles")
    print(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    # Initialize calculator
    calculator = EMACalculator()
    calculator.initialize_from_historical_data(df)
    
    status = calculator.get_current_status()
    
    print(f"✅ Initialization complete")
    print(f"   EMA20: ${status['fast_ema']:.2f}")
    print(f"   EMA50: ${status['slow_ema']:.2f}")
    print(f"   Data points: {status['data_points']}")
    print(f"   Trend: {status['trend'].upper()}")
    
    return status['data_points'] > 0


def main():
    """Run all EMA tests"""
    print("🚀 EMA Calculator Test Suite")
    print("=" * 50)
    
    tests = [
        ("Basic EMA Calculations", test_ema_calculations),
        ("Real-time Integration", test_real_time_integration),
        ("Historical Initialization", test_historical_initialization)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print(f"\n📋 TEST SUMMARY")
    print("=" * 30)
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total:.1%}")
    
    if passed == total:
        print("🎉 All tests passed! EMA system is ready.")
    else:
        print("⚠️  Some tests failed. Check implementation.")


if __name__ == "__main__":
    main()
