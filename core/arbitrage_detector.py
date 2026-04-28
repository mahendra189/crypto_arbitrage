import time
import math
from collections import deque

from data.broker_clients import BinanceClient
from data.cross_broker_aggregator import CrossBrokerAggregator
from core.graph_builder import GraphBuilder


class ArbitrageDetector:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.client = BinanceClient()
        self.cross_broker_aggregator = CrossBrokerAggregator(logger, config)
        self.graph_builder = GraphBuilder(
            config.currencies,
            config.fee,
            config.slippage
        )

        self.price_history = {}
        for pair_a, pair_b in config.stat_arb_pairs:
            self.price_history.setdefault(pair_a, deque(maxlen=config.stat_arb_window))
            self.price_history.setdefault(pair_b, deque(maxlen=config.stat_arb_window))

    def scan(self):
        self.logger.info("═══ Scanning all arbitrage strategies ═══")

        data = self.client.fetch_market_data()

        if not data or not isinstance(data, dict):
            self.logger.error("Invalid market data format")
            return

        print("DATA SAMPLE:", list(data.keys())[:5])

        graph = self.graph_builder.build_graph(data)
        print("GRAPH NODES:", len(graph))

        if len(graph) == 0:
            print("GRAPH EMPTY — CHECK DATA")
            return

        self._update_price_history(data)

        all_opportunities = []

        short_cycles = self.graph_builder.find_arbitrage_cycles(
            data,
            min_len=3,
            max_len=4,
            top_n=20
        )

        print("SHORT CYCLES:", len(short_cycles))

        for c in short_cycles:
            c["type"] = "real_arbitrage"

        long_cycles = self.graph_builder.find_arbitrage_cycles(
            data,
            min_len=5,
            max_len=6,
            top_n=10
        )

        print("LONG CYCLES:", len(long_cycles))

        for c in long_cycles:
            c["type"] = "extended_path"

        all_opportunities.extend(short_cycles)
        all_opportunities.extend(long_cycles)

        all_opportunities.sort(
            key=lambda x: x.get('net_profit', 0),
            reverse=True
        )

        self._display_opportunities(all_opportunities[:self.config.max_opportunities_display])

    def _update_price_history(self, data):
        for sym, prices in data.items():
            try:
                mid = (prices["bid"] + prices["ask"]) / 2
                if sym in self.price_history:
                    self.price_history[sym].append(mid)
            except:
                continue

    def _display_opportunities(self, opportunities):
        if not opportunities:
            print("No arbitrage opportunities found.")
            return

        print("\nTOP OPPORTUNITIES:\n")

        for i, opp in enumerate(opportunities):
            print(f"{i+1}. [{opp['type']}] {opp['path']}")
            print(f"   Raw: {opp.get('raw_profit',0):+.4f}% | Net: {opp.get('net_profit',0):+.4f}%\n")