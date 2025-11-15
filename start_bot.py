#!/usr/bin/env python3
"""
MXC Scalp Bot Starter Script

This script starts the complete trading bot with web interface and all features.
"""
import asyncio
import sys
import os
import signal
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / 'src'))

from src.main import MXCScalpBot


def main():
    """Main entry point for starting the bot."""
    print("="*60)
    print("🚀 MXC Scalp Trading Bot with Web Interface")
    print("="*60)
    print("Features:")
    print(" • Scalping, range scalping, and futures strategies")
    print(" • Real-time exchange data (balance, orders, positions, trades)")
    print(" • Risk management and position sizing controls")
    print(" • API credential management via web interface")
    print(" • Telegram bot control and notifications")
    print(" • Web dashboard at http://localhost:5001")
    print("="*60)
    print()
    
    # Create the bot instance
    bot = MXCScalpBot()
    
    try:
        # Run the bot
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("\n🛑 Shutdown signal received")
    except Exception as e:
        print(f"\n💥 Error running bot: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔒 Shutting down bot...")
        # Cleanup will happen in the bot's shutdown method


if __name__ == "__main__":
    main()