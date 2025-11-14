# MXC Scalp Bot Project

## Project Overview
This project is a sophisticated cryptocurrency trading bot designed for scalping strategies on the MXC exchange. Scalping is a trading strategy that aims to make small profits from frequent trades, buying and selling assets within a short time frame to capitalize on small price movements. The bot includes Telegram control and monitoring capabilities.

## Project Structure
The project is fully implemented with the following structure:

```
mxc-scalp-bot/
├── README.md                    # Project overview and usage instructions
├── requirements.txt             # Python dependencies
├── config.json                  # Configuration file
├── QWEN.md                     # This file - context for AI interactions
├── src/                        # Source code for the trading bot
│   ├── __init__.py
│   ├── main.py                 # Main bot entry point
│   ├── config/                 # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py         # Settings loader
│   ├── exchange/               # MXC exchange integration
│   │   ├── __init__.py
│   │   ├── api_client.py       # API wrapper and communication
│   │   ├── market_data.py      # Market data handler with WebSocket
│   │   └── order_manager.py    # Order execution and management
│   ├── strategies/             # Trading strategies
│   │   ├── __init__.py
│   │   ├── base_strategy.py    # Strategy base class
│   │   ├── scalping_strategy.py # Main scalping implementation
│   │   └── indicators.py        # Technical analysis indicators
│   ├── telegram_bot/           # Telegram integration
│   │   ├── __init__.py
│   │   └── bot_handler.py      # Bot command handler
│   ├── risk_management/        # Risk controls
│   │   ├── __init__.py
│   │   └── risk_calculator.py  # Risk management logic
│   ├── monitoring/             # Monitoring & logging
│   │   ├── __init__.py
│   │   ├── logger.py           # Logging setup
│   │   └── metrics.py          # Performance metrics tracking
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       ├── helpers.py          # Helper functions
│       └── validators.py       # Validation utilities
```

## Technology Stack
- **Language**: Python 3.9+
- **Exchange API**: MXC REST and WebSocket APIs for real-time trading
- **Telegram Bot**: python-telegram-bot library for control and notifications
- **Async Framework**: asyncio for concurrent operations
- **Web Framework**: aiohttp for HTTP requests
- **WebSocket**: websockets library for market data
- **Data Processing**: pandas for technical analysis
- **Configuration**: python-decouple for environment management

## Building and Running
1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate` (on Windows: `venv\Scripts\activate`)
4. Install dependencies: `pip install -r requirements.txt`
5. Configure environment variables for MXC API keys and Telegram bot
6. Run the bot: `python -m src.main`

## Development Conventions
- Use Python's logging module for proper logging
- Follow PEP 8 style guide for Python code
- Implement proper error handling for API calls
- Securely manage API keys and credentials
- Include unit tests for critical functions
- Use async/await for non-blocking operations
- Implement rate limiting to respect API constraints

## Implemented Features
- **High-Frequency Trading**: Optimized for scalping strategies with 10ms market data updates
- **Range Scalping Strategy**: Places both long and short orders at 1-hour min/max levels with 10% stop loss risk
- **Futures Trading Strategy**: Advanced futures trading with leverage and position management
- **Pair Selection**: Dynamic trading pair configuration via Telegram and web interface
- **Web Interface**: Complete web-based dashboard to control bot alongside Telegram
- **Risk Parameter Controls**: Adjust risk settings (daily loss, risk per trade, etc.) via both Telegram and web interface
- **Position Size Controls**: Configure position sizing via both Telegram and web interface
- **Real-Time Monitoring**: WebSocket integration for live market data
- **Risk Management**: Daily loss limits, position sizing controls, stop-losses
- **Telegram Control**: Start/stop trading, check status, receive notifications
- **Performance Tracking**: Detailed metrics and statistics
- **Technical Analysis**: Multiple indicators (SMA, EMA, RSI, Bollinger Bands, etc.)
- **Secure Operations**: Encrypted API communication, IP whitelisting support
- **Rate Limiting**: Proper handling to avoid API restrictions

## Security Considerations
- API keys should be stored securely and not committed to version control
- Implements rate limiting to comply with exchange API requirements
- Secure all network communications via HTTPS/WebSocket
- Includes proper authentication and authorization mechanisms
- Position sizing controls to limit risk per trade
- Daily loss limits to prevent excessive drawdowns

## Key Components
1. **Exchange Module**: Handles all communication with MXC API (REST and WebSocket)
2. **Strategy Module**: Implements scalping algorithms with technical analysis
3. **Risk Management**: Controls position sizing, daily losses, and consecutive losses
4. **Telegram Bot**: Provides control interface and notifications
5. **Monitoring**: Tracks performance metrics and logs activities
6. **Configuration**: Manages settings and credentials securely