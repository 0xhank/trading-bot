import logging
from typing import Dict, Optional
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config.settings import Config

Base = declarative_base()

class Position(Base):
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)  # 'long' or 'short'
    amount = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)  # 'buy' or 'sell'
    amount = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    pnl = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Portfolio:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        
        # Database setup
        self.engine = create_engine(self.config.DATABASE_URL)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Portfolio state
        self.balance = self.config.INITIAL_BALANCE
        self.positions = {}
        
    def add_position(self, symbol: str, side: str, amount: float, price: float):
        """Add a new position"""
        position = Position(
            symbol=symbol,
            side=side,
            amount=amount,
            entry_price=price,
            current_price=price
        )
        
        self.session.add(position)
        self.session.commit()
        
        self.positions[symbol] = {
            'side': side,
            'amount': amount,
            'entry_price': price,
            'current_price': price
        }
        
        self.logger.info(f"Added {side} position: {amount} {symbol} at {price}")
    
    def update_position_price(self, symbol: str, current_price: float):
        """Update position with current market price"""
        if symbol in self.positions:
            position = self.session.query(Position).filter_by(symbol=symbol).first()
            if position:
                position.current_price = current_price
                position.unrealized_pnl = self._calculate_pnl(
                    position.entry_price, 
                    current_price, 
                    position.amount, 
                    position.side
                )
                self.session.commit()
                
                self.positions[symbol]['current_price'] = current_price
    
    def close_position(self, symbol: str, exit_price: float) -> Optional[float]:
        """Close position and record trade"""
        if symbol not in self.positions:
            return None
        
        position_data = self.positions[symbol]
        pnl = self._calculate_pnl(
            position_data['entry_price'],
            exit_price,
            position_data['amount'],
            position_data['side']
        )
        
        # Record trade
        trade = Trade(
            symbol=symbol,
            side='sell' if position_data['side'] == 'long' else 'buy',
            amount=position_data['amount'],
            price=exit_price,
            pnl=pnl
        )
        
        self.session.add(trade)
        
        # Remove position from database
        position = self.session.query(Position).filter_by(symbol=symbol).first()
        if position:
            self.session.delete(position)
        
        self.session.commit()
        
        # Update balance and remove position
        self.balance += pnl
        del self.positions[symbol]
        
        self.logger.info(f"Closed position: {symbol}, PnL: {pnl:.2f}")
        return pnl
    
    def _calculate_pnl(self, entry_price: float, exit_price: float, amount: float, side: str) -> float:
        """Calculate profit/loss for a position"""
        if side == 'long':
            return (exit_price - entry_price) * amount
        else:  # short
            return (entry_price - exit_price) * amount
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value including unrealized PnL"""
        total_value = self.balance
        
        for symbol, position in self.positions.items():
            unrealized_pnl = self._calculate_pnl(
                position['entry_price'],
                position['current_price'],
                position['amount'],
                position['side']
            )
            total_value += unrealized_pnl
        
        return total_value
    
    def get_position_size(self, symbol: str) -> float:
        """Get current position size for symbol"""
        return self.positions.get(symbol, {}).get('amount', 0.0)
    
    def has_position(self, symbol: str) -> bool:
        """Check if we have an open position for symbol"""
        return symbol in self.positions