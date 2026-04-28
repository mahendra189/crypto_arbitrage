import requests

class BinanceClient:
    def __init__(self, api_url="https://api.binance.com/api/v3/ticker/bookTicker"):
        self.api_url = api_url

    def fetch_market_data(self):
        """
        Fetches bid/ask data from Binance and formats it into
        a clean dictionary:
        {
            "BTCUSDT": {"bid": float, "ask": float},
            ...
        }
        """
        try:
            response = requests.get(self.api_url, timeout=5)
            response.raise_for_status()
            data = response.json()

            formatted_data = {}

            for item in data:
                symbol = item.get("symbol")

                try:
                    bid = float(item.get("bidPrice", 0))
                    ask = float(item.get("askPrice", 0))

                    # Skip invalid prices
                    if bid <= 0 or ask <= 0:
                        continue

                    formatted_data[symbol] = {
                        "bid": bid,
                        "ask": ask
                    }

                except (ValueError, TypeError):
                    continue

            return formatted_data

        except requests.RequestException as e:
            print(f"[ERROR] Binance fetch failed: {e}")
            return {}

    def get_filtered_symbols(self, symbols_list):
        """
        Filter only required symbols (for performance + cleaner graph)
        """
        data = self.fetch_market_data()
        filtered = {}

        for symbol in data:
            for coin in symbols_list:
                if coin in symbol:
                    filtered[symbol] = data[symbol]

        return filtered