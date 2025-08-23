import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta

class MarketDataProvider:
    """Handles market data fetching and processing"""
    
    def __init__(self, exchange_client):
        self.exchange = exchange_client
        self.logger = logging.getLogger(__name__)
        self.data_cache = {}
    
    def get_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> pd.DataFrame:
        """
        Fetch OHLCV data from Hyperliquid
        
        Args:
            symbol: Trading pair symbol (e.g., BTC/USDC)
            timeframe: Candlestick timeframe (1m, 5m, 1h, etc.)
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Convert symbol format (e.g., BTC/USDT -> BTC)
            coin = symbol.split('/')[0] if '/' in symbol else symbol
            
            # Get candle data from Hyperliquid
            candles = self.exchange.info.candles_snapshot({
                "coin": coin,
                "interval": timeframe,
                "startTime": None,  # Will get most recent data
                "endTime": None
            })
            
            if not candles:
                self.logger.warning(f"No candle data available for {coin}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = []
            for candle in candles:
                data.append([
                    candle['t'],  # timestamp (open time)
                    float(candle['o']),  # open
                    float(candle['h']),  # high
                    float(candle['l']),  # low
                    float(candle['c']),  # close
                    float(candle['v'])   # volume
                ])
            
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df.sort_index()  # Ensure chronological order
            
            self.logger.debug(f"Fetched {len(df)} candles for {coin}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for symbol"""
        try:
            ticker = self.exchange.get_ticker(symbol)
            return ticker.get('last')
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    def calculate_sma(self, data: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """Calculate Simple Moving Average"""
        return data[column].rolling(window=period).mean()
    
    def calculate_ema(self, data: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """Calculate Exponential Moving Average"""
        return data[column].ewm(span=period).mean()
    
    def calculate_rsi(self, data: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = data[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_bollinger_bands(self, data: pd.DataFrame, period: int = 20, std_dev: float = 2, column: str = 'close') -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = self.calculate_sma(data, period, column)
        std = data[column].rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }
    
    def calculate_macd(self, data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9, column: str = 'close') -> Dict[str, pd.Series]:
        """Calculate MACD indicator"""
        ema_fast = self.calculate_ema(data, fast, column)
        ema_slow = self.calculate_ema(data, slow, column)
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add common technical indicators to DataFrame"""
        if len(data) < 50:
            self.logger.warning("Insufficient data for technical indicators")
            return data
        
        # Moving averages
        data['sma_20'] = self.calculate_sma(data, 20)
        data['sma_50'] = self.calculate_sma(data, 50)
        data['ema_12'] = self.calculate_ema(data, 12)
        data['ema_26'] = self.calculate_ema(data, 26)
        
        # RSI
        data['rsi'] = self.calculate_rsi(data)
        
        # Bollinger Bands
        bb = self.calculate_bollinger_bands(data)
        data['bb_upper'] = bb['upper']
        data['bb_middle'] = bb['middle']
        data['bb_lower'] = bb['lower']
        
        # MACD
        macd = self.calculate_macd(data)
        data['macd'] = macd['macd']
        data['macd_signal'] = macd['signal']
        data['macd_histogram'] = macd['histogram']
        
        return data
    
    def get_market_data_with_indicators(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> pd.DataFrame:
        """Get market data with technical indicators"""
        data = self.get_ohlcv(symbol, timeframe, limit)
        if not data.empty:
            data = self.add_technical_indicators(data)
        return data