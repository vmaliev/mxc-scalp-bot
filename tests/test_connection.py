import asyncio
import unittest
import json
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from exchange.api_client import MXCClient
from exchange.market_data import MarketDataHandler


class MockWebSocketContext:
    """Async context manager wrapper around a mocked websocket."""

    def __init__(self, websocket):
        self.websocket = websocket

    async def __aenter__(self):
        return self.websocket

    async def __aexit__(self, exc_type, exc, tb):
        return False


class TestMXCConnection(unittest.TestCase):
    """Test MXC Exchange Connection"""
    
    def setUp(self):
        # Use test credentials (should be set in environment variables or config)
        self.api_key = "test_api_key"
        self.secret_key = "test_secret_key"
        self.client = MXCClient(self.api_key, self.secret_key)
        self.market_data = MarketDataHandler(self.client)
        
    def test_rest_api_connection(self):
        """Test REST API connection"""

        async def test():
            # Prevent real session creation
            self.client.initialize_session = AsyncMock()

            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.json = AsyncMock(return_value={'serverTime': 1620000000000})

            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            self.client.session = MagicMock()
            self.client.session.get.return_value = mock_context

            response = await self.client._make_request('GET', '/api/v3/time')
            self.assertIn('serverTime', response)

        asyncio.run(test())
        
    def test_websocket_connection(self):
        """Test WebSocket subscription helper sends request."""

        async def test():
            websocket_mock = AsyncMock()
            websocket_mock.send = AsyncMock()
            self.client.websocket = websocket_mock

            await self.client._subscribe_to_streams()
            websocket_mock.send.assert_awaited_once()

            # Ensure market callbacks structure can be triggered
            channel = 'spot@public.deal@BTCUSDT'
            callback = AsyncMock()
            self.client.market_callbacks[channel] = [callback]

            message = {
                'channel': channel,
                'data': [{'price': '100', 'qty': '0.1'}]
            }
            await self.client._handle_websocket_message(message)
            callback.assert_awaited_once_with(message['data'])

        asyncio.run(test())
        
    def test_market_data_handler(self):
        """Test Market Data Handler subscription and callbacks."""

        async def test():
            websocket_mock = AsyncMock()
            websocket_mock.send = AsyncMock()
            self.market_data.websocket = websocket_mock

            await self.market_data._subscribe_to_stream('BTCUSDT')
            websocket_mock.send.assert_awaited_once()

            callback = AsyncMock()
            channel = "spot@public.deals.v3.api.pb@10ms@BTCUSDT"
            self.market_data.callbacks[channel] = [callback]

            message = {'channel': channel, 'data': [{'price': '100'}]}
            await self.market_data._handle_message(message)

            callback.assert_awaited_once_with(message['data'])

        asyncio.run(test())


if __name__ == '__main__':
    unittest.main()
