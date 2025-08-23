#!/usr/bin/env python3

import logging
from config.settings import Config
from core.exchange import ExchangeClient
from core.portfolio import Portfolio
from data.market_data import MarketDataProvider
from utils.helpers import setup_logging
from strategies.base_strategy import BaseStrategy

class TradingBot:
    def __init__(self):
        self.config = Config()
        setup_logging(self.config.LOG_LEVEL, self.config.LOG_FILE)
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.exchange = ExchangeClient()
        self.portfolio = Portfolio()
        self.market_data = MarketDataProvider(self.exchange)
        self.strategy = None
        
        self.logger.info("Trading bot initialized")
    
    def set_strategy(self, strategy: BaseStrategy):
        """Set trading strategy"""
        self.strategy = strategy
        self.logger.info(f"Strategy set to: {strategy.name}")
    
    def run(self):
        """Main trading loop"""
        if not self.strategy:
            self.logger.error("No strategy set. Use set_strategy() first.")
            return
        
        self.logger.info("Starting trading bot...")
        
        try:
            # Get market data
            data = self.market_data.get_market_data_with_indicators(
                self.config.SYMBOL,
                timeframe='1m',
                limit=100
            )
            
            if data.empty:
                self.logger.warning("No market data available")
                return
            
            # Get latest data point
            latest_data = data.iloc[-1].to_dict()
            current_price = self.market_data.get_current_price(self.config.SYMBOL)
            
            if current_price:
                latest_data['current_price'] = current_price
            
            # Check for existing position
            has_position = self.portfolio.has_position(self.config.SYMBOL)
            
            if has_position:
                # Check exit conditions
                position_data = self.portfolio.positions[self.config.SYMBOL]
                should_exit = self.strategy.should_exit(latest_data, position_data['side'])
                
                if should_exit and current_price:
                    # Close position
                    pnl = self.portfolio.close_position(self.config.SYMBOL, current_price)
                    self.logger.info(f"Position closed. PnL: {pnl:.2f}")
                    
                    # Place market order to close
                    side = 'sell' if position_data['side'] == 'long' else 'buy'
                    self.exchange.place_market_order(
                        self.config.SYMBOL,
                        side,
                        position_data['amount']
                    )
                else:
                    # Update position price
                    if current_price:
                        self.portfolio.update_position_price(self.config.SYMBOL, current_price)
            else:
                # Check for entry signal
                signal = self.strategy.generate_signal(latest_data)
                
                if signal in ['buy', 'sell'] and current_price:
                    # Calculate position size (simplified)
                    balance = self.portfolio.balance
                    position_value = balance * self.config.MAX_POSITION_SIZE
                    amount = position_value / current_price
                    
                    # Place order
                    order = self.exchange.place_market_order(
                        self.config.SYMBOL,
                        signal,
                        amount
                    )
                    
                    if order:
                        # Add position to portfolio
                        side = 'long' if signal == 'buy' else 'short'
                        self.portfolio.add_position(
                            self.config.SYMBOL,
                            side,
                            amount,
                            current_price
                        )
            
            # Log portfolio status
            portfolio_value = self.portfolio.get_portfolio_value()
            self.logger.info(f"Portfolio value: ${portfolio_value:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error in trading loop: {e}")
    
    def get_status(self) -> dict:
        """Get bot status"""
        return {
            'portfolio_value': self.portfolio.get_portfolio_value(),
            'balance': self.portfolio.balance,
            'positions': self.portfolio.positions,
            'strategy': self.strategy.name if self.strategy else None
        }

def main():
    """Main entry point"""
    bot = TradingBot()
    
    # Example: Set a basic strategy (you'll need to implement this)
    # from strategies.simple_ma_strategy import SimpleMAStrategy
    # strategy = SimpleMAStrategy()
    # bot.set_strategy(strategy)
    
    # Run once (in production, you'd run this in a loop or schedule it)
    # bot.run()
    
    print("Trading bot setup complete!")
    print("To get started:")
    print("1. Update .env file with your exchange credentials")
    print("2. Implement a trading strategy")
    print("3. Call bot.set_strategy() and bot.run()")

if __name__ == "__main__":
    main()