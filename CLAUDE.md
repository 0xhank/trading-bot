# Hyperliquid Moving Average Crossover Trading Bot Specification

## Overview
A simple automated trading bot that executes long/short positions on Hyperliquid perpetuals based on moving average crossovers with integrated risk management.

## Trading Strategy
**Signal Generation:**
- **Long Signal:** 20-period EMA crosses above 50-period EMA
- **Short Signal:** 20-period EMA crosses below 50-period EMA
- **Exit:** Opposite crossover or stop loss/take profit hit

**Timeframe:** 1-hour candles (adjustable)

## Risk Management Rules
- **Position Size:** 2% of total account balance per trade (base position)
- **Leverage:** 2-3x leverage on positions for enhanced returns
- **Effective Exposure:** 4-6% of account balance per trade (2% × 2-3x leverage)
- **Stop Loss:** 2% from entry price (liquidation risk ~6% with 3x leverage)
- **Take Profit:** 4% from entry price (2:1 risk/reward ratio)
- **Max Daily Trades:** 5 trades maximum
- **Max Drawdown:** Stop trading if account drops 10% from starting balance
- **Leverage Safety:** Monitor margin ratio, maintain >50% buffer from liquidation

## Technical Architecture

### 1. Dependencies & Setup
```python
# Required libraries
hyperliquid-python-sdk
pandas
numpy
python-dotenv
logging
time
```

### 2. Core Components

#### Data Manager (`data_manager.py`)
- Fetch historical OHLCV data using `info.candles_snapshot()`
- Real-time price updates via WebSocket or polling
- Calculate 20 EMA and 50 EMA using pandas
- Detect crossover events

#### Strategy Engine (`strategy.py`)
- Moving average calculation and crossover detection
- Signal generation (LONG/SHORT/EXIT/HOLD)
- Entry/exit logic with confirmation

#### Risk Manager (`risk_manager.py`)
- Position sizing calculation with leverage (2% base × 2-3x leverage)
- Dynamic leverage selection based on market conditions/volatility
- Stop loss and take profit price calculation
- Liquidation price monitoring and margin ratio tracking
- Daily trade limit enforcement
- Maximum drawdown monitoring
- Account balance and margin requirement tracking
- Emergency deleveraging logic

#### Order Manager (`order_manager.py`)
- Interface with Hyperliquid Exchange API
- Market order execution for entries
- Stop loss and take profit order placement
- Position monitoring and management
- Order status tracking

#### Main Bot (`main.py`)
- Orchestrates all components
- Main trading loop with error handling
- Logging and monitoring
- Configuration management

### 3. Configuration (`config.py`)
```python
TRADING_CONFIG = {
    'symbol': 'ETH-USD',
    'fast_ma_period': 20,
    'slow_ma_period': 50,
    'timeframe': '1h',
    'position_size_pct': 0.02,  # Base position size
    'leverage': 3,  # 2-3x leverage (adjustable)
    'stop_loss_pct': 0.02,
    'take_profit_pct': 0.04,
    'max_daily_trades': 5,
    'max_drawdown_pct': 0.10,
    'liquidation_buffer': 0.50,  # Maintain 50% buffer from liquidation
    'max_margin_usage': 0.70,  # Don't use more than 70% of available margin
}
```

### 4. Hyperliquid SDK Integration

#### Authentication
- Store API keys in `.env` file
- Initialize `Exchange` class for trading operations
- Initialize `Info` class for market data

#### Key API Endpoints Used
- `info.user_state()` - Get account balance, positions, and margin info
- `info.candles_snapshot()` - Historical price data
- `exchange.market_order()` - Execute leveraged trades
- `exchange.order()` - Place limit/stop orders with leverage
- `info.open_orders()` - Monitor order status
- `exchange.update_leverage()` - Adjust position leverage
- Margin and liquidation price calculations

### 5. Data Flow
1. **Initialization:** Load config, authenticate with Hyperliquid
2. **Data Collection:** Fetch latest candles and update moving averages
3. **Signal Generation:** Check for crossover events
4. **Risk Check:** Validate trade against risk parameters and margin requirements
5. **Leverage Calculation:** Determine optimal leverage (2-3x) based on volatility
6. **Order Execution:** Place leveraged market order if signal valid
7. **Position Management:** Monitor stops, profits, and liquidation risk
8. **Loop:** Wait for next timeframe, repeat

### 6. Error Handling & Monitoring
- API connection failures with retry logic
- Insufficient balance and margin checks
- Liquidation risk monitoring and alerts
- Order rejection handling
- Leverage adjustment failures
- Logging all trades and decisions
- Real-time margin ratio monitoring
- Daily performance reporting

### 7. Backtesting Module (`backtest.py`)
- Historical strategy performance testing
- Key metrics calculation (win rate, Sharpe ratio, max drawdown)
- Performance visualization
- Strategy optimization

## Implementation Steps

1. **Environment Setup**
   - Install dependencies
   - Configure API credentials
   - Test connection to Hyperliquid

2. **Data Pipeline**
   - Implement candle data fetching
   - Build moving average calculation
   - Test crossover detection

3. **Trading Logic**
   - Build strategy engine
   - Implement risk management
   - Test order execution on testnet

4. **Integration Testing**
   - Paper trading mode
   - Monitor for 24-48 hours
   - Validate all risk controls

5. **Live Deployment**
   - Start with minimal position sizes
   - Gradual scaling based on performance
   - Continuous monitoring and adjustment

## Safety Features
- **Kill Switch:** Manual stop functionality with emergency position closure
- **Paper Trading Mode:** Test without real money
- **Position Limits:** Never exceed configured risk levels
- **Liquidation Monitoring:** Real-time liquidation price tracking
- **Margin Alerts:** Warnings when approaching margin limits
- **Auto-Deleveraging:** Reduce leverage if margin ratio becomes dangerous
- **API Rate Limiting:** Respect exchange limits
- **Graceful Shutdown:** Close positions cleanly on exit

## Performance Tracking
- Track P&L per trade and overall
- Monitor win rate and average trade duration
- Daily/weekly performance reports
- Strategy effectiveness metrics

This specification provides a foundation for a production-ready trading bot while maintaining simplicity for learning purposes.