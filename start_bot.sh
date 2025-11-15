#!/bin/bash
# Startup script for MXC Scalp Trading Bot with Web Interface

echo "Starting MXC Scalp Trading Bot with Enhanced Web Interface..."
echo "Features:"
echo "  - Scalping, range scalping, and futures strategies"
echo "  - Risk management controls"
echo "  - Position sizing controls"
echo "  - API credential management via web interface"
echo "  - Exchange data monitoring (balance, orders, positions, trades)"
echo ""

cd /Users/slava/mxc-scalp-bot
source bot_env/bin/activate
cd src

echo "Running in background..."
python main.py &

echo ""
echo "Bot started successfully!"
echo "Web interface available at: http://localhost:5001"
echo "The interface includes:"
echo "  - Strategy controls (start/stop)"
echo "  - Risk management settings"
echo "  - Position sizing"
echo "  - API credential configuration"
echo "  - Exchange data monitoring (balance, orders, positions, trades)"
echo ""