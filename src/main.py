import json
from hyperliquid.info import Info
from hyperliquid.utils import constants
from lib.data import Data
from lib.utils import setup
from lib.logger import get_trading_logger

logger = get_trading_logger()

def main():

    data_manager = Data(constants.TESTNET_API_URL)
    data_manager.add_coin("BTC")

if __name__ == "__main__":
    main()
