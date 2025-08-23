import json
import logging
import threading
import time
from typing import Dict, Callable, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from data.websocket_client import HyperliquidWebSocketClient
from data.ema_calculator import EMACalculator, EMAData, CrossoverSignal


@dataclass
class PriceUpdate:
    """Real-time price update from WebSocket"""
    coin: str
    price: float
    timestamp: datetime
    source: str  # 'trade' or 'mid'


class RealTimeEMATracker:
    """
    Real-time EMA tracking system that integrates with WebSocket price feeds
    
    Features:
    - Tracks multiple coins simultaneously
    - Real-time EMA calculations from live price data
    - Signal generation and alerting
    - Performance monitoring
    """
    
    def __init__(self, coins: list = None):
        self.coins = coins or ["BTC", "ETH", "SOL"]
        self.logger = logging.getLogger(__name__)
        
        # WebSocket client
        self.ws_client = HyperliquidWebSocketClient()
        
        # EMA calculators for each coin
        self.ema_calculators: Dict[str, EMACalculator] = {}
        for coin in self.coins:
            self.ema_calculators[coin] = EMACalculator()
        
        # Signal callbacks
        self.signal_callbacks: Dict[str, list] = {}
        self.price_callbacks: Dict[str, list] = {}
        
        # State tracking
        self.is_running = False
        self.last_prices: Dict[str, float] = {}
        self.last_updates: Dict[str, datetime] = {}
        
        # Performance stats
        self.stats = {
            'total_updates': 0,
            'signals_generated': 0,
            'start_time': None,
            'coins_tracking': len(self.coins)
        }
        
        # Threading
        self.update_thread = None
        self.stop_event = threading.Event()
    
    def add_signal_callback(self, coin: str, callback: Callable):
        """
        Add callback function for signal events
        
        Args:
            coin: Coin symbol (e.g., 'BTC')
            callback: Function to call when signal is generated
                     callback(coin, ema_data, signal_info)
        """
        if coin not in self.signal_callbacks:
            self.signal_callbacks[coin] = []
        self.signal_callbacks[coin].append(callback)
        self.logger.info(f"Added signal callback for {coin}")
    
    def add_price_callback(self, coin: str, callback: Callable):
        """
        Add callback function for price updates
        
        Args:
            coin: Coin symbol
            callback: Function to call on price update
                     callback(coin, price_update)
        """
        if coin not in self.price_callbacks:
            self.price_callbacks[coin] = []
        self.price_callbacks[coin].append(callback)
        self.logger.info(f"Added price callback for {coin}")
    
    def start(self, use_historical_init: bool = True):
        """
        Start real-time EMA tracking
        
        Args:
            use_historical_init: Whether to initialize EMAs with historical data
        """
        if self.is_running:
            self.logger.warning("EMA tracker is already running")
            return
        
        self.logger.info(f"Starting real-time EMA tracking for {self.coins}")
        self.stats['start_time'] = datetime.utcnow()
        
        try:
            # Initialize historical data if requested
            if use_historical_init:
                self._initialize_historical_data()
            
            # Connect to WebSocket
            self.ws_client.connect()
            
            # Subscribe to price feeds
            self._setup_subscriptions()
            
            # Start update monitoring thread
            self._start_update_thread()
            
            self.is_running = True
            self.logger.info("✅ Real-time EMA tracking started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start EMA tracking: {e}")
            raise
    
    def stop(self):
        """Stop real-time EMA tracking"""
        if not self.is_running:
            return
        
        self.logger.info("Stopping real-time EMA tracking...")
        
        self.is_running = False
        self.stop_event.set()
        
        # Disconnect WebSocket
        if self.ws_client:
            self.ws_client.disconnect()
        
        # Wait for update thread to finish
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5)
        
        self.logger.info("✅ Real-time EMA tracking stopped")
    
    def _initialize_historical_data(self):
        """Initialize EMAs with historical data from exchange"""
        self.logger.info("Initializing EMAs with historical data...")
        
        for coin in self.coins:
            try:
                # Get historical candle data (1-hour timeframe, last 100 candles)
                candles = self.ws_client.info.candles_snapshot({
                    "coin": coin,
                    "interval": "1h",
                    "startTime": None,
                    "endTime": None
                })
                
                if candles:
                    # Sort by timestamp and take last 100
                    sorted_candles = sorted(candles, key=lambda x: x['t'])[-100:]
                    
                    calculator = self.ema_calculators[coin]
                    for candle in sorted_candles:
                        price = float(candle['c'])  # Close price
                        timestamp = datetime.fromtimestamp(candle['t'] / 1000)
                        calculator.add_price(price, timestamp)
                    
                    self.logger.info(f"Initialized {coin} EMAs from {len(sorted_candles)} historical candles")
                    
            except Exception as e:
                self.logger.error(f"Failed to initialize historical data for {coin}: {e}")
    
    def _setup_subscriptions(self):
        """Setup WebSocket subscriptions for price data"""
        # Subscribe to all mid prices for quick updates
        self.ws_client.subscribe_all_mids(callback=self._handle_mid_prices)
        
        # Subscribe to trades for each coin for more granular data
        for coin in self.coins:
            self.ws_client.subscribe_trades(coin, callback=self._handle_trades)
    
    def _handle_mid_prices(self, channel: str, data: dict):
        """Handle mid price updates from WebSocket"""
        try:
            mids = data.get('data', {}).get('mids', {})
            timestamp = datetime.utcnow()
            
            for coin, price_str in mids.items():
                if coin in self.coins:
                    price = float(price_str)
                    self._process_price_update(coin, price, timestamp, 'mid')
                    
        except Exception as e:
            self.logger.error(f"Error handling mid prices: {e}")
    
    def _handle_trades(self, channel: str, data: dict):
        """Handle trade updates from WebSocket"""
        try:
            trades = data.get('data', [])
            
            for trade in trades:
                if isinstance(trade, dict):
                    coin = trade.get('coin')
                    if coin in self.coins:
                        price = float(trade.get('px', 0))
                        timestamp = datetime.fromtimestamp(trade.get('time', 0) / 1000)
                        self._process_price_update(coin, price, timestamp, 'trade')
                        
        except Exception as e:
            self.logger.error(f"Error handling trades: {e}")
    
    def _process_price_update(self, coin: str, price: float, timestamp: datetime, source: str):
        """Process price update and calculate EMAs"""
        if price <= 0:
            return
        
        # Update last known price and timestamp
        self.last_prices[coin] = price
        self.last_updates[coin] = timestamp
        
        # Calculate EMAs
        calculator = self.ema_calculators[coin]
        ema_data = calculator.add_price(price, timestamp)
        
        # Update stats
        self.stats['total_updates'] += 1
        
        # Create price update object
        price_update = PriceUpdate(
            coin=coin,
            price=price,
            timestamp=timestamp,
            source=source
        )
        
        # Call price callbacks
        if coin in self.price_callbacks:
            for callback in self.price_callbacks[coin]:
                try:
                    callback(coin, price_update)
                except Exception as e:
                    self.logger.error(f"Error in price callback for {coin}: {e}")
        
        # Check for trading signals
        if ema_data.signal != CrossoverSignal.NO_SIGNAL:
            self._handle_signal(coin, ema_data)
    
    def _handle_signal(self, coin: str, ema_data: EMAData):
        """Handle EMA crossover signals"""
        self.stats['signals_generated'] += 1
        
        # Get detailed signal information
        calculator = self.ema_calculators[coin]
        signal_info = calculator.get_trading_signal()
        
        self.logger.info(f"🎯 SIGNAL for {coin}: {ema_data.signal.value} - Strength: {ema_data.signal_strength:.3f}")
        
        # Call signal callbacks
        if coin in self.signal_callbacks:
            for callback in self.signal_callbacks[coin]:
                try:
                    callback(coin, ema_data, signal_info)
                except Exception as e:
                    self.logger.error(f"Error in signal callback for {coin}: {e}")
    
    def _start_update_thread(self):
        """Start background thread for monitoring and maintenance"""
        def update_loop():
            while not self.stop_event.is_set():
                try:
                    # Log periodic status
                    if self.stats['total_updates'] % 100 == 0 and self.stats['total_updates'] > 0:
                        self._log_status()
                    
                    # Check for stale data
                    self._check_stale_data()
                    
                    time.sleep(10)  # Check every 10 seconds
                    
                except Exception as e:
                    self.logger.error(f"Error in update thread: {e}")
        
        self.update_thread = threading.Thread(target=update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
    
    def _check_stale_data(self):
        """Check for coins with stale price data"""
        now = datetime.utcnow()
        stale_threshold = timedelta(minutes=5)
        
        for coin in self.coins:
            last_update = self.last_updates.get(coin)
            if last_update and (now - last_update) > stale_threshold:
                self.logger.warning(f"Stale data for {coin}: last update {last_update}")
    
    def _log_status(self):
        """Log current tracking status"""
        uptime = datetime.utcnow() - self.stats['start_time']
        
        status_msg = (
            f"📊 EMA Tracker Status: "
            f"Updates: {self.stats['total_updates']}, "
            f"Signals: {self.stats['signals_generated']}, "
            f"Uptime: {uptime}"
        )
        self.logger.info(status_msg)
    
    def get_current_data(self, coin: str) -> Optional[Dict]:
        """Get current EMA data for a coin"""
        if coin not in self.ema_calculators:
            return None
        
        calculator = self.ema_calculators[coin]
        status = calculator.get_current_status()
        signal_info = calculator.get_trading_signal()
        
        return {
            'coin': coin,
            'last_price': self.last_prices.get(coin),
            'last_update': self.last_updates.get(coin),
            'ema_status': status,
            'trading_signal': signal_info
        }
    
    def get_all_current_data(self) -> Dict[str, Dict]:
        """Get current EMA data for all tracked coins"""
        return {coin: self.get_current_data(coin) for coin in self.coins if coin in self.ema_calculators}
    
    def get_stats(self) -> Dict:
        """Get tracking statistics"""
        if self.stats['start_time']:
            uptime = datetime.utcnow() - self.stats['start_time']
            self.stats['uptime_seconds'] = uptime.total_seconds()
        
        return self.stats.copy()


def simple_signal_handler(coin: str, ema_data: EMAData, signal_info: Dict):
    """Example signal handler that prints signals"""
    signal_emoji = "🟢" if ema_data.signal == CrossoverSignal.GOLDEN_CROSS else "🔴"
    print(f"\n{signal_emoji} {coin} SIGNAL: {ema_data.signal.value.upper()}")
    print(f"   Price: ${ema_data.price:.2f}")
    print(f"   EMA20: ${ema_data.ema_20:.2f}")
    print(f"   EMA50: ${ema_data.ema_50:.2f}")
    print(f"   Strength: {ema_data.signal_strength:.1%}")
    print(f"   Action: {signal_info['action'].upper()}")
    print(f"   Confidence: {signal_info['confidence']:.1%}")


def simple_price_handler(coin: str, price_update: PriceUpdate):
    """Example price handler that prints price updates"""
    if price_update.source == 'trade':  # Only print trade updates to reduce noise
        print(f"💰 {coin}: ${price_update.price:.2f} ({price_update.source})")
