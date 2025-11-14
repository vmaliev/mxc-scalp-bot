"""
Web Control Interface for MXC Scalp Bot

Provides a web-based interface to control the trading bot alongside the Telegram bot
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for
import threading
import logging
import os

from config.settings import Settings
from exchange.api_client import MXCClient
from strategies.scalping_strategy import ScalpingStrategy
from strategies.range_scalp_strategy import RangeScalpStrategy
from strategies.futures_strategy import FuturesStrategy
from telegram_bot.bot_handler import TelegramBot
from monitoring.metrics import MetricsManager
from risk_management.risk_calculator import RiskManager


class WebController:
    """
    Web controller that manages the web interface for the trading bot
    """
    
    def __init__(self, bot_manager):
        self.bot_manager = bot_manager
        self.app = Flask(__name__)
        self.setup_routes()
        
    def setup_routes(self):
        """Setup web routes for the control interface."""
        
        @self.app.route('/')
        def index():
            """Main dashboard page."""
            return render_template('dashboard.html', 
                                 status=self.get_status(),
                                 risk_params=self.get_risk_params())
        
        @self.app.route('/status')
        def status():
            """Get bot status."""
            return jsonify(self.get_status())
        
        @self.app.route('/start_scalp', methods=['POST'])
        def start_scalp():
            """Start scalping strategy."""
            if self.bot_manager.scalping_strategy:
                self.bot_manager.scalping_strategy.start()
                return jsonify({'status': 'success', 'message': 'Scalping strategy started'})
            return jsonify({'status': 'error', 'message': 'Strategy not available'})
        
        @self.app.route('/stop_scalp', methods=['POST'])
        def stop_scalp():
            """Stop scalping strategy."""
            if self.bot_manager.scalping_strategy:
                self.bot_manager.scalping_strategy.stop()
                return jsonify({'status': 'success', 'message': 'Scalping strategy stopped'})
            return jsonify({'status': 'error', 'message': 'Strategy not available'})
        
        @self.app.route('/start_range', methods=['POST'])
        def start_range():
            """Start range scalping strategy."""
            if self.bot_manager.range_scalp_strategy:
                self.bot_manager.range_scalp_strategy.start()
                return jsonify({'status': 'success', 'message': 'Range scalping strategy started'})
            return jsonify({'status': 'error', 'message': 'Strategy not available'})
        
        @self.app.route('/stop_range', methods=['POST'])
        def stop_range():
            """Stop range scalping strategy."""
            if self.bot_manager.range_scalp_strategy:
                self.bot_manager.range_scalp_strategy.stop()
                return jsonify({'status': 'success', 'message': 'Range scalping strategy stopped'})
            return jsonify({'status': 'error', 'message': 'Strategy not available'})
        
        @self.app.route('/start_futures', methods=['POST'])
        def start_futures():
            """Start futures strategy."""
            if self.bot_manager.futures_strategy:
                self.bot_manager.futures_strategy.start()
                return jsonify({'status': 'success', 'message': 'Futures strategy started'})
            return jsonify({'status': 'error', 'message': 'Strategy not available'})
        
        @self.app.route('/stop_futures', methods=['POST'])
        def stop_futures():
            """Stop futures strategy."""
            if self.bot_manager.futures_strategy:
                self.bot_manager.futures_strategy.stop()
                return jsonify({'status': 'success', 'message': 'Futures strategy stopped'})
            return jsonify({'status': 'error', 'message': 'Strategy not available'})
        
        @self.app.route('/set_pairs', methods=['POST'])
        def set_pairs():
            """Set trading pairs."""
            pairs_str = request.form.get('pairs', '')
            pairs = [pair.strip().upper() for pair in pairs_str.split(',') if pair.strip()]
            
            if pairs:
                if self.bot_manager.scalping_strategy:
                    self.bot_manager.scalping_strategy.trading_pairs = pairs
                if self.bot_manager.range_scalp_strategy:
                    self.bot_manager.range_scalp_strategy.trading_pairs = pairs
                if self.bot_manager.futures_strategy:
                    self.bot_manager.futures_strategy.set_trading_pairs(pairs)
                
                return jsonify({'status': 'success', 'message': f'Trading pairs updated: {", ".join(pairs)}'})
            return jsonify({'status': 'error', 'message': 'No valid pairs provided'})
        
        @self.app.route('/set_risk', methods=['POST'])
        def set_risk():
            """Set risk parameters."""
            settings = self.bot_manager.scalping_strategy.settings if self.bot_manager.scalping_strategy else None
            if not settings:
                return jsonify({'status': 'error', 'message': 'Settings not available'})
            
            # Update various risk parameters
            max_daily_loss = request.form.get('max_daily_loss')
            risk_per_trade = request.form.get('risk_per_trade')
            max_consecutive_losses = request.form.get('max_consecutive_losses')
            profit_target = request.form.get('profit_target')
            stop_loss = request.form.get('stop_loss')
            
            updates = 0
            if max_daily_loss:
                try:
                    settings.max_daily_loss = float(max_daily_loss)
                    updates += 1
                except ValueError:
                    pass
            
            if risk_per_trade:
                try:
                    settings.risk_per_trade = float(risk_per_trade)
                    updates += 1
                except ValueError:
                    pass
            
            if max_consecutive_losses:
                try:
                    settings.max_consecutive_losses = int(max_consecutive_losses)
                    updates += 1
                except ValueError:
                    pass
            
            if profit_target:
                try:
                    settings.scalp_profit_target = float(profit_target)
                    updates += 1
                except ValueError:
                    pass
            
            if stop_loss:
                try:
                    settings.scalp_stop_loss = float(stop_loss)
                    updates += 1
                except ValueError:
                    pass
            
            return jsonify({'status': 'success', 'message': f'{updates} risk parameters updated'})
        
        @self.app.route('/set_size', methods=['POST'])
        def set_size():
            """Set position size."""
            size_str = request.form.get('size', '')
            if size_str:
                try:
                    size = float(size_str)
                    if size > 0:
                        if self.bot_manager.scalping_strategy:
                            self.bot_manager.scalping_strategy.settings.max_position_size = size
                        return jsonify({'status': 'success', 'message': f'Position size set to {size}'})
                except ValueError:
                    pass
            return jsonify({'status': 'error', 'message': 'Invalid position size'})
        
        @self.app.route('/metrics')
        def metrics():
            """Get trading metrics."""
            if self.bot_manager.metrics_manager:
                stats = self.bot_manager.metrics_manager.get_statistics()
                return jsonify(stats)
            return jsonify({'error': 'Metrics not available'})
    
    def get_status(self):
        """Get the current status of all components."""
        status = {
            'scalping_running': self.bot_manager.scalping_strategy.is_running if self.bot_manager.scalping_strategy else False,
            'range_running': self.bot_manager.range_scalp_strategy.is_running if self.bot_manager.range_scalp_strategy else False,
            'futures_running': self.bot_manager.futures_strategy.is_running if self.bot_manager.futures_strategy else False,
            'trading_pairs': [],
            'active_strategies': 0
        }
        
        if self.bot_manager.scalping_strategy:
            status['trading_pairs'] = self.bot_manager.scalping_strategy.trading_pairs
            if self.bot_manager.scalping_strategy.is_running:
                status['active_strategies'] += 1
        
        if self.bot_manager.range_scalp_strategy:
            if self.bot_manager.range_scalp_strategy.is_running:
                status['active_strategies'] += 1
        
        if self.bot_manager.futures_strategy:
            if self.bot_manager.futures_strategy.is_running:
                status['active_strategies'] += 1
        
        return status
    
    def get_risk_params(self):
        """Get current risk parameters."""
        if self.bot_manager.scalping_strategy:
            settings = self.bot_manager.scalping_strategy.settings
            return {
                'max_daily_loss': settings.max_daily_loss,
                'risk_per_trade': settings.risk_per_trade,
                'max_consecutive_losses': settings.max_consecutive_losses,
                'profit_target': settings.scalp_profit_target,
                'stop_loss': settings.scalp_stop_loss,
                'max_position_size': settings.max_position_size
            }
        return {}
    
    def start(self, host='0.0.0.0', port=5000, debug=False):
        """Start the web server."""
        print(f"Starting web interface on {host}:{port}")
        threading.Thread(target=lambda: self.app.run(host=host, port=port, debug=debug, use_reloader=False)).start()