import time
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from lib.utils import setup
from lib.data_store import DataStore
from lib.coin import Coin
from lib.logger import get_subscription_logger
from typing import Optional, List, Dict

logger = get_subscription_logger()


class Data:
    """Manages subscriptions to market data and user data streams"""
    address: str
    info: Info
    exchange: Exchange
    store: DataStore

    coins: Dict[str, Coin]
    
    def __init__(self, api_url: str = constants.TESTNET_API_URL):
        self.address, self.info, self.exchange = setup(api_url)
        self.store = DataStore(self.address, self.info)
        self.coins = {}

        # Start the data store (this handles all subscriptions)
        self.store.start()

        logger.info(f"Initialized connection for address: {self.address}")
        logger.success("User subscriptions set up successfully!")
        
    def start(self):
        """Start the data collection"""
        self.store.start()

    def add_coin(self, coin_symbol: str, intervals: Optional[List[str]] = None):
        """Add a coin to track with specified intervals"""
        if not self.coins or not self.info:
            raise ValueError("Must call setup() first")
            
        if intervals is None:
            intervals = ["1m"]
            
        self.coins.add_coin(self.info, coin_symbol, intervals=intervals)
        logger.info(f"Added coin {coin_symbol} with intervals {intervals}")
        
    def add_multiple_coins(self, coins_config: dict):
        """Add multiple coins with their respective intervals
        
        Args:
            coins_config: dict like {"BTC": ["1m", "1h"], "ETH": ["5m"], "SOL": ["1m"]}
        """
        for coin_symbol, intervals in coins_config.items():
            self.add_coin(coin_symbol, intervals)
            
    def get_coins(self):
        """Get the coins manager"""
        return self.coins

    def _add_coin(self, coin_symbol: str) -> Coin:
        """Add a new coin to track"""
        if coin_symbol not in self.coins:
            self.coins[coin_symbol] = Coin(self.info, coin_symbol, self.address)
            logger.info(f"Added coin handler for {coin_symbol}")
        return self.coins[coin_symbol]
    
    def _get_coin(self, coin_symbol: str) -> Optional[Coin]:
        """Get coin store for a specific coin"""
        return self.coins.get(coin_symbol)
    
    def add_coin(self, coin_symbol: str, intervals: List[str] = None) -> Coin:
        """Set up all subscriptions for a specific coin"""
        if intervals is None:
            intervals = ["1m"]
            
        coin = self._add_coin(coin_symbol)

        coin.subscribe_to_ohclv()
        coin.subscribe_to_bbo()

        return coin
          
    def _handle_shutdown(self):
        """Handle graceful shutdown and data saving"""
        logger.warning("Stopping data collection...")
        self.store.print_summary()
        
        # Save all data to CSV files
        logger.info("Saving data to CSV files...")
        self.store.save_all_to_csv()
        self.coins.save_all_to_csv()
        
        # Show sample data from active subscriptions
        self._show_sample_data()
        
        # Show user fills summary if available
        self._show_user_fills_summary()
        
        # Final user summary
        self._print_final_user_summary()
        