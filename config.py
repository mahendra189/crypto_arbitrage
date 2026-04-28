class Config:
    def __init__(self):

        self.api_url = "https://api.binance.com/api/v3/ticker/bookTicker"

        self.currencies = [
            "USDT", "BTC", "ETH", "BNB", "SOL",
            "MATIC", "AVAX", "LINK"
        ]

        self.fee = 0.001
        self.slippage = 0.001
        self.per_hop_cost = self.fee + self.slippage

        self.min_profit_threshold = 0.01
        self.cross_broker_min_profit = 0.01
        self.funding_rate_min_profit = 0.01

        self.scan_interval = 1

        self.min_cycle_length = 3
        self.max_cycle_length = 4

        self.enable_cross_broker = True
        self.supported_brokers = [
            "Binance", "BinanceUS", "Bybit", "KuCoin"
        ]

        self.cross_broker_pairs = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"
        ]

        self.broker_fees = {
            'Binance': 0.001,
            'BinanceUS': 0.001,
            'Bybit': 0.001,
            'KuCoin': 0.001
        }

        self.enable_stat_arb = True

        self.stat_arb_pairs = [
            ("BTCUSDT", "ETHUSDT"),
            ("ETHUSDT", "SOLUSDT"),
            ("BTCUSDT", "SOLUSDT")
        ]

        self.stat_arb_window = 50
        self.stat_arb_z_threshold = 2.0

        self.enable_funding_arb = True
        self.futures_api_url = "https://fapi.binance.com/fapi/v1/premiumIndex"

        self.funding_arb_symbols = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT"
        ]

        self.funding_rate_threshold = 0.0001

        self.max_opportunities_display = 30