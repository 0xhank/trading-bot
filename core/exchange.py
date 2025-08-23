from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import logging
from typing import Dict, List, Optional
from config.settings import Config

class ExchangeClient:
    def __init__(self):
        self.config = Config()
        self.info = None
        self.exchange = None
        self.logger = logging.getLogger(__name__)
        self._initialize_exchange()
    
    def _initialize_exchange(self):
        """Initialize Hyperliquid exchange connection"""
        try:
            # Determine API URL based on environment
            api_url = constants.TESTNET_API_URL if self.config.SANDBOX else constants.MAINNET_API_URL
            
            # Initialize Info client for market data
            self.info = Info(api_url, skip_ws=True)
            
            # Initialize Exchange client for trading (requires private key)
            if self.config.SECRET_KEY:
                self.exchange = Exchange(
                    account_address=self.config.ACCOUNT_ADDRESS,
                    secret_key=self.config.SECRET_KEY,
                    api_url=api_url
                )
                self.logger.info("Connected to Hyperliquid exchange with trading capabilities")
            else:
                self.logger.info("Connected to Hyperliquid info API (read-only)")
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Hyperliquid: {e}")
            raise
    
    def get_balance(self) -> Dict:
        """Get account balance"""
        try:
            if not self.config.ACCOUNT_ADDRESS:
                self.logger.error("Account address not configured")
                return {}
            
            user_state = self.info.user_state(self.config.ACCOUNT_ADDRESS)
            return {
                'USDC': {
                    'free': float(user_state.get('withdrawable', '0')),
                    'used': float(user_state.get('marginSummary', {}).get('totalMarginUsed', '0')),
                    'total': float(user_state.get('marginSummary', {}).get('accountValue', '0'))
                }
            }
        except Exception as e:
            self.logger.error(f"Error fetching balance: {e}")
            return {}
    
    def get_ticker(self, symbol: str) -> Dict:
        """Get ticker data for symbol"""
        try:
            # Convert symbol format (e.g., BTC/USDT -> BTC)
            coin = symbol.split('/')[0] if '/' in symbol else symbol
            
            all_mids = self.info.all_mids()
            if coin in all_mids:
                price = float(all_mids[coin])
                return {
                    'symbol': symbol,
                    'last': price,
                    'bid': price,
                    'ask': price,
                    'close': price
                }
            else:
                self.logger.warning(f"Symbol {coin} not found in market data")
                return {}
        except Exception as e:
            self.logger.error(f"Error fetching ticker for {symbol}: {e}")
            return {}
    
    def place_market_order(self, symbol: str, side: str, amount: float) -> Optional[Dict]:
        """Place market order"""
        try:
            if not self.exchange:
                self.logger.error("Exchange client not initialized for trading")
                return None
            
            # Convert symbol format and get asset index
            coin = symbol.split('/')[0] if '/' in symbol else symbol
            asset = self._get_asset_index(coin)
            if asset is None:
                return None
            
            # Convert side to boolean (True for buy, False for sell)
            is_buy = side.lower() == 'buy'
            
            # Place market order
            order_result = self.exchange.market_order(coin, is_buy, amount, None)
            
            if order_result and order_result.get('status') == 'ok':
                self.logger.info(f"Market {side} order placed for {amount} {coin}")
                return {
                    'id': order_result.get('response', {}).get('data', {}).get('statuses', [{}])[0].get('filled', {}).get('oid'),
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'type': 'market'
                }
            else:
                self.logger.error(f"Market order failed: {order_result}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error placing market order: {e}")
            return None
    
    def place_limit_order(self, symbol: str, side: str, amount: float, price: float) -> Optional[Dict]:
        """Place limit order"""
        try:
            if not self.exchange:
                self.logger.error("Exchange client not initialized for trading")
                return None
            
            # Convert symbol format 
            coin = symbol.split('/')[0] if '/' in symbol else symbol
            asset = self._get_asset_index(coin)
            if asset is None:
                return None
            
            # Convert side to boolean
            is_buy = side.lower() == 'buy'
            
            # Place limit order
            order_result = self.exchange.order(coin, is_buy, amount, price, {"limit": {"tif": "Gtc"}})
            
            if order_result and order_result.get('status') == 'ok':
                oid = order_result.get('response', {}).get('data', {}).get('statuses', [{}])[0].get('resting', {}).get('oid')
                self.logger.info(f"Limit {side} order placed: {oid}")
                return {
                    'id': oid,
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'price': price,
                    'type': 'limit'
                }
            else:
                self.logger.error(f"Limit order failed: {order_result}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error placing limit order: {e}")
            return None
    
    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """Get open orders"""
        try:
            if not self.config.ACCOUNT_ADDRESS:
                self.logger.error("Account address not configured")
                return []
            
            open_orders = self.info.open_orders(self.config.ACCOUNT_ADDRESS)
            
            orders = []
            for order in open_orders:
                orders.append({
                    'id': order.get('oid'),
                    'symbol': f"{order.get('coin')}/USDC",
                    'side': 'buy' if order.get('side') == 'B' else 'sell',
                    'amount': float(order.get('sz', 0)),
                    'price': float(order.get('limitPx', 0)),
                    'timestamp': order.get('timestamp')
                })
            
            return orders
            
        except Exception as e:
            self.logger.error(f"Error fetching open orders: {e}")
            return []
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel order"""
        try:
            if not self.exchange:
                self.logger.error("Exchange client not initialized for trading")
                return False
            
            # Convert symbol format
            coin = symbol.split('/')[0] if '/' in symbol else symbol
            asset = self._get_asset_index(coin)
            if asset is None:
                return False
            
            # Cancel order
            cancel_result = self.exchange.cancel(coin, int(order_id))
            
            if cancel_result and cancel_result.get('status') == 'ok':
                self.logger.info(f"Order {order_id} cancelled")
                return True
            else:
                self.logger.error(f"Order cancellation failed: {cancel_result}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def _get_asset_index(self, coin: str) -> Optional[int]:
        """Get asset index for a coin"""
        try:
            meta = self.info.meta()
            universe = meta.get('universe', [])
            
            for i, asset_info in enumerate(universe):
                if asset_info.get('name') == coin:
                    return i
            
            self.logger.error(f"Asset {coin} not found in universe")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting asset index for {coin}: {e}")
            return None