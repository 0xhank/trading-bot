#!/usr/bin/env python3
"""
Quick WebSocket Test - 10 seconds of live data
"""

import sys
import os
import time
import threading

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.websocket_client import HyperliquidWebSocketClient

def quick_test():
    print("🚀 Quick WebSocket Test (10 seconds)")
    print("=" * 40)
    
    ws_client = HyperliquidWebSocketClient()
    
    try:
        # Connect
        print("📡 Connecting...")
        ws_client.connect()
        print("✅ Connected!")
        
        # Subscribe to BTC trades
        print("📈 Subscribing to BTC trades...")
        ws_client.subscribe_trades("BTC")
        
        # Subscribe to price updates
        print("💰 Subscribing to all prices...")
        ws_client.subscribe_all_mids()
        
        print("\n🔴 LIVE DATA:")
        print("-" * 40)
        
        # Run for 10 seconds
        time.sleep(10)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("\n🛑 Stopping...")
        ws_client.disconnect()
        print("✅ Test complete!")

if __name__ == "__main__":
    quick_test()
