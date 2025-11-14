"""
Market Data Handler for MXC Exchange

Manages WebSocket connections and provides market data to strategies
"""
import asyncio
import json
import websockets
from typing import Dict, Any, Callable, List
import logging


class MarketDataHandler:
    """
    Handles real-time market data from MXC exchange via WebSocket
    """
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.logger = logging.getLogger(__name__)
        
        # WebSocket connection
        self.websocket = None
        self.websocket_url = "wss://wbs-api.mexc.com/ws"
        self.is_connected = False
        
        # Market data callbacks
        self.callbacks: Dict[str, List[Callable]] = {}
        
        # Reconnection logic
        self.should_reconnect = True
        self.reconnect_delay = 5  # seconds
    
    def register_callback(self, symbol: str, callback: Callable):
        """Register a callback for market data updates for a specific symbol."""
        channel = f"spot@public.deals.v3.api.pb@10ms@{symbol}"
        if channel not in self.callbacks:
            self.callbacks[channel] = []
        self.callbacks[channel].append(callback)
        
        # Subscribe to the stream
        if self.is_connected:
            asyncio.create_task(self._subscribe_to_stream(symbol))
    
    async def _subscribe_to_stream(self, symbol: str):
        """Subscribe to market data stream for a symbol."""
        if not self.websocket:
            return
            
        # Subscribe to trade data for the symbol with 10ms updates for scalping
        subscribe_msg = {
            "method": "sub.public.deal",
            "param": {
                "symbol": symbol,
                "limit": 1
            }
        }
        
        try:
            await self.websocket.send(json.dumps(subscribe_msg))
            self.logger.info(f"Subscribed to market data for {symbol}")
        except Exception as e:
            self.logger.error(f"Error subscribing to {symbol}: {e}")
    
    async def connect(self):
        """Connect to the WebSocket and start listening for market data."""
        self.should_reconnect = True
        
        while self.should_reconnect:
            try:
                async with websockets.connect(self.websocket_url) as ws:
                    self.websocket = ws
                    self.is_connected = True
                    self.logger.info("Connected to MXC WebSocket")
                    
                    # Subscribe to all registered symbols
                    for channel in self.callbacks.keys():
                        # Extract symbol from channel name
                        symbol = channel.split('@')[-1]
                        await self._subscribe_to_stream(symbol)
                    
                    # Listen for messages
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            await self._handle_message(data)
                        except json.JSONDecodeError:
                            self.logger.error(f"Invalid JSON received: {message}")
                        except Exception as e:
                            self.logger.error(f"Error handling websocket message: {e}")
            
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("WebSocket connection closed, reconnecting...")
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
            
            if self.should_reconnect:
                self.logger.info(f"Reconnecting in {self.reconnect_delay} seconds...")
                await asyncio.sleep(self.reconnect_delay)
    
    async def _handle_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket messages."""
        try:
            if 'channel' in data and 'data' in data:
                channel = data['channel']
                message_data = data['data']
                
                # Notify registered callbacks
                if channel in self.callbacks:
                    for callback in self.callbacks[channel]:
                        try:
                            await callback(message_data)
                        except Exception as e:
                            self.logger.error(f"Error in market data callback: {e}")
            elif 'symbol' in data and 'data' in data:
                # Handle different message format
                symbol = data['symbol']
                channel = f"spot@public.deals.v3.api.pb@10ms@{symbol}"
                
                if channel in self.callbacks:
                    for callback in self.callbacks[channel]:
                        try:
                            await callback(data['data'])
                        except Exception as e:
                            self.logger.error(f"Error in market data callback: {e}")
        except Exception as e:
            self.logger.error(f"Error processing WebSocket message: {e}")
    
    async def disconnect(self):
        """Disconnect from the WebSocket."""
        self.should_reconnect = False
        if self.websocket:
            await self.websocket.close()
        self.is_connected = False
        self.logger.info("Disconnected from MXC WebSocket")