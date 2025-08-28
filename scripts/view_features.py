import ccxt
import json
from stockstats import StockDataFrame as Sdf
import pandas as pd
import time

def get_historical_data(exchange, coin_pair, timeframe):
    """Get Historical data (ohlcv) from a coin_pair
    """
    # optional: exchange.fetch_ohlcv(coin_pair, '1h', since)
    data = exchange.fetch_ohlcv(coin_pair, timeframe)
    # update timestamp to human readable timestamp
    data = [[exchange.iso8601(candle[0])] + candle[1:] for candle in data]
    header = ['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
    df = pd.DataFrame(data, columns=header)
    return df


def create_stock(historical_data):
    """Create StockData from historical data 
    """
    stock  = Sdf.retype(historical_data)
    return stock


def calculate_rsi_and_analyze(stock_data, coin_pair):
    """Calculate RSI and analyze overbought/oversold conditions
    """
    try:
        # Calculate RSI
        stock_data['rsi_14']
        
        # Check if RSI data is available and valid
        if 'rsi_14' not in stock_data.columns or stock_data['rsi_14'].empty or len(stock_data['rsi_14'].dropna()) == 0:
            print(f"{coin_pair} - Insufficient data for RSI calculation")
            return None
        
        print(stock_data)
        
        # Get most recent RSI value of our data frame
        # In our case this represents the RSI of the last 1h
        last_rsi = stock_data['rsi_14'].iloc[-1]
        
        # Check if RSI value is NaN
        if pd.isna(last_rsi):
            print(f"{coin_pair} - RSI calculation returned NaN (insufficient data)")
            return None
        
        print(f"{coin_pair} - Last RSI: {last_rsi}")
        
        # Traditional interpretation: RSI >= 70 overbought, RSI <= 30 oversold
        if last_rsi >= 70:
            print(f"{coin_pair} is OVERBOUGHT (RSI: {last_rsi})")
        elif last_rsi <= 30:
            print(f"{coin_pair} is OVERSOLD (RSI: {last_rsi})")
        else:
            print(f"{coin_pair} is NEUTRAL (RSI: {last_rsi})")
        
        return last_rsi
    
    except (IndexError, KeyError) as e:
        print(f"{coin_pair} - Error calculating RSI: {e} (likely insufficient data)")
        return None


def calculate_macd_and_analyze(stock_data, coin_pair):
    """Calculate MACD with periods 20 and 50
    """
    try:
        # Calculate EMAs first
        stock_data['close_20_ema']
        stock_data['close_50_ema']
        
        # Check if EMA data is available
        if 'close_20_ema' not in stock_data.columns or 'close_50_ema' not in stock_data.columns:
            print(f"{coin_pair} - EMA data not available for MACD calculation")
            return None, None
        
        # Calculate MACD with custom periods (20 and 50)
        stock_data['macd_20_50'] = stock_data['close_20_ema'] - stock_data['close_50_ema']
        stock_data['macds_20_50'] = stock_data['macd_20_50'].ewm(span=9).mean()
        
        # Check if we have valid MACD data
        if len(stock_data['macd_20_50'].dropna()) == 0 or len(stock_data['macds_20_50'].dropna()) == 0:
            print(f"{coin_pair} - Insufficient data for MACD calculation")
            return None, None
        
        print(stock_data[['macd_20_50', 'macds_20_50']].tail())
        
        # Get most recent MACD values
        last_macd = stock_data['macd_20_50'].iloc[-1]
        last_macds = stock_data['macds_20_50'].iloc[-1]
        
        # Check if values are NaN
        if pd.isna(last_macd) or pd.isna(last_macds):
            print(f"{coin_pair} - MACD calculation returned NaN (insufficient data)")
            return None, None
        
        print(f"{coin_pair} - MACD: {last_macd:.4f}, MACDS: {last_macds:.4f}")
        
        # Analyze MACD crossover signals
        if last_macd > last_macds:
            print(f"{coin_pair} - MACD above signal line (BULLISH)")
        else:
            print(f"{coin_pair} - MACD below signal line (BEARISH)")
        
        return last_macd, last_macds
    
    except (IndexError, KeyError) as e:
        print(f"{coin_pair} - Error calculating MACD: {e} (likely insufficient data)")
        return None, None

def main():

    exchange = ccxt.hyperliquid()
    exchange.load_markets()

    pairs = ['UETH/USDC', "UBTC/USDC","USOL/USDC", "HYPE/USDC"]

    for coin_pair in pairs:
        # respect rate limit
        time.sleep (exchange.rateLimit / 1000)
        data = get_historical_data(exchange, coin_pair, '1h')
        stock_data = create_stock(data)
        
        # Calculate RSI and analyze
        last_rsi = calculate_rsi_and_analyze(stock_data, coin_pair)
        
        # Calculate MACD and analyze
        last_macd, last_macds = calculate_macd_and_analyze(stock_data, coin_pair)


if __name__ == "__main__":
    main()