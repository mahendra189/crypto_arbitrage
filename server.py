from flask import Flask, render_template, send_from_directory, jsonify
import os
import json
from config import Config
from utils.logger import Logger
from trading.trading_api import TradingAPI

app = Flask(__name__)

# Initialize components
config = Config()
logger = Logger()
trading_api = TradingAPI(app, config, logger)

@app.route('/')
def index():
    return send_from_directory('web', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('web', filename)

@app.route('/data.json')
def get_data():
    """Serve the latest arbitrage data"""
    try:
        with open('web/data.json', 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({
            "top_opportunities": [],
            "logs": ["No data available"],
            "market_indices": {"BTC": 0, "ETH": 0, "BNB": 0}
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
