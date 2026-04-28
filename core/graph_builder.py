import math
from collections import defaultdict


class GraphBuilder:
    def __init__(self, currencies, fee, slippage=0.0):
        self.currencies = set(currencies)
        self.fee = fee
        self.slippage = slippage
        self.per_hop_cost = fee + slippage

    def split_symbol(self, symbol):
        for quote in ["USDT", "BTC", "ETH", "BNB"]:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return base, quote
        return None, None

    def build_graph(self, market_data):
        graph = defaultdict(dict)

        for symbol, prices in market_data.items():
            bid_price = prices["bid"]
            ask_price = prices["ask"]

            if bid_price <= 0 or ask_price <= 0:
                continue

            base, quote = self.split_symbol(symbol)

            if not base or not quote:
                continue

            # 🔥 IMPORTANT: allow full graph (no strict filtering)
            graph[base][quote] = bid_price
            graph[quote][base] = 1.0 / ask_price

        return dict(graph)

    def find_all_cycles(self, graph, min_len=3, max_len=4):
        all_cycles = []
        nodes = list(graph.keys())

        for start in nodes:
            stack = [(start, [start], {start})]

            while stack:
                current, path, visited = stack.pop()

                for neighbour in graph.get(current, {}):
                    if neighbour == start and len(path) >= min_len:
                        all_cycles.append(list(path))
                        continue

                    if neighbour not in visited and len(path) < max_len:
                        stack.append((neighbour, path + [neighbour], visited | {neighbour}))

        return all_cycles

    def deduplicate_cycles(self, cycles):
        unique = set()
        result = []

        for cycle in cycles:
            normalized = tuple(sorted(cycle))
            if normalized not in unique:
                unique.add(normalized)
                result.append(cycle)

        return result

    def calculate_cycle_profit(self, graph, cycle):
        num_hops = len(cycle)
        multiplier = 1.0

        for i in range(num_hops):
            src = cycle[i]
            dst = cycle[(i + 1) % num_hops]

            rate = graph.get(src, {}).get(dst)
            if not rate or rate <= 0:
                return None, None, num_hops

            multiplier *= rate

        gross = (multiplier - 1) * 100
        net_multiplier = multiplier * ((1 - self.per_hop_cost) ** num_hops)
        net = (net_multiplier - 1) * 100

        return gross, net, num_hops

    def find_arbitrage_cycles(self, market_data, min_len=3, max_len=4, top_n=10):
        graph = self.build_graph(market_data)

        raw_cycles = self.find_all_cycles(graph, min_len, max_len)
        unique_cycles = self.deduplicate_cycles(raw_cycles)

        results = []

        for cycle in unique_cycles:
            gross, net, hops = self.calculate_cycle_profit(graph, cycle)

            if gross is None:
                continue

            results.append({
                "type": "triangular",
                "path": " → ".join(cycle) + " → " + cycle[0],
                "raw_profit": round(gross, 4),
                "net_profit": round(net, 4),
                "hops": hops
            })

        results.sort(key=lambda x: x["raw_profit"], reverse=True)
        return results[:top_n]