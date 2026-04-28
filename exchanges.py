"""
Exchange clients and cross-broker opportunity aggregation.
"""

import threading
import time

import requests

TOP10_USDT = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
    "PEPEUSDT", "SHIBUSDT", "NEARUSDT", "INJUSDT", "SUIUSDT",
    "SEIUSDT", "APTUSDT", "FETUSDT", "RENDERUSDT", "ARBUSDT"
]
TOP10_BASES = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT", "MATIC",
    "PEPE", "SHIB", "NEAR", "INJ", "SUI", "SEI", "APT", "FET", "RENDER", "ARB"
]

HTTP = requests.Session()
HTTP.trust_env = False
HTTP.headers.update({"User-Agent": "CryptoArbitrageEngine/1.0"})


def _safe_get_json(url, timeout=10):
    response = HTTP.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class BrokerClient:
    def __init__(self, name, api_url):
        self.name = name
        self.api_url = api_url

    def fetch_market_data(self):
        try:
            return _safe_get_json(self.api_url, timeout=10)
        except (requests.RequestException, ValueError) as exc:
            print(f"[{self.name}] {exc}")
            return None


class BinanceClient(BrokerClient):
    def __init__(self):
        super().__init__("Binance", "https://api.binance.com/api/v3/ticker/bookTicker")

    def fetch_futures_data(self):
        try:
            data = _safe_get_json("https://fapi.binance.com/fapi/v1/premiumIndex", timeout=10)
            return [item for item in data if item.get("symbol") in TOP10_USDT]
        except (requests.RequestException, ValueError) as exc:
            print(f"[Binance Futures] {exc}")
            return None


class CoinbaseClient(BrokerClient):
    def __init__(self):
        # Using real actively maintained public API 
        super().__init__("Coinbase", "https://api.exchange.coinbase.com/products/")
        self.targets = ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "AVAX-USD", "DOT-USD", "MATIC-USD"]

    def fetch_market_data(self):
        try:
            result = []
            for pair in self.targets:
                try:
                    data = _safe_get_json(self.api_url + f"{pair}/ticker", timeout=5)
                    result.append({
                        "symbol": pair,
                        "bidPrice": str(data.get("bid", 0)),
                        "askPrice": str(data.get("ask", 0)),
                        "bidQty": str(data.get("volume", 0)),
                        "askQty": str(data.get("volume", 0)),
                    })
                except (requests.RequestException, ValueError):
                    pass
            return result if result else None
        except Exception as exc:
            print(f"[Coinbase] {exc}")
            return None


class KrakenClient(BrokerClient):
    def __init__(self):
        # Removed pair limit to fetch the full realtime public ticker roster
        super().__init__("Kraken", "https://api.kraken.com/0/public/Ticker")

    def fetch_market_data(self):
        try:
            data = _safe_get_json(self.api_url, timeout=10)
            if data.get("error"):
                print(f"[Kraken] {data['error']}")
                return None

            result = []
            for pair, ticker in data.get("result", {}).items():
                result.append({
                    "symbol": pair,
                    "bidPrice": ticker.get("b", ["0"])[0],
                    "askPrice": ticker.get("a", ["0"])[0],
                    "bidQty": ticker.get("b", ["0", "0"])[1],
                    "askQty": ticker.get("a", ["0", "0"])[1],
                })
            return result
        except (requests.RequestException, ValueError) as exc:
            print(f"[Kraken] {exc}")
            return None


class BinanceUSClient(BrokerClient):
    def __init__(self):
        super().__init__("BinanceUS", "https://api.binance.us/api/v3/ticker/bookTicker")


class BybitClient(BrokerClient):
    def __init__(self):
        super().__init__("Bybit", "https://api.bybit.com/v5/market/tickers?category=spot")

    def fetch_market_data(self):
        try:
            data = _safe_get_json(self.api_url, timeout=10)
            if data.get("retCode") != 0:
                return None

            result = []
            for ticker in data.get("result", {}).get("list", []):
                symbol = ticker.get("symbol", "")
                if symbol in TOP10_USDT:
                    result.append({
                        "symbol": symbol,
                        "bidPrice": ticker.get("bid1Price", "0"),
                        "askPrice": ticker.get("ask1Price", "0"),
                        "bidQty": ticker.get("bid1Size", "0"),
                        "askQty": ticker.get("ask1Size", "0"),
                    })
            return result
        except (requests.RequestException, ValueError) as exc:
            print(f"[Bybit] {exc}")
            return None


