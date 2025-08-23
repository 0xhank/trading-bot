from abc import ABC, abstractmethod
from typing import Dict, Optional
import logging

class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(__name__)
        self.parameters = {}
    
    @abstractmethod
    def generate_signal(self, data: Dict) -> Optional[str]:
        """
        Generate trading signal based on market data
        
        Args:
            data: Market data dictionary containing OHLCV data
            
        Returns:
            'buy', 'sell', or None
        """
        pass
    
    @abstractmethod
    def should_exit(self, data: Dict, position_side: str) -> bool:
        """
        Determine if current position should be closed
        
        Args:
            data: Current market data
            position_side: 'long' or 'short'
            
        Returns:
            True if position should be closed, False otherwise
        """
        pass
    
    def set_parameters(self, **kwargs):
        """Set strategy parameters"""
        self.parameters.update(kwargs)
        self.logger.info(f"Updated {self.name} parameters: {kwargs}")
    
    def get_parameters(self) -> Dict:
        """Get current strategy parameters"""
        return self.parameters.copy()
    
    def validate_signal(self, signal: Optional[str]) -> bool:
        """Validate if signal is valid"""
        return signal in ['buy', 'sell', None]