from hyperliquid.info import Info
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
import json
from lib.logger import get_market_data_logger
import time
from stockstats import StockDataFrame as Sdf
logger = get_market_data_logger()


class Coin:
    """Manages data storage for a specific coin across multiple subscription types"""
    def __init__(self, info: Info, coin_symbol: str, user_address: Optional[str] = None):
        self.coin_symbol = coin_symbol
        self.user_address = user_address
        self.info = info
        
        # Initialize DataFrames for each subscription type
        self.dataframes = {
            'ohclv': pd.DataFrame(columns=['openMs', 'closeMs', 'coin', 'interval', 'open', 'close', 'high', 'low', 'volume', 'numTrades']),

            'bbo': pd.DataFrame(columns=['timestamp', 'coin', 'time', 'bid_px', 'bid_sz', 'bid_n', 'ask_px', 'ask_sz', 'ask_n']),
            
            'technical_indicators': pd.DataFrame(columns=['timestamp', 'rsi_14', 'close_20_ema', 'close_50_ema', 'macd_20_50', 'macds_20_50'])
        }
        
    def subscribe_to_ohclv(self):
        """Subscribe to OHCLV data"""

        data = self.info.candles_snapshot(self.coin_symbol, "1m", 0, int(time.time() * 1000))
        formatted_data = []
        for candle in data:
            formatted_data.append({
                'openMs': candle["t"],
                'closeMs': candle["T"],
                'coin': candle["s"],
                'interval': candle["i"],
                'open': candle["o"],
                'close': candle["c"],
                'high': candle["h"],
                'low': candle["l"],
                'volume': candle["v"],
                'numTrades': candle["n"]
            })
        self.dataframes['ohclv'] = pd.DataFrame(formatted_data)
        print(f"Initial OHCLV data: {len(self.dataframes['ohclv'])}")
        self.info.subscribe({"type": "candle", "coin": self.coin_symbol, "interval": "1m"}, self.create_handler("candle"))
        
    def subscribe_to_bbo(self):
        """Subscribe to BBO data"""
        self.info.subscribe({"type": "bbo", "coin": self.coin_symbol}, self.create_handler("bbo"))
        
    def create_handler(self, subscription_type: str):
        """Create a handler function for a specific subscription type"""
        def handler(data):
            print(f"Received data for {self.coin_symbol}:{subscription_type}: {data}")
            try:
                timestamp = datetime.now()
                rows = self._parse_data(subscription_type, data, timestamp)
                
                if rows:
                    new_df = pd.DataFrame(rows)
                    
                    # For state-based subscriptions, keep only the latest entry
                    if subscription_type in ['bbo']:
                        # Replace existing data completely for state-based subscriptions
                        self.dataframes[subscription_type] = new_df
                    else:
                        # For historical data (trades, candles), append new data
                        # Map 'candle' subscription to 'ohclv' dataframe
                        df_key = 'ohclv' if subscription_type == 'candle' else subscription_type
                        self.dataframes[df_key] = pd.concat(
                            [self.dataframes[df_key], new_df], 
                            ignore_index=True
                        )
                        
                        # Update technical indicators when new candle data is received
                        if subscription_type == 'candle':
                            self.update_technical_indicators()
                
                logger.debug(f"[{self.coin_symbol}:{subscription_type}] Received data - {len(rows) if rows else 0} records")
                
            except Exception as e:
                logger.error(f"Error processing {self.coin_symbol}:{subscription_type} data: {e}")
                logger.debug(f"Raw data: {data}")
        
        return handler
    
    def _parse_data(self, subscription_type: str, data: Any, timestamp: datetime) -> List[Dict]:
        """Parse data based on subscription type and return list of rows for DataFrame"""
        
        if subscription_type == 'l2Book':
            return [{
                'timestamp': timestamp,
                'coin': data.get('coin', ''),
                'levels': json.dumps(data.get('levels', [])),
                'time': data.get('time', 0)
            }]
            
        elif subscription_type == 'trades':
            trades = data if isinstance(data, list) else [data]
            rows = []
            for trade in trades:
                rows.append({
                    'timestamp': timestamp,
                    'coin': trade.get('coin', ''),
                    'side': trade.get('side', ''),
                    'px': trade.get('px', ''),
                    'sz': trade.get('sz', ''),
                    'hash': trade.get('hash', ''),
                    'time': trade.get('time', 0),
                    'tid': trade.get('tid', 0),
                    'users': json.dumps(trade.get('users', []))
                })
            return rows
            
        elif subscription_type == 'candle':
            candles = data if isinstance(data, list) else [data]
            rows = []
            for candle in candles:
                rows.append({
                    'openMs': candle.get('t', 0),
                    'closeMs': candle.get('T', 0),
                    'coin': candle.get('s', ''),
                    'interval': candle.get('i', ''),
                    'open': candle.get('o', 0),
                    'close': candle.get('c', 0),
                    'high': candle.get('h', 0),
                    'low': candle.get('l', 0),
                    'volume': candle.get('v', 0),
                    'numTrades': candle.get('n', 0)
                })
            return rows
            
        elif subscription_type == 'bbo':
            bbo_data = data.get('bbo', [None, None])
            bid, ask = bbo_data
            return [{
                'timestamp': timestamp,
                'coin': data.get('coin', ''),
                'time': data.get('time', 0),
                'bid_px': bid.get('px', '') if bid else '',
                'bid_sz': bid.get('sz', '') if bid else '',
                'bid_n': bid.get('n', 0) if bid else 0,
                'ask_px': ask.get('px', '') if ask else '',
                'ask_sz': ask.get('sz', '') if ask else '',
                'ask_n': ask.get('n', 0) if ask else 0
            }]
            
        elif subscription_type == 'activeAssetCtx':
            ctx = data.get('ctx', {})
            return [{
                'timestamp': timestamp,
                'coin': data.get('coin', ''),
                'dayNtlVlm': ctx.get('dayNtlVlm', 0),
                'prevDayPx': ctx.get('prevDayPx', 0),
                'markPx': ctx.get('markPx', 0),
                'midPx': ctx.get('midPx', 0),
                'funding': ctx.get('funding', 0),
                'openInterest': ctx.get('openInterest', 0),
                'oraclePx': ctx.get('oraclePx', 0),
                'circulatingSupply': ctx.get('circulatingSupply', 0)
            }]
            
        elif subscription_type == 'activeAssetData':
            return [{
                'timestamp': timestamp,
                'user': data.get('user', ''),
                'coin': data.get('coin', ''),
                'leverage': json.dumps(data.get('leverage', {})),
                'maxTradeSzs': json.dumps(data.get('maxTradeSzs', [])),
                'availableToTrade': json.dumps(data.get('availableToTrade', []))
            }]
        
        return []
    
    def calculate_rsi(self) -> Optional[float]:
        """Calculate RSI using stockstats methodology (14-period)"""
        try:
            ohclv_df = self.get_dataframe('ohclv')
            if ohclv_df.empty or len(ohclv_df) < 15:  # Need at least 15 periods for RSI calculation
                return None
            
            # Convert to format expected by stockstats
            # StockStats expects columns: open, high, low, close, volume
            stock_df = ohclv_df[['open', 'high', 'low', 'close', 'volume']].copy()
            stock_df = stock_df.astype(float)
            
            # Create StockDataFrame
            stock = Sdf.retype(stock_df)
            
            # Calculate RSI (this automatically calculates rsi_14)
            rsi_series = stock['rsi_14']
            
            # Return the latest RSI value
            if not rsi_series.empty and not pd.isna(rsi_series.iloc[-1]):
                return float(rsi_series.iloc[-1])
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating RSI for {self.coin_symbol}: {e}")
            return None
    
    def calculate_macd(self) -> tuple[Optional[float], Optional[float]]:
        """Calculate MACD using 20/50 EMA periods with 9-period signal line"""
        try:
            ohclv_df = self.get_dataframe('ohclv')
            if ohclv_df.empty or len(ohclv_df) < 60:  # Need at least 60 periods for 50 EMA + signal calculation
                return None, None
            
            # Convert to format expected by stockstats
            stock_df = ohclv_df[['open', 'high', 'low', 'close', 'volume']].copy()
            stock_df = stock_df.astype(float)
            
            # Create StockDataFrame
            stock = Sdf.retype(stock_df)
            
            # Calculate EMAs (this automatically calculates close_20_ema and close_50_ema)
            ema_20 = stock['close_20_ema']
            ema_50 = stock['close_50_ema']
            
            # Calculate MACD line (20 EMA - 50 EMA)
            stock['macd_20_50'] = ema_20 - ema_50
            
            # Calculate MACD signal line (9-period EMA of MACD line)
            stock['macds_20_50'] = stock['macd_20_50'].ewm(span=9).mean()
            
            # Get latest values
            latest_macd = stock['macd_20_50'].iloc[-1]
            latest_signal = stock['macds_20_50'].iloc[-1]
            
            # Return None if values are NaN
            if pd.isna(latest_macd) or pd.isna(latest_signal):
                return None, None
                
            return float(latest_macd), float(latest_signal)
            
        except Exception as e:
            logger.error(f"Error calculating MACD for {self.coin_symbol}: {e}")
            return None, None
    
    def update_technical_indicators(self):
        """Update the technical indicators dataframe with latest RSI and MACD values"""
        try:
            print(f"Updating technical indicators for {self.coin_symbol}")
            # Calculate current indicators
            rsi = self.calculate_rsi()
            macd, macd_signal = self.calculate_macd()
            
            if rsi is None and macd is None:
                return  # No data to update
            
            # Get the current OHCLV data to calculate EMAs for storage
            ohclv_df = self.get_dataframe('ohclv')
            if ohclv_df.empty:
                return
                
            # Convert to stockstats format to get EMA values
            stock_df = ohclv_df[['open', 'high', 'low', 'close', 'volume']].copy()
            stock_df = stock_df.astype(float)
            stock = Sdf.retype(stock_df)
            
            # Get latest EMA values
            ema_20 = stock['close_20_ema'].iloc[-1] if not stock['close_20_ema'].empty else None
            ema_50 = stock['close_50_ema'].iloc[-1] if not stock['close_50_ema'].empty else None
            
            # Create new row for technical indicators
            new_row = {
                'timestamp': datetime.now(),
                'rsi_14': rsi,
                'close_20_ema': ema_20,
                'close_50_ema': ema_50,
                'macd_20_50': macd,
                'macds_20_50': macd_signal
            }
            
            new_df = pd.DataFrame([new_row])
            
            # Update the technical indicators dataframe
            if self.dataframes['technical_indicators'].empty:
                self.dataframes['technical_indicators'] = new_df
            else:
                self.dataframes['technical_indicators'] = pd.concat(
                    [self.dataframes['technical_indicators'], new_df], 
                    ignore_index=True
                )
            print(f"Updated technical indicators for {self.coin_symbol} - RSI: {rsi}, MACD: {macd}")
            logger.debug(f"[{self.coin_symbol}] Updated technical indicators - RSI: {rsi}, MACD: {macd}")
            
        except Exception as e:
            logger.error(f"Error updating technical indicators for {self.coin_symbol}: {e}")
    
    def get_dataframe(self, subscription_type: str) -> pd.DataFrame:
        """Get DataFrame for a specific subscription type"""
        return self.dataframes.get(subscription_type, pd.DataFrame())
    
    def get_all_dataframes(self) -> Dict[str, pd.DataFrame]:
        """Get all DataFrames for this coin"""
        return self.dataframes.copy()
    
    def get_latest_rsi(self) -> Optional[float]:
        """Get the latest RSI value from technical indicators"""
        indicators_df = self.get_dataframe('technical_indicators')
        if not indicators_df.empty and 'rsi_14' in indicators_df.columns:
            latest_rsi = indicators_df['rsi_14'].iloc[-1]
            return float(latest_rsi) if not pd.isna(latest_rsi) else None
        return None
    
    def get_latest_macd(self) -> tuple[Optional[float], Optional[float]]:
        """Get the latest MACD and signal values from technical indicators"""
        indicators_df = self.get_dataframe('technical_indicators')
        if not indicators_df.empty and 'macd_20_50' in indicators_df.columns and 'macds_20_50' in indicators_df.columns:
            latest_macd = indicators_df['macd_20_50'].iloc[-1]
            latest_signal = indicators_df['macds_20_50'].iloc[-1]
            
            macd_val = float(latest_macd) if not pd.isna(latest_macd) else None
            signal_val = float(latest_signal) if not pd.isna(latest_signal) else None
            
            return macd_val, signal_val
        return None, None

    def get_latest_price(self) -> Optional[float]:
        """Get the latest price from BBO data"""
        bbo_df = self.get_dataframe('bbo')
        if not bbo_df.empty:
            latest_row = bbo_df.iloc[-1]
            # Use mid-point of bid-ask spread
            bid_px = pd.to_numeric(latest_row['bid_px'], errors='coerce')
            ask_px = pd.to_numeric(latest_row['ask_px'], errors='coerce')
            if not pd.isna(bid_px) and not pd.isna(ask_px):
                return (bid_px + ask_px) / 2
        return None
    
    def get_trade_stats(self) -> Dict[str, Any]:
        """Get trading statistics for this coin"""
        trades_df = self.get_dataframe('trades')
        if trades_df.empty:
            return {}
        
        trades_df['px_float'] = pd.to_numeric(trades_df['px'], errors='coerce')
        trades_df['sz_float'] = pd.to_numeric(trades_df['sz'], errors='coerce')
        
        stats = {
            'total_trades': len(trades_df),
            'total_volume': trades_df['sz_float'].sum(),
            'avg_price': trades_df['px_float'].mean(),
            'min_price': trades_df['px_float'].min(),
            'max_price': trades_df['px_float'].max(),
            'latest_price': trades_df['px_float'].iloc[-1] if not trades_df.empty else None
        }
        
        return {k: v for k, v in stats.items() if not pd.isna(v)}
    
    def print_summary(self):
        """Print summary for this coin"""
        logger.info(f"{self.coin_symbol} Data Summary:")
        logger.info("-" * 40)
        
        for sub_type, df in self.dataframes.items():
            count = len(df)
            latest_time = df['timestamp'].max() if not df.empty and 'timestamp' in df.columns else 'N/A'
            logger.info(f"  {sub_type:<20}: {count:>6} records (latest: {latest_time})")
        
        # Show current price if available
        latest_price = self.get_latest_price()
        if latest_price:
            logger.info(f"  {'Latest Price':<20}: ${latest_price:.4f}")
    
    def save_to_csv(self, prefix: str = None):
        """Save all DataFrames to CSV files"""
        if prefix is None:
            prefix = f"{self.coin_symbol.lower()}"
            
        for sub_type, df in self.dataframes.items():
            if not df.empty:
                filename = f"{prefix}_{sub_type}.csv"
                df.to_csv(filename, index=False)
                logger.success(f"Saved {len(df)} {self.coin_symbol} {sub_type} records to {filename}")
