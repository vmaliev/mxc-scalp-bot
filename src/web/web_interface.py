"""
Web Controller Module for MXC Scalp Bot

Integrates web interface with the existing bot system
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from flask import Flask, render_template, request, jsonify
from threading import Thread
from config.settings import Settings
from exchange.api_client import MXCClient
from strategies.scalping_strategy import ScalpingStrategy
from strategies.range_scalp_strategy import RangeScalpStrategy
from strategies.futures_strategy import FuturesStrategy
from monitoring.metrics import MetricsManager
from risk_management.risk_calculator import RiskManager


class WebBotController:
    """
    Controller that handles both web interface and bot management
    Can work with existing components or initialize its own
    """
    
    def __init__(self, scalping_strategy=None, range_scalp_strategy=None, 
                 futures_strategy=None, metrics_manager=None, 
                 risk_manager=None, settings=None, mxc_client=None):
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
    
    def setup_routes(self):
        """Setup Flask routes."""
        @self.app.route('/')
        def index():
            return render_template('dashboard.html', 
                                 status=self.get_status(),
                                 risk_params=self.get_risk_parameters())
        
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