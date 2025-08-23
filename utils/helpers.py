import logging
import json
from datetime import datetime
from typing import Any, Dict

def setup_logging(log_level: str = 'INFO', log_file: str = None):
    """Setup logging configuration"""
    level = getattr(logging, log_level.upper())
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if log_file provided)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

def calculate_position_size(balance: float, risk_percent: float, entry_price: float, stop_loss_price: float) -> float:
    """
    Calculate position size based on risk management
    
    Args:
        balance: Available balance
        risk_percent: Risk percentage (0.01 = 1%)
        entry_price: Entry price for position
        stop_loss_price: Stop loss price
        
    Returns:
        Position size
    """
    if entry_price <= 0 or stop_loss_price <= 0:
        return 0
    
    risk_amount = balance * risk_percent
    price_diff = abs(entry_price - stop_loss_price)
    
    if price_diff == 0:
        return 0
    
    position_size = risk_amount / price_diff
    return position_size

def format_currency(amount: float, decimals: int = 2) -> str:
    """Format currency amount"""
    return f"${amount:,.{decimals}f}"

def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage"""
    return f"{value:.{decimals}f}%"

def save_to_json(data: Dict[str, Any], filename: str):
    """Save data to JSON file"""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logging.error(f"Error saving to {filename}: {e}")

def load_from_json(filename: str) -> Dict[str, Any]:
    """Load data from JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"File {filename} not found")
        return {}
    except Exception as e:
        logging.error(f"Error loading from {filename}: {e}")
        return {}

def validate_symbol(symbol: str) -> bool:
    """Validate trading symbol format"""
    return '/' in symbol and len(symbol.split('/')) == 2

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values"""
    if old_value == 0:
        return 0
    return ((new_value - old_value) / old_value) * 100

def timestamp_to_string(timestamp: datetime) -> str:
    """Convert timestamp to string"""
    return timestamp.strftime('%Y-%m-%d %H:%M:%S')

def string_to_timestamp(date_string: str) -> datetime:
    """Convert string to timestamp"""
    return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')