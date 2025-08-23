import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Hyperliquid API credentials
    ACCOUNT_ADDRESS = os.getenv('ACCOUNT_ADDRESS')  # Public address for the account
    SECRET_KEY = os.getenv('SECRET_KEY')  # Private key for signing transactions
    SANDBOX = os.getenv('SANDBOX', 'True').lower() == 'true'  # Use testnet if True
    
    # Trading parameters
    SYMBOL = os.getenv('SYMBOL', 'BTC/USDC')  # Hyperliquid uses USDC as base
    BASE_CURRENCY = os.getenv('BASE_CURRENCY', 'USDC')
    INITIAL_BALANCE = float(os.getenv('INITIAL_BALANCE', '1000'))
    
    # Risk management
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '0.1'))
    STOP_LOSS = float(os.getenv('STOP_LOSS', '0.02'))
    TAKE_PROFIT = float(os.getenv('TAKE_PROFIT', '0.05'))
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///trading_bot.db')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/trading_bot.log')