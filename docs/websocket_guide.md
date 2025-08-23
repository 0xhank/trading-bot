# Hyperliquid WebSocket Guide

## Overview
This guide explains how to use the Hyperliquid WebSocket client for real-time data feeds in your trading bot.

## WebSocket Client Features

### 🔗 **Connection Management**
- Automatic connection to Hyperliquid WebSocket API
- Support for both testnet and mainnet
- Automatic reconnection with exponential backoff
- Heartbeat/ping mechanism to maintain connection

### 📊 **Data Subscriptions**
- **All Mids**: Real-time mid prices for all assets
- **Trades**: Live trade data for specific coins
- **L2 Book**: Order book updates
- **Candles**: OHLCV candle data
- **User Fills**: Your trade executions (requires account address)
- **User Orders**: Your order updates (requires account address)

### 🛠 **Custom Handlers**
- Register custom callback functions for specific data types
- Process data in real-time as it arrives
- Flexible event-driven architecture

## Quick Start

### 1. Basic Usage
```python
from data.websocket_client import HyperliquidWebSocketClient

# Create client
ws_client = HyperliquidWebSocketClient()

# Connect
ws_client.connect()

# Subscribe to data feeds
ws_client.subscribe_all_mids()           # All prices
ws_client.subscribe_trades("BTC")        # BTC trades
ws_client.subscribe_l2_book("ETH")       # ETH order book

# Keep running
import time
while True:
    time.sleep(1)
```

### 2. Custom Handlers
```python
def my_trade_handler(channel, data):
    trades = data.get('data', [])
    for trade in trades:
        print(f"Trade: {trade['coin']} - {trade['side']} {trade['sz']} @ ${trade['px']}")

# Subscribe with custom handler
ws_client.subscribe_trades("BTC", callback=my_trade_handler)
```

## Available Subscriptions

### 📈 **Price Data**
```python
# All mid prices (updated frequently)
ws_client.subscribe_all_mids()

# Individual coin trades
ws_client.subscribe_trades("BTC")
ws_client.subscribe_trades("ETH")
```

### 📖 **Order Book**
```python
# L2 order book (up to 20 levels)
ws_client.subscribe_l2_book("BTC")
```

### 🕯 **Candle Data**
```python
# Supported intervals: "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "8h", "12h", "1d", "3d", "1w", "1M"
ws_client.subscribe_candles("BTC", "1m")
ws_client.subscribe_candles("ETH", "5m")
```

### 👤 **User Data** (requires account address)
```python
# Your trade fills
ws_client.subscribe_user_fills("0x1234...")

# Your order updates
ws_client.subscribe_user_orders("0x1234...")
```

## Example Scripts

### 🚀 **Simple Example**
```bash
python3 examples/simple_websocket.py
```
- Basic connection and subscription
- Prints all incoming data
- Good for testing connectivity

### 🎯 **Advanced Demo**
```bash
python3 examples/websocket_demo.py
```
- Multiple demo modes
- Custom handlers example
- Interactive menu

## Data Format Examples

### All Mids Response
```json
{
  "channel": "allMids",
  "data": {
    "mids": {
      "BTC": "45123.45",
      "ETH": "2345.67",
      "SOL": "123.45"
    }
  }
}
```

### Trade Response
```json
{
  "channel": "trades",
  "data": [
    {
      "coin": "BTC",
      "side": "B",
      "px": "45123.45",
      "sz": "0.1",
      "time": 1698765432000,
      "hash": "0x...",
      "tid": 123456
    }
  ]
}
```

### L2 Book Response
```json
{
  "channel": "l2Book",
  "data": {
    "coin": "BTC",
    "time": 1698765432000,
    "levels": [
      [{"px": "45123.0", "sz": "0.5", "n": 3}],  // Bids
      [{"px": "45124.0", "sz": "0.3", "n": 2}]   // Asks
    ]
  }
}
```

## Configuration

The WebSocket client uses your existing configuration:

```python
# config/settings.py
SANDBOX = True  # Uses testnet WebSocket if True
```

- **Testnet**: `wss://api.hyperliquid-testnet.xyz/ws`
- **Mainnet**: `wss://api.hyperliquid.xyz/ws`

## Error Handling

### Connection Issues
- Automatic reconnection with exponential backoff
- Maximum 5 reconnection attempts
- Graceful degradation on persistent failures

### Message Handling
- JSON parsing error handling
- Individual message error isolation
- Comprehensive logging

## Best Practices

### 🔄 **Connection Management**
- Always call `disconnect()` when shutting down
- Use signal handlers for graceful shutdown
- Monitor connection status

### 📊 **Data Processing**
- Use custom handlers for specific data processing
- Avoid blocking operations in handlers
- Consider using queues for heavy processing

### 🚨 **Error Handling**
- Implement try-catch in custom handlers
- Log errors appropriately
- Have fallback strategies for data outages

## Integration with Trading Bot

### Example: Price Monitoring
```python
class PriceMonitor:
    def __init__(self):
        self.ws_client = HyperliquidWebSocketClient()
        self.current_prices = {}
    
    def price_handler(self, channel, data):
        mids = data.get('data', {}).get('mids', {})
        self.current_prices.update(mids)
        
        # Trigger trading logic
        self.check_trading_signals()
    
    def start(self):
        self.ws_client.connect()
        self.ws_client.subscribe_all_mids(callback=self.price_handler)
```

### Example: Trade Monitoring
```python
def trade_handler(channel, data):
    trades = data.get('data', [])
    for trade in trades:
        # Analyze market sentiment
        volume = float(trade['sz'])
        price = float(trade['px'])
        
        # Update market indicators
        update_volume_profile(trade['coin'], volume, price)
```

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   - Check internet connectivity
   - Verify WebSocket URL
   - Check firewall settings

2. **No Data Received**
   - Verify subscription messages
   - Check coin symbols (use correct format)
   - Monitor connection status

3. **High CPU Usage**
   - Optimize message handlers
   - Avoid heavy processing in callbacks
   - Use background threads for intensive tasks

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show detailed WebSocket messages
ws_client = HyperliquidWebSocketClient()
```

## Performance Considerations

- **Message Rate**: Up to 100+ messages per second during active trading
- **Memory Usage**: Minimal, messages are processed immediately
- **CPU Usage**: Low for basic message handling
- **Network**: ~1-10 KB/s depending on subscriptions

## Next Steps

1. Start with `examples/simple_websocket.py` to test connectivity
2. Experiment with different subscriptions
3. Implement custom handlers for your specific needs
4. Integrate with your existing trading logic
5. Consider implementing data persistence for analysis
