"""
Telegram Bot Handler

Manages the Telegram bot interface for control and monitoring
"""
import asyncio
import logging
from typing import Dict, Any, List

from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.helpers import escape_markdown

from exchange.api_client import MXCClient
from strategies.scalping_strategy import ScalpingStrategy
from monitoring.metrics import MetricsManager
from config.settings import Settings


class TelegramBot:
    """
    Handles Telegram bot commands and notifications.
    """
    
    def __init__(self, bot_token: str, authorized_users: List[int], 
                 exchange_client: MXCClient, scalping_strategy: ScalpingStrategy,
                 metrics_manager: MetricsManager, risk_manager: 'RiskManager' = None,
                 range_scalp_strategy: 'RangeScalpStrategy' = None,
                 futures_strategy: 'FuturesStrategy' = None):
        self.bot_token = bot_token
        self.authorized_users = authorized_users
        self.exchange_client = exchange_client
        self.scalping_strategy = scalping_strategy
        self.range_scalp_strategy = range_scalp_strategy
        self.futures_strategy = futures_strategy
        self.metrics_manager = metrics_manager
        self.risk_manager = risk_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize the bot application
        self.application = Application.builder().token(bot_token).build()
        self.bot: Bot = self.application.bot
        
        # Store user chat IDs for notifications
        self.notification_users = set()
        
        # Register command handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register command handlers for the bot."""
        # Command handlers
        self.application.add_handler(CommandHandler('start', self._start))
        self.application.add_handler(CommandHandler('help', self._help))
        self.application.add_handler(CommandHandler('status', self._status))
        self.application.add_handler(CommandHandler('balance', self._balance))
        self.application.add_handler(CommandHandler('start_trading', self._start_trading))
        self.application.add_handler(CommandHandler('stop_trading', self._stop_trading))
        self.application.add_handler(CommandHandler('start_range_trading', self._start_range_trading))
        self.application.add_handler(CommandHandler('stop_range_trading', self._stop_range_trading))
        self.application.add_handler(CommandHandler('start_futures_trading', self._start_futures_trading))
        self.application.add_handler(CommandHandler('stop_futures_trading', self._stop_futures_trading))
        self.application.add_handler(CommandHandler('set_pairs', self._set_trading_pairs))
        self.application.add_handler(CommandHandler('pairs', self._get_trading_pairs))
        self.application.add_handler(CommandHandler('leverage', self._get_leverage))
        self.application.add_handler(CommandHandler('set_leverage', self._set_leverage))
        self.application.add_handler(CommandHandler('set_risk', self._set_risk_parameters))
        self.application.add_handler(CommandHandler('set_size', self._set_position_size))
        self.application.add_handler(CommandHandler('risk_params', self._get_risk_parameters))
        self.application.add_handler(CommandHandler('trades', self._trades))
        self.application.add_handler(CommandHandler('profit', self._profit))
        self.application.add_handler(CommandHandler('risk', self._risk_status))
        self.application.add_handler(CommandHandler('subscribe', self._subscribe_notifications))
        self.application.add_handler(CommandHandler('unsubscribe', self._unsubscribe_notifications))
        
        # Message handler for non-command messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
    
    def _is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized to use the bot."""
        return user_id in self.authorized_users
    
    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user_id = update.effective_user.id
        
        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        welcome_message = (
            "🤖 *MXC Scalp Trading Bot* \n\n"
            "Welcome! I'm your trading assistant powered by the MXC exchange.\n\n"
            "Available commands:\n"
            "/help - Show all commands\n"
            "/status - Show bot status\n"
            "/balance - Show account balance\n"
            "/start_trading - Start scalping strategy\n"
            "/stop_trading - Stop scalping strategy\n"
            "/start_range_trading - Start range scalping strategy\n"
            "/stop_range_trading - Stop range scalping strategy\n"
            "/start_futures_trading - Start futures strategy\n"
            "/stop_futures_trading - Stop futures strategy\n"
            "/set_pairs - Set trading pairs\n"
            "/pairs - Show current trading pairs\n"
            "/set_leverage - Set futures leverage\n"
            "/leverage - Show current futures leverage\n"
            "/set_risk - Set risk parameters\n"
            "/set_size - Set position size\n"
            "/risk_params - Show current risk parameters\n"
            "/trades - Show recent trades\n"
            "/profit - Show profit/loss\n"
            "/risk - Show risk management status\n"
            "/subscribe - Subscribe to notifications\n"
            "/unsubscribe - Unsubscribe from notifications"
        )
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def _help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        user_id = update.effective_user.id
        
        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        help_message = (
            "🤖 *MXC Scalp Trading Bot - Help*\n\n"
            "*Commands:*\n"
            "/start - Start the bot and show welcome message\n"
            "/help - Show this help message\n"
            "/status - Show current bot status\n"
            "/balance - Show account balances\n"
            "/start_trading - Start the scalping strategy\n"
            "/stop_trading - Stop the scalping strategy\n"
            "/start_range_trading - Start the range scalping strategy\n"
            "/stop_range_trading - Stop the range scalping strategy\n"
            "/start_futures_trading - Start the futures strategy\n"
            "/stop_futures_trading - Stop the futures strategy\n"
            "/set_pairs - Set trading pairs (e.g., /set_pairs BTCUSDT,ETHUSDT)\n"
            "/pairs - Show current trading pairs\n"
            "/set_leverage - Set futures leverage (e.g., /set_leverage 10)\n"
            "/leverage - Show current futures leverage\n"
            "/set_risk - Set risk parameters (e.g., /set_risk max_daily_loss 100)\n"
            "/set_size - Set position size (e.g., /set_size 100)\n"
            "/risk_params - Show current risk parameters\n"
            "/trades - Show recent trade history\n"
            "/profit - Show profit/loss statistics\n"
            "/risk - Show risk management status\n"
            "/subscribe - Subscribe to trading notifications\n"
            "/unsubscribe - Unsubscribe from notifications\n\n"
            "*Note: Only authorized users can execute trading commands.*"
        )
        
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def _status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        user_id = update.effective_user.id
        
        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        try:
            # Get strategy status
            strategy_status = self.scalping_strategy.get_status()
            
            # Get account info
            account_info = await self.exchange_client.get_account_info()
            total_balance = sum(
                float(balance['free']) + float(balance['locked']) 
                for balance in account_info['balances'] 
                if float(balance['free']) + float(balance['locked']) > 0
            )
            
            status_message = (
                "📊 *Bot Status*\n\n"
                f"Trading: {'✅ ON' if strategy_status['is_running'] and self.scalping_strategy.settings.trading_enabled else '❌ OFF'}\n"
                f"Active Positions: {strategy_status['active_positions_count']}\n"
                f"Trading Pairs: {', '.join(strategy_status['trading_pairs'])}\n"
                f"Account Balance: ${total_balance:.2f}\n"
                f"Notifications: {'✅ ON' if user_id in self.notification_users else '❌ OFF'}"
            )
            
            await update.message.reply_text(status_message, parse_mode='Markdown')
            
        except Exception as e:
            error_message = f"❌ Error getting status: {str(e)}"
            await update.message.reply_text(error_message)
    
    async def _balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command."""
        user_id = update.effective_user.id
        
        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        try:
            account_info = await self.exchange_client.get_account_info()
            
            # Format balances
            balances = []
            for balance in account_info['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:  # Only show non-zero balances
                    balances.append(f"{balance['asset']}: {free:.4f} free, {locked:.4f} locked")
            
            if balances:
                balance_message = "💰 *Account Balances*\n\n" + "\n".join(balances)
            else:
                balance_message = "💰 *Account Balances*\n\nNo funds in account."
            
            await update.message.reply_text(balance_message, parse_mode='Markdown')
            
        except Exception as e:
            error_message = f"❌ Error getting balance: {str(e)}"
            await update.message.reply_text(error_message)
    
    async def _start_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_trading command."""
        user_id = update.effective_user.id
        
        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        try:
            # Update settings to enable trading
            self.scalping_strategy.settings.trading_enabled = True
            self.scalping_strategy.start()
            
            success_message = "✅ Scalping strategy started successfully!"
            await update.message.reply_text(success_message)
            
            # Send notification to all subscribers
            await self._send_notification_to_all("🚨 Bot Alert: Scalping strategy started!")
            
        except Exception as e:
            error_message = f"❌ Error starting trading: {str(e)}"
            await update.message.reply_text(error_message)
    
    async def _stop_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop_trading command."""
        user_id = update.effective_user.id
        
        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        try:
            self.scalping_strategy.stop()
            # Also disable trading in settings
            self.scalping_strategy.settings.trading_enabled = False
            
            success_message = "✅ Scalping strategy stopped successfully!"
            await update.message.reply_text(success_message)
            
            # Send notification to all subscribers
            await self._send_notification_to_all("✅ Bot Alert: Scalping strategy stopped!")
            
        except Exception as e:
            error_message = f"❌ Error stopping trading: {str(e)}"
            await update.message.reply_text(error_message)

    async def _start_range_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_range_trading command."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        if not self.range_scalp_strategy:
            await update.message.reply_text("❌ Range scalping strategy is not initialized.")
            return

        try:
            # Start the range scalping strategy
            self.range_scalp_strategy.start()
            # Update settings to enable trading for this strategy
            self.range_scalp_strategy.settings.trading_enabled = True

            success_message = "✅ Range scalping strategy started successfully!"
            await update.message.reply_text(success_message)

            # Send notification to all subscribers
            await self._send_notification_to_all("🚨 Bot Alert: Range scalping strategy started!")

        except Exception as e:
            error_message = f"❌ Error starting range trading: {str(e)}"
            await update.message.reply_text(error_message)

    async def _stop_range_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop_range_trading command."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        if not self.range_scalp_strategy:
            await update.message.reply_text("❌ Range scalping strategy is not initialized.")
            return

        try:
            self.range_scalp_strategy.stop()
            # Also disable trading in settings
            self.range_scalp_strategy.settings.trading_enabled = False

            success_message = "✅ Range scalping strategy stopped successfully!"
            await update.message.reply_text(success_message)

            # Send notification to all subscribers
            await self._send_notification_to_all("✅ Bot Alert: Range scalping strategy stopped!")

        except Exception as e:
            error_message = f"❌ Error stopping range trading: {str(e)}"
            await update.message.reply_text(error_message)

    async def _start_futures_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_futures_trading command."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        if not self.futures_strategy:
            await update.message.reply_text("❌ Futures strategy is not initialized.")
            return

        try:
            self.futures_strategy.start()
            # Update settings to enable trading for this strategy
            self.futures_strategy.settings.trading_enabled = True

            success_message = "✅ Futures strategy started successfully!"
            await update.message.reply_text(success_message)

            # Send notification to all subscribers
            await self._send_notification_to_all("🚨 Bot Alert: Futures strategy started!")

        except Exception as e:
            error_message = f"❌ Error starting futures trading: {str(e)}"
            await update.message.reply_text(error_message)

    async def _stop_futures_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop_futures_trading command."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        if not self.futures_strategy:
            await update.message.reply_text("❌ Futures strategy is not initialized.")
            return

        try:
            self.futures_strategy.stop()
            # Also disable trading in settings
            self.futures_strategy.settings.trading_enabled = False

            success_message = "✅ Futures strategy stopped successfully!"
            await update.message.reply_text(success_message)

            # Send notification to all subscribers
            await self._send_notification_to_all("✅ Bot Alert: Futures strategy stopped!")

        except Exception as e:
            error_message = f"❌ Error stopping futures trading: {str(e)}"
            await update.message.reply_text(error_message)

    async def _set_trading_pairs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /set_pairs command to set trading pairs."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        try:
            # Get the pairs from the command message
            message_text = update.message.text.strip()
            parts = message_text.split(' ', 1)
            
            if len(parts) < 2:
                await update.message.reply_text(
                    "❌ Please specify trading pairs. Usage: /set_pairs BTCUSDT,ETHUSDT"
                )
                return

            pairs_str = parts[1]
            pairs = [pair.strip().upper() for pair in pairs_str.split(',')]
            
            # Validate pairs format (basic validation)
            valid_pairs = []
            for pair in pairs:
                if len(pair) >= 6 and pair.endswith('USDT'):  # Basic validation
                    valid_pairs.append(pair)
                else:
                    await update.message.reply_text(f"⚠️ Invalid pair format: {pair}. Use format like BTCUSDT")
            
            if not valid_pairs:
                await update.message.reply_text("❌ No valid pairs provided. Use format like: BTCUSDT,ETHUSDT")
                return

            # Update all strategies with new pairs
            if self.scalping_strategy:
                self.scalping_strategy.trading_pairs = valid_pairs
            if self.range_scalp_strategy:
                self.range_scalp_strategy.trading_pairs = valid_pairs
            if self.futures_strategy:
                self.futures_strategy.set_trading_pairs(valid_pairs)

            success_message = f"✅ Trading pairs updated successfully: {', '.join(valid_pairs)}"
            await update.message.reply_text(success_message)

        except Exception as e:
            error_message = f"❌ Error setting trading pairs: {str(e)}"
            await update.message.reply_text(error_message)

    async def _get_trading_pairs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pairs command to get current trading pairs."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        try:
            # Get pairs from the scalping strategy as default
            pairs = getattr(self.scalping_strategy, 'trading_pairs', [self.scalping_strategy.settings.default_symbol]) if self.scalping_strategy else []
            
            pairs_message = f"📊 Current trading pairs: {', '.join(pairs) if pairs else 'No pairs set'}"
            await update.message.reply_text(pairs_message)

        except Exception as e:
            error_message = f"❌ Error getting trading pairs: {str(e)}"
            await update.message.reply_text(error_message)

    async def _get_leverage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /leverage command to get current leverage."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        try:
            if not self.futures_strategy:
                await update.message.reply_text("❌ Futures strategy is not initialized.")
                return

            leverage = getattr(self.futures_strategy, 'leverage', 'N/A')
            leverage_message = f"💰 Current futures leverage: {leverage}x"
            await update.message.reply_text(leverage_message)

        except Exception as e:
            error_message = f"❌ Error getting leverage: {str(e)}"
            await update.message.reply_text(error_message)

    async def _set_leverage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /set_leverage command to set leverage for futures."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        try:
            if not self.futures_strategy:
                await update.message.reply_text("❌ Futures strategy is not initialized.")
                return

            # Get the leverage from the command message
            message_text = update.message.text.strip()
            parts = message_text.split(' ', 1)
            
            if len(parts) < 2:
                await update.message.reply_text(
                    "❌ Please specify leverage. Usage: /set_leverage 10"
                )
                return

            try:
                leverage = int(parts[1])
            except ValueError:
                await update.message.reply_text("❌ Leverage must be a number between 1 and 125")
                return
            
            if not (1 <= leverage <= 125):
                await update.message.reply_text("❌ Leverage must be between 1 and 125")
                return

            self.futures_strategy.set_leverage(leverage)
            success_message = f"✅ Futures leverage set to {leverage}x successfully!"
            await update.message.reply_text(success_message)

        except Exception as e:
            error_message = f"❌ Error setting leverage: {str(e)}"
            await update.message.reply_text(error_message)

    async def _set_risk_parameters(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /set_risk command to adjust risk parameters."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        try:
            # Get parameters from the command message
            message_text = update.message.text.strip()
            parts = message_text.split(' ', 1)
            
            if len(parts) < 2:
                await update.message.reply_text(
                    "❌ Please specify risk parameter and value. Usage examples:\n" +
                    "/set_risk max_daily_loss 100\n" +
                    "/set_risk risk_per_trade 0.02\n" +
                    "/set_risk max_consecutive_losses 5\n" +
                    "/set_risk profit_target 0.005\n" +
                    "/set_risk stop_loss 0.003"
                )
                return

            params_str = parts[1]
            param_parts = params_str.split(' ')
            
            if len(param_parts) != 2:
                await update.message.reply_text(
                    "❌ Invalid format. Use: /set_risk parameter_name value"
                )
                return
            
            param_name = param_parts[0].lower()
            param_value = param_parts[1]
            
            # Get the settings from scalping strategy
            if not self.scalping_strategy:
                await update.message.reply_text("❌ Strategy not initialized.")
                return
                
            settings = self.scalping_strategy.settings
            
            # Validate and update the parameter
            success = False
            try:
                if param_name == 'max_daily_loss':
                    value = float(param_value)
                    if value > 0:
                        settings.max_daily_loss = value
                        success = True
                        response = f"✅ Max daily loss set to ${value}"
                    else:
                        await update.message.reply_text("❌ Max daily loss must be positive")
                        return
                        
                elif param_name == 'risk_per_trade':
                    value = float(param_value)
                    if 0 < value <= 0.5:  # Max 50% risk per trade
                        settings.risk_per_trade = value
                        success = True
                        response = f"✅ Risk per trade set to {value:.2%}"
                    else:
                        await update.message.reply_text("❌ Risk per trade must be between 0 and 0.5 (0% to 50%)")
                        return
                        
                elif param_name == 'max_consecutive_losses':
                    value = int(param_value)
                    if value > 0:
                        settings.max_consecutive_losses = value
                        success = True
                        response = f"✅ Max consecutive losses set to {value}"
                    else:
                        await update.message.reply_text("❌ Max consecutive losses must be positive")
                        return
                        
                elif param_name == 'profit_target' or param_name == 'profit_target':
                    value = float(param_value)
                    if 0 < value <= 0.1:  # Max 10% profit target
                        settings.scalp_profit_target = value
                        success = True
                        response = f"✅ Profit target set to {value:.2%}"
                    else:
                        await update.message.reply_text("❌ Profit target must be between 0 and 0.1 (0% to 10%)")
                        return
                        
                elif param_name == 'stop_loss':
                    value = float(param_value)
                    if 0 < value <= 0.1:  # Max 10% stop loss
                        settings.scalp_stop_loss = value
                        success = True
                        response = f"✅ Stop loss set to {value:.2%}"
                    else:
                        await update.message.reply_text("❌ Stop loss must be between 0 and 0.1 (0% to 10%)")
                        return
                        
                else:
                    await update.message.reply_text(
                        "❌ Unknown parameter. Valid parameters:\n" +
                        "- max_daily_loss\n" +
                        "- risk_per_trade\n" +
                        "- max_consecutive_losses\n" +
                        "- profit_target\n" +
                        "- stop_loss"
                    )
                    return
            except ValueError:
                await update.message.reply_text("❌ Invalid value format. Please provide a number.")
                return
            
            if success:
                await update.message.reply_text(response)

        except Exception as e:
            error_message = f"❌ Error setting risk parameters: {str(e)}"
            await update.message.reply_text(error_message)

    async def _set_position_size(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /set_size command to adjust position size."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        try:
            # Get the size from the command message
            message_text = update.message.text.strip()
            parts = message_text.split(' ', 1)
            
            if len(parts) < 2:
                await update.message.reply_text(
                    "❌ Please specify position size. Usage: /set_size 100"
                )
                return

            try:
                size = float(parts[1])
            except ValueError:
                await update.message.reply_text("❌ Position size must be a number")
                return
            
            if size <= 0:
                await update.message.reply_text("❌ Position size must be positive")
                return

            # Get the settings from scalping strategy
            if not self.scalping_strategy:
                await update.message.reply_text("❌ Strategy not initialized.")
                return
                
            settings = self.scalping_strategy.settings
            settings.max_position_size = size
            response = f"✅ Max position size set to {settings.quote_currency} {size}"
            await update.message.reply_text(response)

        except Exception as e:
            error_message = f"❌ Error setting position size: {str(e)}"
            await update.message.reply_text(error_message)

    async def _get_risk_parameters(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /risk_params command to get current risk parameters."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        try:
            if not self.scalping_strategy:
                await update.message.reply_text("❌ Strategy not initialized.")
                return
                
            settings = self.scalping_strategy.settings
            
            risk_params_message = (
                f"📊 *Current Risk Parameters*\n\n"
                f"Max Daily Loss: ${settings.max_daily_loss}\n"
                f"Risk Per Trade: {settings.risk_per_trade:.2%}\n"
                f"Max Consecutive Losses: {settings.max_consecutive_losses}\n"
                f"Profit Target: {settings.scalp_profit_target:.2%}\n"
                f"Stop Loss: {settings.scalp_stop_loss:.2%}\n"
                f"Max Position Size: {settings.max_position_size} {settings.quote_currency}"
            )
            
            await update.message.reply_text(risk_params_message, parse_mode='Markdown')

        except Exception as e:
            error_message = f"❌ Error getting risk parameters: {str(e)}"
            await update.message.reply_text(error_message)

    async def _trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trades command."""
        user_id = update.effective_user.id
        
        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        try:
            # Get recent trades from metrics
            recent_trades = self.metrics_manager.get_recent_trades()
            
            if not recent_trades:
                trades_message = "📋 No recent trades recorded."
            else:
                # Format recent trades
                trade_list = []
                for trade in recent_trades[-5:]:  # Show last 5 trades
                    trade_list.append(
                        f"• {trade['symbol']}: {trade['profit']:+.4f} {self.scalping_strategy.settings.quote_currency} "
                        f"({trade['timestamp']})"
                    )
                
                trades_message = "📋 *Recent Trades*\n\n" + "\n".join(trade_list)
            
            await update.message.reply_text(trades_message, parse_mode='Markdown')
            
        except Exception as e:
            error_message = f"❌ Error getting trades: {str(e)}"
            await update.message.reply_text(error_message)
    
    async def _profit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /profit command."""
        user_id = update.effective_user.id
        
        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        try:
            # Get profit/loss statistics
            stats = self.metrics_manager.get_statistics()
            
            profit_message = (
                "📈 *Profit/Loss Statistics*\n\n"
                f"Total Profit: {stats['total_profit']:+.4f} {self.scalping_strategy.settings.quote_currency}\n"
                f"Total Trades: {stats['total_trades']}\n"
                f"Win Rate: {stats['win_rate']:.2%}\n"
                f"Best Trade: {stats['best_trade']:+.4f} {self.scalping_strategy.settings.quote_currency}\n"
                f"Worst Trade: {stats['worst_trade']:+.4f} {self.scalping_strategy.settings.quote_currency}"
            )
            
            await update.message.reply_text(profit_message, parse_mode='Markdown')
            
        except Exception as e:
            error_message = f"❌ Error getting profit stats: {str(e)}"
            await update.message.reply_text(error_message)

    async def _risk_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /risk command."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        if not self.risk_manager:
            await update.message.reply_text("❌ Risk manager is not initialized.")
            return

        try:
            # Get risk management status
            risk_status = self.risk_manager.get_risk_status()

            risk_message = (
                "🛡️ *Risk Management Status*\n\n"
                f"Daily P&L: {risk_status['daily_pnl']:+.4f} {self.scalping_strategy.settings.quote_currency}\n"
                f"Daily Trades: {risk_status['daily_trades_count']}\n"
                f"Consecutive Losses: {risk_status['consecutive_losses']}\n"
                f"Max Daily Loss: {risk_status['max_daily_loss']} {self.scalping_strategy.settings.quote_currency}\n"
                f"Max Consecutive Losses: {risk_status['max_consecutive_losses']}\n"
                f"Position Size Limit: {risk_status['position_size_limit']} {self.scalping_strategy.settings.quote_currency}\n"
                f"Risk Per Trade: {risk_status['risk_per_trade']:.2%}"
            )

            await update.message.reply_text(risk_message, parse_mode='Markdown')

        except Exception as e:
            error_message = f"❌ Error getting risk status: {str(e)}"
            await update.message.reply_text(error_message)
    
    async def _subscribe_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /subscribe command."""
        user_id = update.effective_user.id
        
        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        self.notification_users.add(user_id)
        
        success_message = "✅ You have subscribed to trading notifications!"
        await update.message.reply_text(success_message)
    
    async def _unsubscribe_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unsubscribe command."""
        user_id = update.effective_user.id
        
        self.notification_users.discard(user_id)
        
        success_message = "✅ You have unsubscribed from trading notifications."
        await update.message.reply_text(success_message)
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle non-command messages."""
        user_id = update.effective_user.id
        
        if not self._is_authorized(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        # For non-authorized users, just acknowledge the message
        await update.message.reply_text("I received your message. Use /help to see available commands.")
    
    async def start_polling(self):
        """Start the Telegram bot polling."""
        self.logger.info("Starting Telegram bot polling...")
        await self.application.start()
        await self.application.updater.start_polling()
    
    async def stop(self):
        """Stop the Telegram bot."""
        self.logger.info("Stopping Telegram bot...")
        await self.application.stop()
        await self.application.shutdown()
    
    async def _send_notification_to_all(self, message: str):
        """Send notification to all subscribed users."""
        for user_id in self.notification_users:
            try:
                await self.bot.send_message(chat_id=user_id, text=message)
            except Exception as e:
                self.logger.error(f"Error sending notification to {user_id}: {e}")
    
    async def send_trade_notification(self, trade_info: Dict[str, Any]):
        """Send a trade notification to subscribed users."""
        message = (
            f"💰 *New Trade Executed*\n\n"
            f"Symbol: {trade_info['symbol']}\n"
            f"Side: {trade_info['side']}\n"
            f"Size: {trade_info['size']}\n"
            f"Profit: {trade_info['profit']:+.4f} {self.scalping_strategy.settings.quote_currency}\n"
            f"Time: {trade_info['timestamp']}"
        )
        
        await self._send_notification_to_all(message)