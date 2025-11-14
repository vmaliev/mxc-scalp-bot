# MXC Scalp Trading Bot

A high-frequency scalping trading bot for the MXC exchange with Telegram control and monitoring.

## Overview

This bot implements a scalping strategy designed to capture small profits from frequent trades on the MXC exchange. It features real-time market monitoring, automated trading execution, risk management controls, and Telegram-based control and notifications.

## Features

- **High-Frequency Trading**: Optimized for scalping strategies with 10ms market data updates
- **Range Scalping Strategy**: Places both long and short orders at 1-hour min/max levels with 10% stop loss risk
- **Futures Trading Strategy**: Advanced futures trading with leverage and position management
- **Pair Selection**: Dynamic trading pair configuration via Telegram and web interface
- **Web Interface**: Complete web-based dashboard to control bot alongside Telegram
- **API Credential Controls**: Set API keys and bot tokens through the web interface
- **Exchange Data Monitoring**: View balance, orders, positions, and trades directly from the web interface
- **Risk Parameter Controls**: Adjust risk settings via Telegram and web interface
- **Position Size Controls**: Configure position sizing via both Telegram and web interface
- **Real-Time Monitoring**: WebSocket integration for live market data
- **Risk Management**: Daily loss limits, position sizing controls, stop-losses
- **Telegram Control**: Start/stop trading, check status, receive notifications
- **Performance Tracking**: Detailed metrics and statistics
- **Secure Operations**: Encrypted API communication, IP whitelisting support

## Prerequisites

- Python 3.9+
- MXC Exchange Account with API keys
- Telegram Bot Token

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd mxc-scalp-bot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your environment variables or edit the config.json file:
   ```bash
   export MXC_API_KEY="your_mxc_api_key"
   export MXC_SECRET_KEY="your_mxc_secret_key"
   export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
   export TELEGRAM_AUTHORIZED_USERS="123456789,987654321"
   ```

## Configuration

The bot can be configured through environment variables or the config.json file:

| Setting | Description | Default |
|--------|-------------|---------|
| `MXC_API_KEY` | MXC Exchange API Key | - |
| `MXC_SECRET_KEY` | MXC Exchange Secret Key | - |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | - |
| `TELEGRAM_AUTHORIZED_USERS` | Comma-separated list of authorized user IDs | - |
| `TRADING_ENABLED` | Enable auto-trading | false |
| `DEFAULT_SYMBOL` | Default trading pair | BTCUSDT |
| `SCALP_PROFIT_TARGET` | Target profit percentage per trade | 0.005 (0.5%) |
| `SCALP_STOP_LOSS` | Stop loss percentage per trade | 0.003 (0.3%) |
| `MAX_POSITION_SIZE` | Maximum position size in quote currency | 10.0 |
| `MAX_DAILY_LOSS` | Maximum daily loss in quote currency | 100.0 |
| `MAX_CONSECUTIVE_LOSSES` | Max losses before pausing trading | 5 |

## Usage

1. Start the bot:
   ```bash
   python -m src.main
   ```

2. Control the bot via Telegram commands:
   - `/start` - Initialize the bot
   - `/status` - Check bot status
   - `/balance` - Show account balance
   - `/start_trading` - Start scalping strategy
   - `/stop_trading` - Stop scalping strategy
   - `/start_range_trading` - Start range scalping strategy  
   - `/stop_range_trading` - Stop range scalping strategy
   - `/start_futures_trading` - Start futures strategy
   - `/stop_futures_trading` - Stop futures strategy
   - `/set_pairs` - Set trading pairs (e.g., /set_pairs BTCUSDT,ETHUSDT)
   - `/pairs` - Show current trading pairs
   - `/set_leverage` - Set futures leverage (e.g., /set_leverage 10)
   - `/leverage` - Show current futures leverage
   - `/set_risk` - Set risk parameters (e.g., /set_risk max_daily_loss 100)
   - `/set_size` - Set position size (e.g., /set_size 100)
   - `/risk_params` - Show current risk parameters
   - `/trades` - Show recent trades
   - `/profit` - Show profit/loss statistics
   - `/subscribe` - Subscribe to notifications
   - `/unsubscribe` - Unsubscribe from notifications

## Risk Management

The bot implements several risk controls:

- **Daily Loss Limit**: Trading stops if daily loss exceeds the configured limit
- **Position Sizing**: Limits on position size per trade
- **Consecutive Losses**: Trading pauses after too many consecutive losses
- **Stop Losses**: Automatic stop losses on all positions
- **Profit Taking**: Automatic profit taking at target levels

## Architecture

The bot is structured into several modules:

- `exchange/` - MXC API integration and market data
- `strategies/` - Trading strategy implementation
- `telegram_bot/` - Telegram command and notification handling
- `risk_management/` - Risk controls and management
- `monitoring/` - Logging and metrics tracking
- `config/` - Configuration management

## Safety Considerations

- Never share your API keys or Telegram bot token
- Start with small position sizes
- Test in a safe environment first
- Monitor the bot regularly
- Enable all risk management features
- Keep your system secure

## Disclaimer

This software is provided for educational purposes only. Cryptocurrency trading involves substantial risk of loss. Past performance is not indicative of future results. Use at your own risk.