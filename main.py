"""
Entry point for the live scanner, dashboard API, and paper-trading server.
"""

import os
import sys
import threading
import time

from flask import Flask, jsonify, request, send_from_directory

from arbitrage_engine import ArbitrageDetector
from paper_trading import PaperTrader

sys.stdout.reconfigure(encoding="utf-8")

PORT = int(os.getenv("PORT", "5000"))


class Config:
    def __init__(self):
        self.currencies = [
            "USDT", "BTC", "ETH", "BNB", "SOL",
            "XRP", "ADA", "DOGE", "AVAX", "DOT", "MATIC",
        ]

        # Execution assumptions
        self.fee = 0.00025
        self.slippage = 0.00015
        self.per_hop_cost = self.fee + self.slippage
        self.withdrawal_fee_usdt = 0.5

        # Opportunity quality filters
        self.min_profit_threshold = 0.01
        self.cross_broker_min_profit = 0.0001   # 0.01% in decimal
        self.min_display_profit_pct = 0.01
        self.max_display_profit_pct = 1.0
        self.min_confidence = 0.1
        self.min_estimated_pnl_usdt = 0.0

        # Scan cadence
        self.scan_interval = 2

        # Multi-hop realism
        self.min_cycle_length = 3
        self.max_cycle_length = 5

        # Cross-exchange
        self.enable_cross_broker = True
        self.broker_fees = {
            "Binance": 0.00025,
            "Coinbase": 0.004,
            "Kraken": 0.0016,
            "BinanceUS": 0.00025,
            "Bybit": 0.00025,
            "Bitget": 0.00025,
            "KuCoin": 0.0005,
            "HTX": 0.001,
            "GateIO": 0.001,
        }

        # Statistical arbitrage
        self.enable_stat_arb = True
        self.stat_arb_pairs = [
            ("BTCUSDT", "ETHUSDT"),
            ("ETHUSDT", "BNBUSDT"),
            ("BTCUSDT", "SOLUSDT"),
            ("ETHUSDT", "SOLUSDT"),
            ("ADAUSDT", "DOGEUSDT"),
            ("XRPUSDT", "ADAUSDT"),
            ("DOTUSDT", "AVAXUSDT"),
        ]
        self.stat_arb_window = 10               # Shortened window for faster testing signals
        self.stat_arb_z_threshold = 0.1         # Fire Stat Arb signal very quickly

        # Funding-rate arbitrage
        self.enable_funding_arb = True
        self.funding_rate_threshold = 0.0
        self.min_funding_period_profit_pct = 0.01
        self.max_funding_basis_pct = 5.0

        # Paper trading
        self.paper_trade_starting_balance_usdt = 10000.0
        self.default_trade_allocation_usdt = 1000.0

        # Conservative execution buffers (Lowered to 0 to show Raw Theoretical Data)
        self.execution_buffer_pct = 0.0
        self.cross_execution_buffer_pct = 0.0
        self.stat_execution_buffer_pct = 0.0
        self.funding_execution_buffer_pct = 0.0

        self.max_opportunities_display = 20


class Logger:
    def __init__(self):
        self.history = []
        self.lock = threading.Lock()

    def _log(self, level, message):
        entry = f"[{level}] {message}"
        print(entry)
        with self.lock:
            self.history.append(entry)
            if len(self.history) > 150:
                self.history.pop(0)

    def info(self, message):
        self._log("INFO", message)

    def debug(self, message):
        self._log("DEBUG", message)

    def error(self, message):
        self._log("ERROR", message)

    def signal(self, message):
        self._log("SIGNAL", message)

    def warning(self, message):
        self._log("WARNING", message)


app = Flask(__name__)
SERVICES = {"detector": None, "paper_trader": None}


@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/api/dashboard")
def dashboard():
    detector = SERVICES["detector"]
    paper_trader = SERVICES["paper_trader"]
    return jsonify(detector.get_dashboard_data(paper_trader.get_state()))


@app.route("/api/paper/state")
def paper_state():
    return jsonify(SERVICES["paper_trader"].get_state())


@app.route("/api/paper/trade", methods=["POST"])
def paper_trade():
    payload = request.get_json(silent=True) or {}
    opportunity_id = payload.get("opportunity_id")
    if not opportunity_id:
        return jsonify({"ok": False, "error": "Missing opportunity_id."}), 400

    detector = SERVICES["detector"]
    opportunity = detector.get_opportunity_by_id(opportunity_id)
    if not opportunity:
        return jsonify({"ok": False, "error": "Opportunity not found or expired."}), 404

    result = SERVICES["paper_trader"].execute(
        opportunity,
        payload.get("allocation_usdt"),
    )
    status = 200 if result.get("ok") else 400
    return jsonify(result), status


@app.route("/api/paper/reset", methods=["POST"])
def reset_paper():
    SERVICES["paper_trader"].reset()
    return jsonify({"ok": True, "account": SERVICES["paper_trader"].get_state()})


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory("web", filename)


def run_scanner(detector, config):
    while True:
        try:
            detector.scan()
        except KeyboardInterrupt:
            break
        except Exception as exc:
            detector.record_runtime_error(str(exc))
            print(f"[ERROR] Scanner exception: {exc}")
            time.sleep(5)
            continue

        time.sleep(config.scan_interval)


def main():
    logger = Logger()
    config = Config()
    detector = ArbitrageDetector(config, logger)
    paper_trader = PaperTrader(config, logger)
    detector.set_paper_state_provider(paper_trader.get_state)

    SERVICES["detector"] = detector
    SERVICES["paper_trader"] = paper_trader

    logger.info(f"Starting arbitrage scanner + web server on port {PORT}...")

    scanner_thread = threading.Thread(
        target=run_scanner,
        args=(detector, config),
        daemon=True,
    )
    scanner_thread.start()

    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
