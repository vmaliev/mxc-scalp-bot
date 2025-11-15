"""
MXC Scalp Trading Bot - Main Entry Point

This is the main application file that initializes all components
and starts the trading engine with Telegram control and monitoring.
"""
import asyncio
import logging

from config.settings import Settings
from exchange.api_client import MXCClient
from strategies.scalping_strategy import ScalpingStrategy
from strategies.range_scalp_strategy import RangeScalpStrategy
from strategies.futures_strategy import FuturesStrategy
from telegram_bot.bot_handler import TelegramBot
from monitoring.logger import setup_logging
from monitoring.metrics import MetricsManager
from risk_management.risk_calculator import RiskManager
from web.web_interface import WebBotController


class MXCScalpBot:
    """
    Main class that orchestrates the MXC Scalp Trading Bot.
    """
    
    def __init__(self):
        # Load configuration
        self.settings = Settings()
        
        # Setup logging
        setup_logging(self.settings.log_level, self.settings.log_file)
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.mxc_client = None
        self.scalping_strategy = None
        self.range_scalp_strategy = None
        self.futures_strategy = None
        self.current_strategy = None  # Currently active strategy
        self.trading_pairs = []  # List of trading pairs
        self.telegram_bot = None
        self.web_controller = None  # Web interface controller
        self.metrics_manager = None
        self.risk_manager = None
        
    async def initialize(self):
        """Initialize all components of the trading bot."""
        self.logger.info("Initializing MXC Scalp Trading Bot...")
        
        # Initialize exchange client
        self.mxc_client = MXCClient(
            api_key=self.settings.api_key,
            secret_key=self.settings.secret_key,
            base_url=self.settings.api_base_url
        )
        
        # Initialize metrics manager
        self.metrics_manager = MetricsManager()
        
        # Initialize risk manager
        self.risk_manager = RiskManager(
            exchange_client=self.mxc_client,
            settings=self.settings
        )
        
        # Initialize scalping strategy
        self.scalping_strategy = ScalpingStrategy(
            exchange_client=self.mxc_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        # Initialize range scalping strategy
        self.range_scalp_strategy = RangeScalpStrategy(
            exchange_client=self.mxc_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        # Initialize futures strategy
        self.futures_strategy = FuturesStrategy(
            exchange_client=self.mxc_client,
            metrics_manager=self.metrics_manager,
            settings=self.settings
        )
        
        # Set the default strategy (can be changed via Telegram commands later)
        self.current_strategy = self.scalping_strategy
        
        # Initialize Telegram bot with all strategies
        self.telegram_bot = TelegramBot(
            bot_token=self.settings.telegram_bot_token,
            authorized_users=self.settings.telegram_authorized_users,
            exchange_client=self.mxc_client,
            scalping_strategy=self.scalping_strategy,
            range_scalp_strategy=self.range_scalp_strategy,
            futures_strategy=self.futures_strategy,
            metrics_manager=self.metrics_manager,
            risk_manager=self.risk_manager
        )
        
        # Initialize web controller with access to all strategies
        self.web_controller = WebBotController(
            scalping_strategy=self.scalping_strategy,
            range_scalp_strategy=self.range_scalp_strategy,
            futures_strategy=self.futures_strategy,
            metrics_manager=self.metrics_manager,
            risk_manager=self.risk_manager,
            settings=self.settings,
            mxc_client=self.mxc_client
        )
        
        # Initialize trading pairs with default
        self.trading_pairs = [self.settings.default_symbol]
        
        self.logger.info("All components initialized successfully")
    
    async def start(self):
        """Start the trading bot."""
        try:
            # Initialize all components
            await self.initialize()
            
            # Start the exchange client (connect to WebSocket)
            await self.mxc_client.start_websocket()
            
            # Start the currently selected strategy
            if self.current_strategy:
                self.current_strategy.start()
            
            # Start the Telegram bot
            await self.telegram_bot.start_polling()
            
            # Start the web interface in a separate thread
            if self.web_controller:
                import threading
                # Update the web controller with references to the exchange and strategies
                self.web_controller.mxc_client = self.mxc_client
                self.web_controller.scalping_strategy = self.scalping_strategy
                self.web_controller.range_scalp_strategy = self.range_scalp_strategy
                self.web_controller.futures_strategy = self.futures_strategy
                self.web_controller.metrics_manager = self.metrics_manager
                self.web_controller.risk_manager = self.risk_manager
                self.web_controller.settings = self.settings
                
                web_thread = threading.Thread(
                    target=self.web_controller.start_server,
                    kwargs={'host':'0.0.0.0', 'port': 5001, 'debug': False},
                    daemon=True  # Daemon thread will stop when main program exits
                )
                web_thread.start()
                self.logger.info("Web interface started on http://0.0.0.0:5001")
            
            # Keep the main thread running
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Shutdown signal received")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Clean shutdown of all components."""
        self.logger.info("Shutting down MXC Scalp Trading Bot...")
        
        if self.scalping_strategy:
            self.scalping_strategy.stop()
        
        if self.range_scalp_strategy:
            self.range_scalp_strategy.stop()
        
        if self.futures_strategy:
            self.futures_strategy.stop()
        
        if self.mxc_client:
            await self.mxc_client.stop_websocket()
        
        if self.telegram_bot:
            await self.telegram_bot.stop()
        
        # Web controller shutdown happens automatically when script terminates
        if self.web_controller:
            self.logger.info("Web interface ready to shutdown")
        
        self.logger.info("All components shut down successfully")


def main():
    """Main entry point."""
    bot = MXCScalpBot()
    
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Error running bot: {e}")


if __name__ == "__main__":
    main()