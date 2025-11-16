"""
Configuration settings for the MXC Scalp Trading Bot.
"""
import os
import warnings


class Settings:
    """Configuration settings loaded from environment variables or config files."""
    
    def __init__(self):
        # Exchange API settings
        self.api_key = os.getenv('MXC_API_KEY', '')
        self.secret_key = os.getenv('MXC_SECRET_KEY', '')
        self.api_base_url = os.getenv('MXC_API_BASE_URL', 'https://api.mexc.com')
        
        # Telegram settings
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_authorized_users = self._parse_authorized_users(
            os.getenv('TELEGRAM_AUTHORIZED_USERS', '')
        )
        
        # Trading settings
        self.trading_enabled = os.getenv('TRADING_ENABLED', 'false').lower() == 'true'
        self.default_symbol = os.getenv('DEFAULT_SYMBOL', 'BTCUSDT')
        self.quote_currency = os.getenv('QUOTE_CURRENCY', 'USDT')
        
        # Scalping strategy settings
        self.scalp_profit_target = float(os.getenv('SCALP_PROFIT_TARGET', '0.005'))  # 0.5%
        self.scalp_stop_loss = float(os.getenv('SCALP_STOP_LOSS', '0.003'))  # 0.3%
        self.max_position_size = float(os.getenv('MAX_POSITION_SIZE', '10.0'))  # Max $10 per trade
        
        # Risk management
        self.max_daily_loss = float(os.getenv('MAX_DAILY_LOSS', '100.0'))  # Max $100 daily loss
        self.max_consecutive_losses = int(os.getenv('MAX_CONSECUTIVE_LOSSES', '5'))
        self.risk_per_trade = float(os.getenv('RISK_PER_TRADE', '0.02'))  # 2% of balance per trade
        
        # Logging settings
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('LOG_FILE', 'bot.log')
        
        # WebSocket settings
        self.websocket_reconnect_delay = int(os.getenv('WEBSOCKET_RECONNECT_DELAY', '5'))
        
        # Validation
        self.missing_credentials = []
        self._validate()
    
    def _parse_authorized_users(self, users_str):
        """Parse comma-separated string of user IDs to a list of integers."""
        if not users_str:
            return []
        return [int(uid.strip()) for uid in users_str.split(',')]
    
    def _validate(self):
        """Validate configuration settings."""
        warnings_list = []
        fatal_errors = []

        if not self.api_key:
            warnings_list.append("MXC_API_KEY is missing")

        if not self.secret_key:
            warnings_list.append("MXC_SECRET_KEY is missing")

        if not self.telegram_bot_token:
            warnings_list.append("TELEGRAM_BOT_TOKEN is missing")

        if not self.telegram_authorized_users:
            warnings_list.append("TELEGRAM_AUTHORIZED_USERS is missing")

        if self.scalp_profit_target <= 0:
            fatal_errors.append("SCALP_PROFIT_TARGET must be positive")

        if self.scalp_stop_loss <= 0:
            fatal_errors.append("SCALP_STOP_LOSS must be positive")

        if self.max_position_size <= 0:
            fatal_errors.append("MAX_POSITION_SIZE must be positive")

        if self.max_daily_loss <= 0:
            fatal_errors.append("MAX_DAILY_LOSS must be positive")

        if fatal_errors:
            raise ValueError("Configuration validation errors: {}".format(', '.join(fatal_errors)))

        self.missing_credentials = warnings_list
        if warnings_list:
            warnings.warn(
                "Missing credentials detected: {}. Web interface will be limited until updated.".format(', '.join(warnings_list))
            )