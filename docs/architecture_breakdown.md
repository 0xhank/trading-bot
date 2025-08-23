# Architecture Breakdown for Hyperliquid Trading Bot

Based on the CLAUDE.md specification for the Hyperliquid Moving Average Crossover Trading Bot, here's a strategic breakdown of how we should build it:

## Core Architecture Components

### 1. **Data Management Layer**
- **Hyperliquid API Integration**: Replace ccxt with hyperliquid-python-sdk
- **Real-time Data Pipeline**: Implement WebSocket connections for live price feeds
- **Technical Indicators**: Focus on EMA calculations (20/50 periods) vs generic indicators
- **Candle Data Management**: Use `info.candles_snapshot()` for historical data

### 2. **Strategy Engine** 
- **Crossover Detection**: Implement precise EMA crossover logic with confirmation
- **Signal Validation**: Add signal strength and momentum filters
- **Timeframe Management**: Focus on 1-hour candles with configurable periods

### 3. **Risk Management System** (Critical Component)
- **Leverage Integration**: 2-3x leverage calculations with margin monitoring
- **Position Sizing**: 2% base position with leverage multiplier (4-6% effective exposure)
- **Liquidation Monitoring**: Real-time tracking with 50% safety buffer
- **Stop Loss/Take Profit**: 2% SL / 4% TP (2:1 risk/reward)
- **Daily Limits**: Max 5 trades, 10% max drawdown protection

### 4. **Order Management**
- **Hyperliquid-Specific Orders**: Leverage market orders and stop orders
- **Position Monitoring**: Track margin ratios and liquidation prices  
- **Emergency Controls**: Kill switch and auto-deleveraging

### 5. **Configuration Management**
- **Environment-Based Config**: Trading pairs, leverage, risk parameters
- **Paper Trading Mode**: Safe testing environment
- **Dynamic Parameter Adjustment**: Based on market conditions

## Implementation Approach

### Phase 1: Foundation
1. **Replace Exchange Layer**: Swap ccxt for Hyperliquid SDK
2. **Simplify Structure**: Focus on specific components vs generic framework
3. **Add Leverage Support**: Margin calculations and liquidation monitoring

### Phase 2: Strategy Implementation  
1. **EMA Crossover Logic**: Implement precise crossover detection
2. **Risk Management Integration**: Position sizing with leverage
3. **Order Execution**: Hyperliquid-specific order placement

### Phase 3: Safety & Monitoring
1. **Liquidation Protection**: Real-time margin monitoring
2. **Kill Switch**: Emergency position closure
3. **Performance Tracking**: P&L and trade analytics

## Key Differences from Current Setup

**Need to Add:**
- Hyperliquid SDK integration
- Leverage and margin calculations
- Liquidation price monitoring
- EMA-specific crossover detection
- Daily trade limits
- Emergency controls

**Can Simplify:**
- Remove generic exchange support (focus on Hyperliquid only)
- Reduce technical indicators to just EMAs
- Streamline to 1-hour timeframe focus

**Critical Safety Features:**
- Paper trading mode
- Margin ratio monitoring
- Auto-deleveraging logic
- Kill switch functionality

## File Structure Modifications Needed

```
trading_bot/
├── config/
│   ├── __init__.py
│   ├── settings.py              # Update for Hyperliquid config
│   └── trading_config.py        # New: Trading-specific parameters
├── core/
│   ├── __init__.py
│   ├── hyperliquid_client.py    # New: Replace exchange.py
│   ├── portfolio.py             # Update: Add leverage support
│   └── risk_manager.py          # New: Dedicated risk management
├── strategies/
│   ├── __init__.py
│   ├── base_strategy.py
│   └── ma_crossover.py          # New: EMA crossover strategy
├── data/
│   ├── __init__.py
│   └── hyperliquid_data.py      # New: Replace market_data.py
├── orders/                      # New: Order management
│   ├── __init__.py
│   └── order_manager.py
├── utils/
│   ├── __init__.py
│   ├── helpers.py
│   └── performance.py           # New: P&L tracking
├── docs/
│   ├── CLAUDE.md
│   └── architecture_breakdown.md
├── tests/
├── logs/
├── .env
├── requirements.txt             # Update: Add hyperliquid-python-sdk
└── main.py                      # Update: New main loop
```

The current setup provides a good foundation, but needs significant modifications for Hyperliquid's leveraged perpetuals trading with proper risk management.