class BitgetClient(BrokerClient):
    def __init__(self):
        super().__init__("Bitget", "https://api.bitget.com/api/v2/spot/market/tickers")

    def fetch_market_data(self):
        try:
            data = _safe_get_json(self.api_url, timeout=10)
            if data.get("code") != "00000":
                return None

            result = []
            for ticker in data.get("data", []):
                symbol = ticker.get("symbol", "")
                bid = ticker.get("bidPr", "0")
                ask = ticker.get("askPr", "0")
                if symbol in TOP10_USDT and _safe_float(bid) > 0 and _safe_float(ask) > 0:
                    result.append({
                        "symbol": symbol,
                        "bidPrice": bid,
                        "askPrice": ask,
                        "bidQty": ticker.get("bidSz", "0"),
                        "askQty": ticker.get("askSz", "0"),
                    })
            return result
        except (requests.RequestException, ValueError) as exc:
            print(f"[Bitget] {exc}")
            return None


class KuCoinClient(BrokerClient):
    def __init__(self):
        super().__init__("KuCoin", "https://api.kucoin.com/api/v1/market/allTickers")

    def fetch_market_data(self):
        try:
            data = _safe_get_json(self.api_url, timeout=10)
            if data.get("code") != "200000":
                return None

            targets = {f"{base}-USDT" for base in TOP10_BASES}
            result = []
            for ticker in data.get("data", {}).get("ticker", []):
                symbol = ticker.get("symbol", "")
                bid = ticker.get("buy", "0")
                ask = ticker.get("sell", "0")
                if symbol in targets and _safe_float(bid) > 0 and _safe_float(ask) > 0:
                    result.append({
                        "symbol": symbol,
                        "bidPrice": bid,
                        "askPrice": ask,
                        "bidQty": ticker.get("buySize", "0"),
                        "askQty": ticker.get("sellSize", "0"),
                    })
            return result
        except (requests.RequestException, ValueError) as exc:
            print(f"[KuCoin] {exc}")
            return None


class HTXClient(BrokerClient):
    def __init__(self):
        super().__init__("HTX", "https://api.huobi.pro/market/tickers")

    def fetch_market_data(self):
        try:
            data = _safe_get_json(self.api_url, timeout=10)
            if data.get("status") != "ok":
                return None

            targets = {symbol.lower() for symbol in TOP10_USDT}
            result = []
            for ticker in data.get("data", []):
                symbol = ticker.get("symbol", "")
                if symbol in targets:
                    result.append({
                        "symbol": symbol.upper(),
                        "bidPrice": str(ticker.get("bid", 0)),
                        "askPrice": str(ticker.get("ask", 0)),
                        "bidQty": str(ticker.get("bidSize", 0)),
                        "askQty": str(ticker.get("askSize", 0)),
                    })
            return result
        except (requests.RequestException, ValueError) as exc:
            print(f"[HTX] {exc}")
            return None


class GateIOClient(BrokerClient):
    def __init__(self):
        super().__init__("GateIO", "https://api.gateio.ws/api/v4/spot/tickers")

    def fetch_market_data(self):
        try:
            data = _safe_get_json(self.api_url, timeout=10)
            targets = {f"{base}_USDT" for base in TOP10_BASES}
            result = []
            for ticker in data:
                symbol = ticker.get("currency_pair", "")
                if symbol.upper() in targets:
                    result.append({
                        "symbol": symbol.upper(),
                        "bidPrice": ticker.get("highest_bid", "0"),
                        "askPrice": ticker.get("lowest_ask", "0"),
                        "bidQty": ticker.get("base_volume", "0"),
                        "askQty": ticker.get("base_volume", "0"),
                    })
            return result
        except (requests.RequestException, ValueError) as exc:
            print(f"[GateIO] {exc}")
            return None


