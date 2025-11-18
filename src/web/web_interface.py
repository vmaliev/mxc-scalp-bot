"""
Web Controller Module for MXC Scalp Bot

Integrates web interface with the existing bot system
"""
import sys
import os
import asyncio
import logging
from concurrent.futures import TimeoutError as FuturesTimeout

sys.path.insert(0, os.path.abspath('.'))

from flask import Flask, render_template, request, jsonify
from threading import Thread
from src.config.settings import Settings
from src.exchange.api_client import MXCClient
from src.strategies.scalping_strategy import ScalpingStrategy
from src.strategies.range_scalp_strategy import RangeScalpStrategy
from src.strategies.futures_strategy import FuturesStrategy
from src.monitoring.metrics import MetricsManager
from src.risk_management.risk_calculator import RiskManager


class WebBotController:
    """
    Controller that handles both web interface and bot management
    Can work with existing components or initialize its own
    """
    
    def __init__(self, scalping_strategy=None, range_scalp_strategy=None,
                 futures_strategy=None, metrics_manager=None,
                 risk_manager=None, settings=None, mxc_client=None,
                 event_loop: asyncio.AbstractEventLoop = None):
        # Initialize Flask app
        import os
        template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
        self.app = Flask(__name__, template_folder=template_dir)
        self.setup_routes()
        
        # Accept existing components or initialize our own
        self.scalping_strategy = scalping_strategy
        self.range_scalp_strategy = range_scalp_strategy
        self.futures_strategy = futures_strategy
        self.metrics_manager = metrics_manager
        self.risk_manager = risk_manager
        self.settings = settings
        self.mxc_client = mxc_client
        self.event_loop = event_loop
        self.logger = logging.getLogger(__name__)

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Assign the main bot asyncio loop for coroutines."""
        self.event_loop = loop

    def _run_async_task(self, coro, timeout: float = 15.0):
        """Run MXC client coroutine on the main loop or a temporary loop."""
        if coro is None:
            return None

        loop = self.event_loop
        try:
            if loop and loop.is_running():
                future = asyncio.run_coroutine_threadsafe(coro, loop)
                return future.result(timeout=timeout)
            # Fallback for standalone usage
            return asyncio.run(coro)
        except FuturesTimeout:
            raise TimeoutError("Timed out waiting for exchange response")
        except RuntimeError as exc:
            # If loop reference is invalid, fallback to running in a fresh loop
            return asyncio.run(coro)

    
    def setup_routes(self):
        """Setup Flask routes."""
        @self.app.route('/')
        def index():
            return render_template('dashboard.html', 
                                 status=self.get_status(),
                                 risk_params=self.get_risk_parameters(),
                                 credentials=self.get_credentials_status())
        
        @self.app.route('/status')
        def status():
            return jsonify(self.get_status())
        
        @self.app.route('/start_scalp', methods=['POST'])
        def start_scalp():
            if self.scalping_strategy:
                try:
                    self.scalping_strategy.start()
                    return jsonify({'status': 'success', 'message': 'Scalping strategy started'})
                except Exception as e:
                    return jsonify({'status': 'error', 'message': f'Error starting scalping strategy: {str(e)}'})
            return jsonify({'status': 'error', 'message': 'Scalping strategy not available'})
        
        @self.app.route('/stop_scalp', methods=['POST'])
        def stop_scalp():
            if self.scalping_strategy:
                try:
                    self.scalping_strategy.stop()
                    return jsonify({'status': 'success', 'message': 'Scalping strategy stopped'})
                except Exception as e:
                    return jsonify({'status': 'error', 'message': f'Error stopping scalping strategy: {str(e)}'})
            return jsonify({'status': 'error', 'message': 'Scalping strategy not available'})
        
        @self.app.route('/start_range', methods=['POST'])
        def start_range():
            if self.range_scalp_strategy:
                try:
                    self.range_scalp_strategy.start()
                    return jsonify({'status': 'success', 'message': 'Range scalping strategy started'})
                except Exception as e:
                    return jsonify({'status': 'error', 'message': f'Error starting range strategy: {str(e)}'})
            return jsonify({'status': 'error', 'message': 'Range scalping strategy not available'})
        
        @self.app.route('/stop_range', methods=['POST'])
        def stop_range():
            if self.range_scalp_strategy:
                try:
                    self.range_scalp_strategy.stop()
                    return jsonify({'status': 'success', 'message': 'Range scalping strategy stopped'})
                except Exception as e:
                    return jsonify({'status': 'error', 'message': f'Error stopping range strategy: {str(e)}'})
            return jsonify({'status': 'error', 'message': 'Range scalping strategy not available'})
        
        @self.app.route('/start_futures', methods=['POST'])
        def start_futures():
            if self.futures_strategy:
                try:
                    self.futures_strategy.start()
                    return jsonify({'status': 'success', 'message': 'Futures strategy started'})
                except Exception as e:
                    return jsonify({'status': 'error', 'message': f'Error starting futures strategy: {str(e)}'})
            return jsonify({'status': 'error', 'message': 'Futures strategy not available'})
        
        @self.app.route('/stop_futures', methods=['POST'])
        def stop_futures():
            if self.futures_strategy:
                try:
                    self.futures_strategy.stop()
                    return jsonify({'status': 'success', 'message': 'Futures strategy stopped'})
                except Exception as e:
                    return jsonify({'status': 'error', 'message': f'Error stopping futures strategy: {str(e)}'})
            return jsonify({'status': 'error', 'message': 'Futures strategy not available'})
        
        @self.app.route('/set_pairs', methods=['POST'])
        def set_pairs():
            pairs_str = request.form.get('pairs', '')
            if pairs_str:
                try:
                    pairs = [pair.strip().upper() for pair in pairs_str.split(',') if pair.strip()]
                    if pairs:
                        success_count = 0
                        if self.scalping_strategy:
                            self.scalping_strategy.trading_pairs = pairs
                            success_count += 1
                        if self.range_scalp_strategy:
                            self.range_scalp_strategy.trading_pairs = pairs
                            success_count += 1
                        if self.futures_strategy:
                            self.futures_strategy.set_trading_pairs(pairs)
                            success_count += 1
                            
                        return jsonify({'status': 'success', 'message': f'Trading pairs updated to: {", ".join(pairs)} ({success_count} strategies updated)'})
                except Exception as e:
                    return jsonify({'status': 'error', 'message': f'Error setting pairs: {str(e)}'})
            return jsonify({'status': 'error', 'message': 'No valid pairs provided'})
        
        @self.app.route('/set_risk', methods=['POST'])
        def set_risk():
            if not self.settings:
                return jsonify({'status': 'error', 'message': 'Settings not available'})
            
            try:
                updates = 0
                # Handle different risk parameters
                for param_name, value in request.form.items():
                    if param_name == 'max_daily_loss' and value:
                        try:
                            self.settings.max_daily_loss = float(value)
                            updates += 1
                        except ValueError:
                            pass
                    elif param_name == 'risk_per_trade' and value:
                        try:
                            self.settings.risk_per_trade = float(value)
                            updates += 1
                        except ValueError:
                            pass
                    elif param_name == 'max_consecutive_losses' and value:
                        try:
                            self.settings.max_consecutive_losses = int(value)
                            updates += 1
                        except ValueError:
                            pass
                    elif param_name == 'profit_target' and value:
                        try:
                            self.settings.scalp_profit_target = float(value)
                            updates += 1
                        except ValueError:
                            pass
                    elif param_name == 'stop_loss' and value:
                        try:
                            self.settings.scalp_stop_loss = float(value)
                            updates += 1
                        except ValueError:
                            pass
                
                return jsonify({'status': 'success', 'message': f'{updates} risk parameters updated'})
            except Exception as e:
                return jsonify({'status': 'error', 'message': f'Error setting risk: {str(e)}'})
        
        @self.app.route('/set_size', methods=['POST'])
        def set_size():
            size_str = request.form.get('size', '')
            if size_str:
                try:
                    size = float(size_str)
                    if size > 0:
                        if self.settings:  # Use the settings object
                            self.settings.max_position_size = size
                        elif self.scalping_strategy and self.scalping_strategy.settings:
                            self.scalping_strategy.settings.max_position_size = size
                        return jsonify({'status': 'success', 'message': f'Max position size set to {size}'})
                    else:
                        return jsonify({'status': 'error', 'message': 'Position size must be positive'})
                except ValueError:
                    return jsonify({'status': 'error', 'message': 'Invalid position size'})
            return jsonify({'status': 'error', 'message': 'No position size provided'})
        
        @self.app.route('/metrics')
        def metrics():
            if self.metrics_manager:
                try:
                    stats = self.metrics_manager.get_statistics()
                    return jsonify(stats)
                except Exception as e:
                    return jsonify({'error': f'Error retrieving metrics: {str(e)}'})
            return jsonify({'error': 'Metrics manager not available'})
        
        @self.app.route('/set_credentials', methods=['POST'])
        def set_credentials():
            """Set API credentials."""
            try:
                # Get form values
                api_key = request.form.get('api_key', '').strip()
                secret_key = request.form.get('secret_key', '').strip()
                bot_token = request.form.get('bot_token', '').strip()
                telegram_users = request.form.get('telegram_users', '').strip()
                
                # Update settings if values provided
                if api_key and self.settings:
                    self.settings.api_key = api_key
                    os.environ['MXC_API_KEY'] = api_key  # Also update environment
                    
                if secret_key and self.settings:
                    self.settings.secret_key = secret_key
                    os.environ['MXC_SECRET_KEY'] = secret_key  # Also update environment

                    
                if bot_token and self.settings:
                    self.settings.telegram_bot_token = bot_token
                    os.environ['TELEGRAM_BOT_TOKEN'] = bot_token  # Also update environment
                    
                if telegram_users and self.settings:
                    # Parse comma-separated user IDs
                    user_ids = [int(uid.strip()) for uid in telegram_users.split(',') if uid.strip()]
                    self.settings.telegram_authorized_users = user_ids
                    os.environ['TELEGRAM_AUTHORIZED_USERS'] = ','.join(map(str, user_ids))  # Also update environment

                # Update MXC client credentials immediately so exchange data works without restart
                if self.mxc_client and (api_key or secret_key):
                    try:
                        self._run_async_task(
                            self.mxc_client.update_credentials(
                                api_key=api_key or None,
                                secret_key=secret_key or None
                            )
                        )
                        self.logger.info(
                            "Updated MXC client credentials via web UI (api_key_set=%s, secret_key_set=%s)",
                            bool(api_key), bool(secret_key)
                        )
                    except Exception as e:
                        return jsonify({'status': 'error', 'message': f'Error updating MXC client: {str(e)}'})
                
                self.logger.info(
                    "Credential update request processed (api_key=%s, secret_key=%s, bot_token=%s, users=%s)",
                    bool(api_key), bool(secret_key), bool(bot_token), bool(telegram_users)
                )
                return jsonify({'status': 'success', 'message': 'API credentials updated successfully'})
                
            except ValueError as e:
                return jsonify({'status': 'error', 'message': f'Invalid user ID format: {str(e)}'})
            except Exception as e:
                return jsonify({'status': 'error', 'message': f'Error setting credentials: {str(e)}'})
        
        @self.app.route('/test_credentials', methods=['POST'])
        def test_credentials():
            """Test API credentials by making a simple request."""
            try:
                if not self.mxc_client or not self.settings:
                    return jsonify({'status': 'error', 'message': 'MXC client not available'})
                
                if not self.settings.api_key or not self.settings.secret_key:
                    return jsonify({'status': 'error', 'message': 'API credentials not configured'})
                
                self.logger.info("Testing API credentials...")
                
                # Test 1: Get server time (public endpoint - no auth required)
                try:
                    server_time_result = self._run_async_task(
                        self.mxc_client._make_request('GET', '/api/v3/time', signed=False)
                    )
                    server_time_ok = 'serverTime' in server_time_result
                except Exception as e:
                    return jsonify({
                        'status': 'error',
                        'message': f'Failed to connect to MXC API: {str(e)}',
                        'details': 'Cannot reach MXC servers. Check your internet connection.'
                    })
                
                # Test 2: Get account info (requires valid credentials)
                try:
                    account_result = self._run_async_task(
                        self.mxc_client.get_account_info()
                    )
                    
                    if 'code' in account_result:
                        # Error response from API
                        error_code = account_result.get('code')
                        error_msg = account_result.get('msg', 'Unknown error')
                        
                        if error_code == 700002:
                            return jsonify({
                                'status': 'error',
                                'message': 'Invalid API signature',
                                'details': 'Your API credentials appear to be incorrect. Please verify:\n1. API Key is correct\n2. Secret Key is correct\n3. No extra spaces or characters\n4. API key has proper permissions (Spot Trading enabled)'
                            })
                        elif error_code == 700001:
                            return jsonify({
                                'status': 'error',
                                'message': 'Invalid API key',
                                'details': 'The API key is not recognized. Please check if it\'s correct and not deleted.'
                            })
                        else:
                            return jsonify({
                                'status': 'error',
                                'message': f'API Error {error_code}: {error_msg}',
                                'details': 'Check MXC API documentation for this error code.'
                            })
                    
                    # Success!
                    if 'balances' in account_result:
                        balance_count = len([b for b in account_result['balances'] 
                                           if float(b.get('free', 0)) + float(b.get('locked', 0)) > 0])
                        return jsonify({
                            'status': 'success',
                            'message': '✅ API credentials are valid!',
                            'details': f'Successfully connected to your MXC account. Found {balance_count} assets with balance.'
                        })
                    else:
                        return jsonify({
                            'status': 'warning',
                            'message': 'Connected but unexpected response',
                            'details': 'API responded but format was unexpected. Credentials might be valid.'
                        })
                        
                except Exception as e:
                    return jsonify({
                        'status': 'error',
                        'message': f'Error testing credentials: {str(e)}',
                        'details': 'An unexpected error occurred during testing.'
                    })
                    
            except Exception as e:
                return jsonify({'status': 'error', 'message': f'Test failed: {str(e)}'})
        
        @self.app.route('/balance_data')
        def get_balance():
            """Get account balance data from exchange."""
            try:
                if self.mxc_client and self.settings and self.settings.api_key and self.settings.secret_key:
                    try:
                        self.logger.info("Fetching balance data from MXC")
                        balances = self._run_async_task(self.mxc_client.get_balance()) or []
                        self.logger.info("Balance data retrieved: %d entries", len(balances))
                        return jsonify({'balances': balances})
                    except Exception as e:
                        self.logger.exception("Error fetching balances: %s", e)
                        return jsonify({'error': f'Error fetching balances: {str(e)}'})
                return jsonify({'error': 'Exchange client not available or credentials not set'})
            except Exception as e:
                return jsonify({'error': f'Error in get balance: {str(e)}'})

        @self.app.route('/open_orders_data')
        def get_open_orders():
            """Get open orders from exchange."""
            try:
                if self.mxc_client and self.settings and self.settings.api_key and self.settings.secret_key:
                    try:
                        symbol = getattr(self.settings, 'default_symbol', None)
                        self.logger.info("Fetching open orders (symbol=%s)", symbol)
                        orders = self._run_async_task(self.mxc_client.get_open_orders(symbol=symbol)) or []
                        self.logger.info("Open orders retrieved: %s", len(orders) if isinstance(orders, list) else 'n/a')
                        return jsonify({'orders': orders})
                    except Exception as e:
                        self.logger.exception("Error fetching open orders: %s", e)
                        return jsonify({'error': f'Error fetching open orders: {str(e)}'})
                return jsonify({'error': 'Exchange client not available or credentials not set'})
            except Exception as e:
                return jsonify({'error': f'Error in get open orders: {str(e)}'})

        @self.app.route('/positions_data')
        def get_positions():
            """Get positions from exchange."""
            try:
                if self.mxc_client and self.settings and self.settings.api_key and self.settings.secret_key:
                    try:
                        self.logger.info("Fetching positions data")
                        positions = self._run_async_task(self.mxc_client.get_position_info()) or {}
                        # Ensure consistent shape {"positions": [...]}
                        if isinstance(positions, dict):
                            self.logger.info(
                                "Positions retrieved: %d entries",
                                len(positions.get('positions', []))
                            )
                            return jsonify(positions)
                        self.logger.info("Positions retrieved (list): %d entries", len(positions))
                        return jsonify({'positions': positions})
                    except Exception as e:
                        self.logger.exception("Error fetching positions: %s", e)
                        return jsonify({'error': f'Error fetching positions: {str(e)}'})
                return jsonify({'error': 'Exchange client not available or credentials not set'})
            except Exception as e:
                return jsonify({'error': f'Error in get positions: {str(e)}'})

        @self.app.route('/trades_data')
        def get_trades():
            """Get recent trades from exchange."""
            try:
                if self.mxc_client and self.settings and self.settings.api_key and self.settings.secret_key:
                    try:
                        symbol = getattr(self.settings, 'default_symbol', 'BTCUSDT')
                        self.logger.info("Fetching trades (symbol=%s)", symbol)
                        trades = self._run_async_task(self.mxc_client.get_my_trades(symbol)) or []
                        self.logger.info("Trades retrieved: %d entries", len(trades))
                        return jsonify({'trades': trades})
                    except Exception as e:
                        self.logger.exception("Error fetching trades: %s", e)
                        return jsonify({'error': f'Error fetching trades: {str(e)}'})
                return jsonify({'error': 'Exchange client not available or credentials not set'})
            except Exception as e:
                return jsonify({'error': f'Error in get trades: {str(e)}'})
    
    def get_status(self):
        """Get current status of all components."""
        return {
            'scalping_running': self.scalping_strategy.is_running if self.scalping_strategy else False,
            'range_running': self.range_scalp_strategy.is_running if self.range_scalp_strategy else False,
            'futures_running': self.futures_strategy.is_running if self.futures_strategy else False,
            'trading_pairs': getattr(self.scalping_strategy, 'trading_pairs', []) if self.scalping_strategy else [],
            'active_strategies': sum([
                1 if self.scalping_strategy and self.scalping_strategy.is_running else 0,
                1 if self.range_scalp_strategy and self.range_scalp_strategy.is_running else 0,
                1 if self.futures_strategy and self.futures_strategy.is_running else 0
            ])
        }
    
    def get_risk_parameters(self):
        """Get current risk parameters."""
        return {
            'max_daily_loss': self.settings.max_daily_loss,
            'risk_per_trade': self.settings.risk_per_trade,
            'max_consecutive_losses': self.settings.max_consecutive_losses,
            'profit_target': self.settings.scalp_profit_target,
            'stop_loss': self.settings.scalp_stop_loss,
            'max_position_size': self.settings.max_position_size
        }
    
    def get_status(self):
        """Get current status of all components."""
        active_strategies = 0
        
        # Count active strategies
        if self.scalping_strategy and hasattr(self.scalping_strategy, 'is_running'):
            if self.scalping_strategy.is_running:
                active_strategies += 1
        if self.range_scalp_strategy and hasattr(self.range_scalp_strategy, 'is_running'):
            if self.range_scalp_strategy.is_running:
                active_strategies += 1
        if self.futures_strategy and hasattr(self.futures_strategy, 'is_running'):
            if self.futures_strategy.is_running:
                active_strategies += 1
        
        # Get trading pairs from scalping strategy if available
        trading_pairs = []
        if self.scalping_strategy and hasattr(self.scalping_strategy, 'trading_pairs'):
            trading_pairs = self.scalping_strategy.trading_pairs
        
        return {
            'scalping_running': (self.scalping_strategy.is_running 
                                 if self.scalping_strategy and hasattr(self.scalping_strategy, 'is_running') 
                                 else False),
            'range_running': (self.range_scalp_strategy.is_running 
                             if self.range_scalp_strategy and hasattr(self.range_scalp_strategy, 'is_running') 
                             else False),
            'futures_running': (self.futures_strategy.is_running 
                               if self.futures_strategy and hasattr(self.futures_strategy, 'is_running') 
                               else False),
            'trading_pairs': trading_pairs,
            'active_strategies': active_strategies
        }
    
    def get_risk_parameters(self):
        """Get current risk parameters."""
        if self.settings:
            return {
                'max_daily_loss': self.settings.max_daily_loss,
                'risk_per_trade': self.settings.risk_per_trade,
                'max_consecutive_losses': self.settings.max_consecutive_losses,
                'profit_target': self.settings.scalp_profit_target,
                'stop_loss': self.settings.scalp_stop_loss,
                'max_position_size': self.settings.max_position_size
            }
        return {}
    
    def get_credentials_status(self):
        """Get current status of API credentials."""
        if self.settings:
            return {
                'api_key_set': bool(getattr(self.settings, 'api_key', '')),
                'secret_key_set': bool(getattr(self.settings, 'secret_key', '')),
                'bot_token_set': bool(getattr(self.settings, 'telegram_bot_token', '')),
                'authorized_users_count': len(getattr(self.settings, 'telegram_authorized_users', []))
            }
        return {
            'api_key_set': False,
            'secret_key_set': False,
            'bot_token_set': False,
            'authorized_users_count': 0
        }

    def start_server(self, host='0.0.0.0', port=5000, debug=False):
        """Start the web server."""
        print(f"Starting web interface on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug, threaded=True)


def run_web_interface():
    """Function to run the web interface."""
    controller = WebBotController()
    controller.start_server()


if __name__ == '__main__':
    # For testing purposes
    controller = WebBotController()
    controller.start_server(debug=True)