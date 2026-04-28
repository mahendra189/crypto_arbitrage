import requests

# ─── Top-10 symbol filters used across all clients ───────────────────────────
TOP10_USDT_SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT'
]

TOP10_BASES = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'MATIC']


class BrokerClient:
    """Base class for all exchange API clients."""
    def __init__(self, name, api_url):
        self.name = name
        self.api_url = api_url

    def fetch_market_data(self):
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching market data from {self.name}: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
#  BINANCE  (also provides futures / funding-rate data)
# ═══════════════════════════════════════════════════════════════════════════════

class BinanceClient(BrokerClient):
    def __init__(self):
        super().__init__("Binance", "https://api.binance.com/api/v3/ticker/bookTicker")

    # ── Futures: premiumIndex (funding rate + mark price) ─────────────────
    def fetch_futures_data(self):
        """Return list of {symbol, markPrice, indexPrice, lastFundingRate} dicts."""
        url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            # Filter to top-10 symbols
            return [item for item in data if item.get('symbol', '') in TOP10_USDT_SYMBOLS]
        except requests.RequestException as e:
            print(f"Error fetching Binance futures data: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
#  COINBASE
# ═══════════════════════════════════════════════════════════════════════════════

class CoinbaseClient(BrokerClient):
    def __init__(self):
        super().__init__("Coinbase", "https://api.pro.coinbase.com/products/BTC-USD/ticker")

    def fetch_market_data(self):
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [{
                'symbol': 'BTC-USD',
                'bidPrice': str(data.get('bid', 0)),
                'askPrice': str(data.get('ask', 0)),
                'bidQty': str(data.get('volume', 0)),
                'askQty': str(data.get('volume', 0))
            }]
        except requests.RequestException as e:
            print(f"Error fetching market data from {self.name}: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
#  KRAKEN
# ═══════════════════════════════════════════════════════════════════════════════

class KrakenClient(BrokerClient):
    def __init__(self):
        super().__init__("Kraken", "https://api.kraken.com/0/public/Ticker?pair=XBTUSD,ETHUSD")

    def fetch_market_data(self):
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            result = []

            if data.get('error'):
                print(f"Kraken API error: {data['error']}")
                return None

            for pair, ticker in data.get('result', {}).items():
                result.append({
                    'symbol': pair,
                    'bidPrice': ticker.get('b', ['0'])[0],
                    'askPrice': ticker.get('a', ['0'])[0],
                    'bidQty': ticker.get('b', ['0'])[1],
                    'askQty': ticker.get('a', ['0'])[1]
                })

            return result
        except requests.RequestException as e:
            print(f"Error fetching market data from {self.name}: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
#  BINANCE US
# ═══════════════════════════════════════════════════════════════════════════════

class BinanceUSClient(BrokerClient):
    def __init__(self):
        super().__init__("BinanceUS", "https://api.binance.us/api/v3/ticker/bookTicker")


# ═══════════════════════════════════════════════════════════════════════════════
#  BYBIT
# ═══════════════════════════════════════════════════════════════════════════════

class BybitClient(BrokerClient):
    def __init__(self):
        super().__init__("Bybit", "https://api.bybit.com/v5/market/tickers?category=spot")

    def fetch_market_data(self):
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            result = []

            if data.get('retCode') != 0:
                print(f"Bybit API error: {data.get('retMsg', 'Unknown error')}")
                return None

            for ticker in data.get('result', {}).get('list', []):
                symbol = ticker.get('symbol', '')
                if symbol in TOP10_USDT_SYMBOLS:
                    result.append({
                        'symbol': symbol,
                        'bidPrice': ticker.get('bid1Price', '0'),
                        'askPrice': ticker.get('ask1Price', '0'),
                        'bidQty': ticker.get('bid1Size', '0'),
                        'askQty': ticker.get('ask1Size', '0')
                    })

            return result
        except requests.RequestException as e:
            print(f"Error fetching market data from {self.name}: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
#  BITGET
# ═══════════════════════════════════════════════════════════════════════════════

class BitgetClient(BrokerClient):
    def __init__(self):
        super().__init__("Bitget", "https://api.bitget.com/api/v2/spot/market/tickers")

    def fetch_market_data(self):
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            result = []

            if data.get('code') != '00000':
                print(f"Bitget API error: {data.get('msg', 'Unknown error')}")
                return None

            for ticker in data.get('data', []):
                symbol = ticker.get('symbol', '')
                if symbol in TOP10_USDT_SYMBOLS:
                    bid_price = ticker.get('bidPrice', '0')
                    ask_price = ticker.get('askPrice', '0')

                    # Only add if we have valid prices
                    if bid_price != '0' and ask_price != '0' and float(bid_price) > 0 and float(ask_price) > 0:
                        result.append({
                            'symbol': symbol,
                            'bidPrice': bid_price,
                            'askPrice': ask_price,
                            'bidQty': ticker.get('bidSize', '0'),
                            'askQty': ticker.get('askSize', '0')
                        })

            return result
        except requests.RequestException as e:
            print(f"Error fetching market data from {self.name}: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
#  KUCOIN
# ═══════════════════════════════════════════════════════════════════════════════

class KuCoinClient(BrokerClient):
    def __init__(self):
        super().__init__("KuCoin", "https://api.kucoin.com/api/v1/market/allTickers")

    def fetch_market_data(self):
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            result = []

            if data.get('code') != '200000':
                print(f"KuCoin API error: {data.get('msg', 'Unknown error')}")
                return None

            # KuCoin uses "BTC-USDT" format — map to standard list
            kucoin_targets = [f"{b}-USDT" for b in TOP10_BASES]

            for ticker in data.get('data', {}).get('ticker', []):
                symbol = ticker.get('symbol', '')
                if symbol in kucoin_targets:
                    buy_price = ticker.get('buy', '0')
                    sell_price = ticker.get('sell', '0')

                    if buy_price and sell_price and float(buy_price) > 0 and float(sell_price) > 0:
                        result.append({
                            'symbol': symbol,
                            'bidPrice': buy_price,
                            'askPrice': sell_price,
                            'bidQty': ticker.get('buySize', '0'),
                            'askQty': ticker.get('sellSize', '0')
                        })

            return result
        except requests.RequestException as e:
            print(f"Error fetching market data from {self.name}: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
#  HTX (Huobi)
# ═══════════════════════════════════════════════════════════════════════════════

class HTXClient(BrokerClient):
    def __init__(self):
        super().__init__("HTX", "https://api.huobi.pro/market/tickers")

    def fetch_market_data(self):
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            result = []

            if data.get('status') != 'ok':
                print(f"HTX API error: {data.get('err-msg', 'Unknown error')}")
                return None

            htx_targets = [s.lower() for s in TOP10_USDT_SYMBOLS]

            for ticker in data.get('data', []):
                symbol = ticker.get('symbol', '')
                if symbol in htx_targets:
                    result.append({
                        'symbol': symbol.upper(),
                        'bidPrice': str(ticker.get('bid', 0)),
                        'askPrice': str(ticker.get('ask', 0)),
                        'bidQty': str(ticker.get('bidSize', 0)),
                        'askQty': str(ticker.get('askSize', 0))
                    })

            return result
        except requests.RequestException as e:
            print(f"Error fetching market data from {self.name}: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
#  GATE.IO
# ═══════════════════════════════════════════════════════════════════════════════

class GateIOClient(BrokerClient):
    def __init__(self):
        super().__init__("GateIO", "https://api.gateio.ws/api/v4/spot/tickers")

    def fetch_market_data(self):
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            result = []

            gateio_targets = [f"{b}_USDT" for b in TOP10_BASES]

            for ticker in data:
                symbol = ticker.get('currency_pair', '')
                if symbol.upper() in gateio_targets:
                    result.append({
                        'symbol': symbol.upper(),
                        'bidPrice': ticker.get('highest_bid', '0'),
                        'askPrice': ticker.get('lowest_ask', '0'),
                        'bidQty': ticker.get('base_volume', '0'),
                        'askQty': ticker.get('base_volume', '0')
                    })

            return result
        except requests.RequestException as e:
            print(f"Error fetching market data from {self.name}: {e}")
            return None