class CrossBrokerAggregator:
    def __init__(self, logger, config):
        self.logger = logger
        self.config = config
        self.brokers = {
            "Binance": BinanceClient(),
            "Coinbase": CoinbaseClient(),
            "Kraken": KrakenClient(),
            "BinanceUS": BinanceUSClient(),
            "Bybit": BybitClient(),
            "Bitget": BitgetClient(),
            "KuCoin": KuCoinClient(),
            "HTX": HTXClient(),
            "GateIO": GateIOClient(),
        }
        self.market_data = {}
        self.last_fetch_errors = {}
        self.last_update = 0.0
        self.broker_fees = config.broker_fees
        self.withdrawal_fee = config.withdrawal_fee_usdt

    def fetch_all_market_data(self):
        threads = []
        results = {}
        errors = {}
        lock = threading.Lock()

        def _fetch(name, client):
            try:
                data = client.fetch_market_data()
                with lock:
                    if data:
                        results[name] = data
                        self.logger.debug(f"{name}: {len(data)} tickers")
                    else:
                        errors[name] = "No data returned."
                        self.logger.warning(f"{name}: no data")
            except Exception as exc:  # noqa: BLE001
                with lock:
                    errors[name] = str(exc)
                self.logger.error(f"{name}: {exc}")

        for name, client in self.brokers.items():
            thread = threading.Thread(target=_fetch, args=(name, client), daemon=True)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join(timeout=12)

        self.market_data = results
        self.last_fetch_errors = errors
        self.last_update = time.time()
        return results

    @staticmethod
    def normalize_symbol(symbol, broker_name):
        normalized = symbol.upper().replace("-", "").replace("_", "")
        if normalized.startswith("XXBT"):
            normalized = "BTC" + normalized[4:]
        elif normalized.startswith("XBT"):
            normalized = "BTC" + normalized[3:]
        if normalized.startswith("XETH"):
            normalized = "ETH" + normalized[4:]
        if normalized.endswith("USD") and not normalized.endswith("USDT"):
            normalized += "T"
        return normalized

    def find_cross_broker_opportunities(self):
        if not self.market_data:
            return []

        opportunities = []
        min_threshold_pct = self.config.cross_broker_min_profit * 100.0

        for pair in TOP10_USDT:
            prices = {}
            for broker_name, data in self.market_data.items():
                for item in data:
                    if self.normalize_symbol(item.get("symbol", ""), broker_name) != pair:
                        continue

                    bid = _safe_float(item.get("bidPrice", 0))
                    ask = _safe_float(item.get("askPrice", 0))
                    if bid <= 0 or ask <= 0:
                        continue

                    prices[broker_name] = {
                        "bid": bid,
                        "ask": ask,
                        "bid_qty": _safe_float(item.get("bidQty", 0)),
                        "ask_qty": _safe_float(item.get("askQty", 0)),
                    }

            if len(prices) < 2:
                continue

            broker_names = list(prices.keys())
            for buy_broker in broker_names:
                for sell_broker in broker_names:
                    if buy_broker == sell_broker:
                        continue

                    ask_price = prices[buy_broker]["ask"]
                    bid_price = prices[sell_broker]["bid"]
                    if ask_price <= 0 or bid_price <= ask_price:
                        continue

                    gross_profit = bid_price - ask_price
                    gross_pct = (gross_profit / ask_price) * 100.0

                    # Calculate individual fees
                    buy_fee = ask_price * self.broker_fees.get(buy_broker, 0.001)
                    sell_fee = bid_price * self.broker_fees.get(sell_broker, 0.001)

                    # 1. Spatial Arbitrage (Involves transferring assets, so apply withdrawal fee)
                    spatial_total_fees = buy_fee + sell_fee + self.withdrawal_fee
                    spatial_total_fees_pct = (spatial_total_fees / ask_price) * 100.0
                    spatial_net_pct = ((gross_profit - spatial_total_fees) / ask_price) * 100.0
                    spatial_realistic_net_pct = spatial_net_pct - self.config.cross_execution_buffer_pct - 0.05 # extra buffer for transfer
                    
                    max_notional = self._estimate_max_notional(prices[buy_broker], prices[sell_broker])
                    confidence = self._calculate_confidence(ask_price, bid_price, prices[buy_broker], prices[sell_broker])

                    if spatial_realistic_net_pct >= min_threshold_pct:
                        opportunities.append({
                            "type": "spatial_arbitrage",
                            "pair": pair,
                            "buy_broker": buy_broker,
                            "sell_broker": sell_broker,
                            "buy_price": ask_price,
                            "sell_price": bid_price,
                            "gross_profit_pct": round(gross_pct, 4),
                            "total_fees_pct": round(spatial_total_fees_pct, 4),
                            "profit_pct": round(spatial_net_pct, 4),
                            "net_profit": round(spatial_net_pct, 4),
                            "trade_profit_pct": round(spatial_net_pct, 4),
                            "realistic_net_profit_pct": round(spatial_realistic_net_pct, 4),
                            "max_notional_usdt": round(max_notional, 2),
                            "path": f"Transfer: Buy {pair} on {buy_broker} @ {ask_price:.2f} -> Sell on {sell_broker} @ {bid_price:.2f}",
                            "confidence": confidence,
                        })

                    # 2. Cross-Exchange Arbitrage (Simultaneous, capital required on both, no transfer fee)
                    cross_total_fees = buy_fee + sell_fee
                    cross_total_fees_pct = (cross_total_fees / ask_price) * 100.0
                    cross_net_pct = ((gross_profit - cross_total_fees) / ask_price) * 100.0
                    cross_realistic_net_pct = cross_net_pct - self.config.cross_execution_buffer_pct
                    
                    if cross_realistic_net_pct >= min_threshold_pct:
                        opportunities.append({
                            "type": "cross_broker",
                            "pair": pair,
                            "buy_broker": buy_broker,
                            "sell_broker": sell_broker,
                            "buy_price": ask_price,
                            "sell_price": bid_price,
                            "gross_profit_pct": round(gross_pct, 4),
                            "total_fees_pct": round(cross_total_fees_pct, 4),
                            "profit_pct": round(cross_net_pct, 4),
                            "net_profit": round(cross_net_pct, 4),
                            "trade_profit_pct": round(cross_net_pct, 4),
                            "realistic_net_profit_pct": round(cross_realistic_net_pct, 4),
                            "max_notional_usdt": round(max_notional, 2),
                            "path": f"Simultaneous: Buy {pair} on {buy_broker} & Sell on {sell_broker}",
                            "confidence": round(confidence * 0.95, 2), # Slightly lower confidence due to double execution risk
                        })

        opportunities.sort(
            key=lambda item: (item.get("realistic_net_profit_pct", 0), item.get("confidence", 0)),
            reverse=True,
        )
        return opportunities[:20]

    @staticmethod
    def _estimate_max_notional(buy_side, sell_side):
        buy_notional = buy_side["ask"] * buy_side["ask_qty"] if buy_side["ask_qty"] > 0 else 0.0
        sell_notional = sell_side["bid"] * sell_side["bid_qty"] if sell_side["bid_qty"] > 0 else 0.0
        if buy_notional > 0 and sell_notional > 0:
            return min(buy_notional, sell_notional)
        return 0.0

    @staticmethod
    def _calculate_confidence(buy_price, sell_price, buy_data, sell_data):
        spread_ratio = max(0.0, (sell_price - buy_price) / buy_price) if buy_price > 0 else 0.0
        spread_conf = min(1.0, spread_ratio * 40.0)

        buy_spread = abs((buy_data["ask"] - buy_data["bid"]) / buy_data["ask"]) if buy_data["ask"] > 0 else 1.0
        sell_spread = abs((sell_data["ask"] - sell_data["bid"]) / sell_data["ask"]) if sell_data["ask"] > 0 else 1.0
        tightness = max(0.1, 1.0 - (buy_spread + sell_spread) * 30.0)

        return round(min(1.0, max(0.1, 0.45 * spread_conf + 0.55 * tightness)), 2)

    def get_broker_status(self):
        status = {}
        for name in self.brokers:
            data = self.market_data.get(name)
            status[name] = {
                "connected": bool(data),
                "pairs_count": len(data) if data else 0,
                "last_update": self.last_update,
                "error": self.last_fetch_errors.get(name, ""),
            }
        return status
