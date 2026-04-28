"""
Trading API for Demo Trading System
Provides REST endpoints for executing trades and managing portfolio
"""

from flask import Flask, request, jsonify
from trading.demo_trader import DemoTrader
from config import Config
from utils.logger import Logger
import threading
import uuid

class TradingAPI:
    def __init__(self, app: Flask, config: Config, logger: Logger):
        self.app = app
        self.config = config
        self.logger = logger
        self.demo_trader = DemoTrader(config, logger)
        self.active_trades = {}  # Track active trades by ID
        
        self.setup_routes()
    
    def setup_routes(self):
        """Setup trading API routes"""
        
        @self.app.route('/api/trading/execute', methods=['POST'])
        def execute_trade():
            """Execute a demo trade"""
            try:
                data = request.get_json()
                opportunity = data.get('opportunity')
                
                if not opportunity:
                    return jsonify({"error": "No opportunity provided"}), 400
                
                # Execute the trade
                result = self.demo_trader.execute_trade(opportunity)
                
                if result["success"]:
                    return jsonify({
                        "success": True,
                        "trade": result["trade"],
                        "message": result["message"]
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": result["error"]
                    }), 400
                    
            except Exception as e:
                self.logger.error(f"Trade execution error: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/trading/portfolio', methods=['GET'])
        def get_portfolio():
            """Get current portfolio status"""
            try:
                portfolio = self.demo_trader.get_portfolio_status()
                return jsonify(portfolio)
            except Exception as e:
                self.logger.error(f"Portfolio error: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/trading/history', methods=['GET'])
        def get_trade_history():
            """Get trade history"""
            try:
                limit = request.args.get('limit', 10, type=int)
                trades = self.demo_trader.get_recent_trades(limit)
                return jsonify({"trades": trades})
            except Exception as e:
                self.logger.error(f"Trade history error: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/trading/reset', methods=['POST'])
        def reset_account():
            """Reset demo account"""
            try:
                self.demo_trader.reset_demo_account()
                return jsonify({
                    "success": True,
                    "message": "Demo account reset successfully",
                    "balance": self.demo_trader.balance
                })
            except Exception as e:
                self.logger.error(f"Reset error: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/trading/status', methods=['GET'])
        def get_trading_status():
            """Get trading system status"""
            try:
                return jsonify({
                    "demo_trading_enabled": self.config.enable_demo_trading,
                    "current_balance": self.demo_trader.balance,
                    "total_trades": len(self.demo_trader.trade_history),
                    "scan_interval": self.config.scan_interval,
                    "risk_per_trade": self.config.risk_per_trade * 100
                })
            except Exception as e:
                self.logger.error(f"Status error: {e}")
                return jsonify({"error": str(e)}), 500
