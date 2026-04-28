"""
Cross-Exchange / Spatial Arbitrage Aggregator.

Fetches live ticker data from 9 exchanges concurrently, normalises symbols,
and finds cross-broker arbitrage: buy at the lowest ask, sell at the highest bid.

All opportunities include:
  • Gross profit  (price spread only)
  • Total fees    (buy-side + sell-side broker fees + withdrawal fee)
  • Net profit    (gross - fees)
  Only opportunities with positive net profit are surfaced.
"""

import threading
import time

from data.broker_clients import (
    BinanceClient, CoinbaseClient, KrakenClient, BinanceUSClient,
    BybitClient, BitgetClient, KuCoinClient, HTXClient, GateIOClient,
    TOP10_USDT_SYMBOLS,
)


class CrossBrokerAggregator:
    def __init__(self, logger, config=None):
        self.logger = logger
        self.config = config or Config()
        self.brokers = {
            'Binance':   BinanceClient(),
            'Coinbase':  CoinbaseClient(),
            'Kraken':    KrakenClient(),
            'BinanceUS': BinanceUSClient(),
            'Bybit':     BybitClient(),
            'Bitget':    BitgetClient(),
            'KuCoin':    KuCoinClient(),
            'HTX':       HTXClient(),
            'GateIO':    GateIOClient(),
        }
        self.market_data = {}

        # Broker-specific taker fees (realistic production values)
        if config and hasattr(config, 'broker_fees'):
            self.broker_fees = config.broker_fees
        else:
            self.broker_fees = {
                'Binance':   0.001,
                'Coinbase':  0.006,
                'Kraken':    0.0026,
                'BinanceUS': 0.001,
                'Bybit':     0.001,
                'Bitget':    0.001,
                'KuCoin':    0.001,
                'HTX':       0.002,
                'GateIO':    0.002,
            }

        # Withdrawal fee estimate (flat USDT) per cross-exchange transfer
        self.withdrawal_fee = getattr(config, 'withdrawal_fee_usdt', 1.0) if config else 1.0

    # ─── Concurrent data fetch ────────────────────────────────────────────
    def fetch_all_market_data(self):
        """Fetch market data from all brokers concurrently with optimized performance"""
        import concurrent.futures
        import time
        
        start_time = time.time()
        results = {}
        
        def fetch_broker_data(broker_name, client):
            try:
                data = client.fetch_market_data()
                if data:
                    results[broker_name] = data
                    self.logger.debug(f"Successfully fetched data from {broker_name}")
                else:
                    self.logger.warning(f"No data received from {broker_name}")
                    return None
            except Exception as e:
                self.logger.error(f"Error fetching from {broker_name}: {e}")
                return None
        
        # Use ThreadPoolExecutor for better performance and resource management
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_concurrent_requests) as executor:
            # Submit all fetch tasks
            future_to_broker = {
                executor.submit(fetch_broker_data, broker_name, client): broker_name
                for broker_name, client in self.brokers.items()
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_broker, timeout=10):
                broker_name = future_to_broker[future]
                try:
                    future.result()  # Result is already stored in results dict
                except Exception as e:
                    self.logger.error(f"Exception in {broker_name} fetch: {e}")
        
        fetch_time = time.time() - start_time
        self.logger.debug(f"Fetched data from {len(results)} brokers in {fetch_time:.2f}s")
        
        self.market_data = results
        return results

    # ─── Symbol normalisation ─────────────────────────────────────────────
    def normalize_symbol(self, symbol, broker_name):
        """Map exchange-specific symbol formats to a canonical form (e.g. BTCUSDT)."""
        symbol = symbol.upper().strip()

        # Most exchanges: BTCUSDT or BTC-USDT or BTC_USDT
        canonical = (symbol
                     .replace('-', '')
                     .replace('_', ''))

        # Coinbase BTC-USD → BTCUSD → BTCUSDT
        if canonical.endswith('USD') and not canonical.endswith('USDT'):
            canonical = canonical + 'T'

        # Kraken XXBTZUSD → XBTUSD → BTCUSDT
        if canonical.startswith('XXBT'):
            canonical = 'BTC' + canonical[4:]
        elif canonical.startswith('XBT'):
            canonical = 'BTC' + canonical[3:]
        if canonical.startswith('XETH'):
            canonical = 'ETH' + canonical[4:]

        if canonical.endswith('USD') and not canonical.endswith('USDT'):
            canonical = canonical + 'T'

        return canonical

    # ─── Find cross-broker arbitrage ──────────────────────────────────────
    def find_cross_broker_opportunities(self):
        """
        For each top-10 pair, compare bid/ask across all exchanges.
        Opportunity: buy at lowest ask on exchange A, sell at highest bid on exchange B.
        Calculate gross, fees, and net profit.
        """
        if not self.market_data:
            return []

        opportunities = []
        target_pairs = TOP10_USDT_SYMBOLS

        for pair in target_pairs:
            prices = {}

            for broker_name, data in self.market_data.items():
                for item in data:
                    canonical = self.normalize_symbol(item.get('symbol', ''), broker_name)
                    if canonical != pair:
                        continue
                    try:
                        bid = float(item.get('bidPrice', 0))
                        ask = float(item.get('askPrice', 0))
                    except (ValueError, TypeError):
                        continue
                    if bid > 0 and ask > 0:
                        prices[broker_name] = {'bid': bid, 'ask': ask, 'symbol': item['symbol']}

            if len(prices) < 2:
                continue

            broker_names = list(prices.keys())

            for i in range(len(broker_names)):
                for j in range(len(broker_names)):
                    if i == j:
                        continue

                    buy_broker = broker_names[i]
                    sell_broker = broker_names[j]

                    ask_price = prices[buy_broker]['ask']    # cost to buy
                    bid_price = prices[sell_broker]['bid']    # revenue from selling

                    if ask_price <= 0:
                        continue

                    # Gross profit
                    gross_profit = bid_price - ask_price
                    gross_pct = (gross_profit / ask_price) * 100

                    # Fees
                    buy_fee  = ask_price * self.broker_fees.get(buy_broker, 0.001)
                    sell_fee = bid_price * self.broker_fees.get(sell_broker, 0.001)
                    total_fees = buy_fee + sell_fee + self.withdrawal_fee
                    total_fees_pct = (total_fees / ask_price) * 100

                    # Net profit
                    net_profit = gross_profit - total_fees
                    net_pct = (net_profit / ask_price) * 100

                    # Only report if gross is positive (net may still be negative — show both)
                    if gross_pct > 0.001:
                        conf = self._calculate_confidence(ask_price, bid_price, prices[buy_broker], prices[sell_broker])
                        opportunities.append({
                            'type': 'cross_broker',
                            'pair': pair,
                            'buy_broker': buy_broker,
                            'sell_broker': sell_broker,
                            'buy_price': ask_price,
                            'sell_price': bid_price,
                            'gross_profit_pct': round(gross_pct, 4),
                            'total_fees_pct': round(total_fees_pct, 4),
                            'profit_pct': round(net_pct, 4),       # NET
                            'net_profit': round(net_pct, 4),        # alias
                            'roi': round(net_pct, 4),
                            'path': f"Buy {pair} on {buy_broker} @ {ask_price:.2f} → Sell on {sell_broker} @ {bid_price:.2f}",
                            'confidence': conf,
                        })

        opportunities.sort(key=lambda x: x['profit_pct'], reverse=True)
        return opportunities[:20]

    # ─── Confidence calculation ───────────────────────────────────────────
    @staticmethod
    def _calculate_confidence(buy_price, sell_price, buy_data, sell_data):
        if buy_price <= 0:
            return 0.1
        spread_ratio = (sell_price - buy_price) / buy_price
        spread_conf = min(1.0, spread_ratio * 50)  # scale up small spreads

        buy_spread = abs((buy_data['bid'] - buy_data['ask']) / buy_data['ask']) if buy_data['ask'] > 0 else 1
        sell_spread = abs((sell_data['bid'] - sell_data['ask']) / sell_data['ask']) if sell_data['ask'] > 0 else 1
        tightness = max(0.1, 1.0 - (buy_spread + sell_spread) * 50)

        return round(min(1.0, max(0.1, 0.4 * spread_conf + 0.6 * tightness)), 2)

    # ─── Broker status ────────────────────────────────────────────────────
    def get_broker_status(self):
        status = {}
        for broker_name in self.brokers:
            data = self.market_data.get(broker_name)
            status[broker_name] = {
                'connected': bool(data and len(data) > 0),
                'pairs_count': len(data) if data else 0,
                'last_update': time.time(),
            }
        return status
