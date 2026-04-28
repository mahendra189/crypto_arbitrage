"""
Arbitrage engine with multi-strategy detection, live dashboard snapshots,
and paper-trading metadata.
"""

import json
import math
import os
import threading
import time
from collections import defaultdict, deque

from exchanges import BinanceClient, CrossBrokerAggregator

HEADER_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]


class GraphBuilder:
    def __init__(self, currencies, fee, slippage=0.0):
        self.currencies = set(currencies)
        self.per_hop_cost = fee + slippage

    def build_graph(self, market_data):
        graph = defaultdict(dict)
        for item in market_data:
            symbol = item.get("symbol", "")
            bid = self._safe_float(item.get("bidPrice"))
            ask = self._safe_float(item.get("askPrice"))
            if bid <= 0 or ask <= 0:
                continue

            base = quote = None
            for currency in self.currencies:
                if symbol.startswith(currency):
                    remainder = symbol[len(currency):]
                    if remainder in self.currencies:
                        base, quote = currency, remainder
                        break

            if not base:
                continue

            graph[base][quote] = bid
            graph[quote][base] = 1.0 / ask
        return dict(graph)

    def find_all_cycles(self, graph, min_len=2, max_len=9):
        cycles = []
        for start in list(graph.keys()):
            stack = [(start, [start], {start})]
            while stack:
                current, path, visited = stack.pop()
                for neighbor in graph.get(current, {}):
                    if neighbor == start and len(path) >= min_len:
                        cycles.append(list(path))
                    elif neighbor not in visited and len(path) < max_len:
                        stack.append((neighbor, path + [neighbor], visited | {neighbor}))
        return cycles

    def deduplicate_cycles(self, cycles):
        unique = {}
        for cycle in cycles:
            smallest = cycle.index(min(cycle))
            key = tuple(cycle[smallest:] + cycle[:smallest])
            unique.setdefault(key, cycle)
        return list(unique.values())

    def bellman_ford_arbitrage(self, graph):
        # Implementation of Bellman-Ford to find negative weight cycles
        # Edge weight is -log(rate). A negative cycle means product of rates > 1
        nodes = list(graph.keys())
        if not nodes:
            return []

        distances = {node: float('inf') for node in nodes}
        predecessor = {node: None for node in nodes}
        source = nodes[0]
        distances[source] = 0

        # Relax edges |V| - 1 times
        for _ in range(len(nodes) - 1):
            for u in nodes:
                if distances[u] == float('inf'):
                    continue
                for v, rate in graph.get(u, {}).items():
                    if rate <= 0:
                        continue
                    weight = -math.log(rate)
                    if distances[u] + weight < distances[v]:
                        distances[v] = distances[u] + weight
                        predecessor[v] = u

        # Check for negative weight cycle
        cycles = []
        for u in nodes:
            for v, rate in graph.get(u, {}).items():
                if rate <= 0:
                    continue
                weight = -math.log(rate)
                if distances[u] != float('inf') and distances[u] + weight < distances[v] - 1e-9:
                    # Negative cycle found, trace back
                    visited = set()
                    curr = v
                    while curr not in visited and curr is not None:
                        visited.add(curr)
                        curr = predecessor.get(curr)
                    
                    if curr is not None:
                        cycle = [curr]
                        node = predecessor[curr]
                        while node != curr and node is not None:
                            cycle.append(node)
                            node = predecessor[node]
                        cycle.reverse()
                        
                        # Only add if it's a valid cycle length
                        if len(cycle) >= 2:
                            cycles.append(cycle)

        return self.deduplicate_cycles(cycles)

    def calculate_cycle_profit(self, graph, cycle):
        multiplier = 1.0
        hops = len(cycle)
        for index in range(hops):
            rate = graph.get(cycle[index], {}).get(cycle[(index + 1) % hops])
            if not rate or rate <= 0:
                return None, None, hops
            multiplier *= rate

        gross_pct = (multiplier - 1.0) * 100.0
        net_pct = (multiplier * ((1 - self.per_hop_cost) ** hops) - 1.0) * 100.0
        return gross_pct, net_pct, hops

    def find_arbitrage_cycles(
        self,
        market_data,
        min_len=2,
        max_len=9,
        top_n=20,
        min_net_pct=0.0,
        min_confidence=0.0,
    ):
        graph = self.build_graph(market_data)
        
        # Combine Bellman-Ford (classic DSA) with DFS for complete path discovery
        raw_cycles = self.find_all_cycles(graph, min_len, max_len)
        bf_cycles = self.bellman_ford_arbitrage(graph)
        
        cycles = self.deduplicate_cycles(raw_cycles + bf_cycles)

        results = []
        for cycle in cycles:
            gross_pct, net_pct, hops = self.calculate_cycle_profit(graph, cycle)
            if gross_pct is None:
                continue

            hop_score = max(0.2, 1.0 - (hops - 2) * 0.15)
            profit_score = min(1.0, max(0.0, net_pct / 0.75))
            confidence = round(min(1.0, 0.45 * hop_score + 0.55 * profit_score), 2)
            if net_pct < min_net_pct or confidence < min_confidence:
                continue

            results.append({
                "type": "triangular",
                "path": " -> ".join(cycle) + " -> " + cycle[0],
                "hops": hops,
                "raw_profit": round(gross_pct, 4),
                "net_profit": round(net_pct, 4),
                "trade_profit_pct": round(net_pct, 4),
                "confidence": confidence,
            })

        results.sort(key=lambda item: (item["net_profit"], item["confidence"]), reverse=True)
        return results[:top_n]

    @staticmethod
    def _safe_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


class ArbitrageDetector:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.client = BinanceClient()
        self.cross_broker = CrossBrokerAggregator(logger, config)
        self.graph = GraphBuilder(config.currencies, config.fee, config.slippage)
        self.paper_state_provider = None

        self.price_history = {}
        for symbol_a, symbol_b in config.stat_arb_pairs:
            self.price_history.setdefault(symbol_a, deque(maxlen=config.stat_arb_window))
            self.price_history.setdefault(symbol_b, deque(maxlen=config.stat_arb_window))

        self.snapshot_lock = threading.RLock()
        self.scan_count = 0
        self.latest_opportunities = {}
        self.latest_snapshot = {
            "top_opportunities": [],
            "logs": [],
            "live_prices": {},
            "network_graph": {},
            "predictions": {},
            "broker_status": {},
            "paper_account": None,
            "timestamp": time.time(),
            "scan_started_at": None,
            "scan_finished_at": None,
            "scan_state": "booting",
            "errors": [],
            "scan_count": 0,
            "source_counts": {},
            "stale": True,
        }

    def set_paper_state_provider(self, provider):
        self.paper_state_provider = provider

    def get_dashboard_data(self, paper_state=None):
        with self.snapshot_lock:
            snapshot = dict(self.latest_snapshot)
            snapshot["top_opportunities"] = [dict(item) for item in self.latest_snapshot.get("top_opportunities", [])]
            snapshot["logs"] = list(self.latest_snapshot.get("logs", []))
            snapshot["live_prices"] = dict(self.latest_snapshot.get("live_prices", {}))
            snapshot["network_graph"] = dict(self.latest_snapshot.get("network_graph", {}))
            snapshot["predictions"] = dict(self.latest_snapshot.get("predictions", {}))
            snapshot["broker_status"] = dict(self.latest_snapshot.get("broker_status", {}))

        snapshot["paper_account"] = paper_state if paper_state is not None else self._paper_state()
        return snapshot

    def get_opportunity_by_id(self, opportunity_id):
        with self.snapshot_lock:
            opportunity = self.latest_opportunities.get(opportunity_id)
            return dict(opportunity) if opportunity else None

    def record_runtime_error(self, message):
        self.logger.error(f"Scanner runtime error: {message}")
        cached = self.get_dashboard_data()
        self._publish_snapshot(
            opportunities=cached.get("top_opportunities", []),
            live_prices=cached.get("live_prices", {}),
            network_graph=cached.get("network_graph", {}),
            broker_status=cached.get("broker_status", {}),
            scan_state="degraded",
            errors=[message],
            scan_started_at=time.time(),
            scan_finished_at=time.time(),
            source_counts=cached.get("source_counts", {}),
        )

    def scan(self):
        scan_started_at = time.time()
        self.logger.info("=== Scanning all arbitrage strategies ===")
        self.scan_count += 1
        scan_id = self.scan_count
        errors = []

        spot_data = self.client.fetch_market_data()
        if not spot_data:
            message = "Binance spot feed unavailable. Showing last known snapshot."
            self.logger.error(message)
            errors.append(message)
            cached = self.get_dashboard_data()
            self._publish_snapshot(
                opportunities=cached.get("top_opportunities", []),
                live_prices=cached.get("live_prices", {}),
                network_graph=cached.get("network_graph", {}),
                predictions=cached.get("predictions", {}),
                broker_status=self.cross_broker.get_broker_status(),
                scan_state="degraded",
                errors=errors,
                scan_started_at=scan_started_at,
                scan_finished_at=time.time(),
                source_counts=cached.get("source_counts", {}),
            )
            return

        cross_data = self.cross_broker.fetch_all_market_data()
        if not cross_data:
            errors.append("Cross-exchange feeds unavailable.")

        self._update_price_history(spot_data)
        live_prices = self._extract_live_prices(spot_data)

        triangular = self.graph.find_arbitrage_cycles(
            spot_data,
            min_len=self.config.min_cycle_length,
            max_len=self.config.max_cycle_length,
            top_n=25,
            min_net_pct=self.config.min_display_profit_pct,
            min_confidence=max(0.2, self.config.min_confidence - 0.05),
        )
        self.logger.info(f"  Multi-hop cycles (Triangular): {len(triangular)}")

        cross_and_spatial = self.cross_broker.find_cross_broker_opportunities() if self.config.enable_cross_broker else []
        
        cross_exchange = [c for c in cross_and_spatial if c['type'] == 'cross_broker']
        spatial = [c for c in cross_and_spatial if c['type'] == 'spatial_arbitrage']
        self.logger.info(f"  Cross-exchange (Simultaneous): {len(cross_exchange)}")
        self.logger.info(f"  Spatial Arbitrage (Transfer): {len(spatial)}")

        statistical = self._detect_stat_arb() if self.config.enable_stat_arb else []
        self.logger.info(f"  Statistical arb: {len(statistical)}")

        funding = self._detect_funding_arb() if self.config.enable_funding_arb else []
        self.logger.info(f"  Funding rate arb: {len(funding)}")

        source_counts = {
            "triangular": len(triangular),
            "cross_broker": len(cross_exchange),
            "spatial": len(spatial),
            "statistical": len(statistical),
            "funding_rate": len(funding),
        }

        all_opportunities = triangular + cross_exchange + spatial + statistical + funding
        ranked = self._rank_and_filter(all_opportunities, scan_id)

        self._display(ranked)

        scan_state = "live" if not errors else "degraded"
        network_graph = self.graph.build_graph(spot_data)
        predictions = self._calculate_predictions()
        self._publish_snapshot(
            opportunities=ranked,
            live_prices=live_prices,
            network_graph=network_graph,
            predictions=predictions,
            broker_status=self.cross_broker.get_broker_status(),
            scan_state=scan_state,
            errors=errors,
            scan_started_at=scan_started_at,
            scan_finished_at=time.time(),
            source_counts=source_counts,
        )

    def _update_price_history(self, market_data):
        price_map = {}
        for item in market_data:
            symbol = item.get("symbol", "")
            bid = self._safe_float(item.get("bidPrice"))
            ask = self._safe_float(item.get("askPrice"))
            if bid > 0 and ask > 0:
                price_map[symbol] = (bid + ask) / 2.0

        for symbol, history in self.price_history.items():
            if symbol in price_map:
                history.append(price_map[symbol])

    def _calculate_predictions(self):
        predictions = {}
        for symbol, history in self.price_history.items():
            if len(history) < 10:
                continue
                
            prices = list(history)
            current = prices[-1]
            old = prices[0]
            
            # Rate of change over the tracked window
            change_pct = ((current - old) / old) * 100 if old > 0 else 0
            
            # AI/Momentum Trend
            trend = "NEUTRAL"
            if change_pct > 0.05:
                trend = "BULLISH"
            elif change_pct < -0.05:
                trend = "BEARISH"
                
            # Volatility (approx std dev / mean)
            mean = sum(prices) / len(prices)
            variance = sum((p - mean) ** 2 for p in prices) / len(prices)
            volatility = (math.sqrt(variance) / mean) * 100 if mean > 0 else 0
            
            # Simple Linear Extrapolation for predicted next price
            predicted_next = current * (1 + (change_pct / 100))
            
            predictions[symbol] = {
                "trend": trend,
                "change_pct": round(change_pct, 4),
                "volatility": round(volatility, 4),
                "predicted_next": round(predicted_next, 4)
            }
        return predictions

    def _detect_stat_arb(self):
        opportunities = []
        min_net_pct = self.config.min_display_profit_pct

        for pair_a, pair_b in self.config.stat_arb_pairs:
            history_a = self.price_history.get(pair_a, deque())
            history_b = self.price_history.get(pair_b, deque())
            if len(history_a) < 10 or len(history_b) < 10:
                continue

            series_a = list(history_a)
            series_b = list(history_b)
            length = min(len(series_a), len(series_b))
            ratios = [series_a[index] / series_b[index] for index in range(length) if series_b[index] > 0]
            if len(ratios) < 10:
                continue

            mean_ratio = sum(ratios) / len(ratios)
            variance = sum((ratio - mean_ratio) ** 2 for ratio in ratios) / len(ratios)
            std_ratio = math.sqrt(variance) if variance > 0 else 0.0001
            current_ratio = ratios[-1]
            z_score = (current_ratio - mean_ratio) / std_ratio

            if abs(z_score) < self.config.stat_arb_z_threshold:
                continue

            expected_reversion_pct = abs(z_score) * std_ratio / mean_ratio * 100.0
            fees_pct = self.config.per_hop_cost * 2 * 100.0
            net_pct = expected_reversion_pct - fees_pct
            confidence = round(min(1.0, abs(z_score) / 4.0), 2)

            if net_pct < min_net_pct or confidence < self.config.min_confidence:
                continue

            direction = "LONG spread" if z_score < 0 else "SHORT spread"
            opportunities.append({
                "type": "statistical",
                "path": f"Stat: {pair_a}/{pair_b} - {direction}",
                "z_score": round(z_score, 3),
                "raw_profit": round(expected_reversion_pct, 4),
                "net_profit": round(net_pct, 4),
                "trade_profit_pct": round(net_pct, 4),
                "fee_pct": round(fees_pct, 4),
                "confidence": confidence,
                "data_points": len(ratios),
            })

        return opportunities

    def _detect_funding_arb(self):
        futures_data = self.client.fetch_futures_data()
        if not futures_data:
            return []

        opportunities = []
        for item in futures_data:
            funding_rate = self._safe_float(item.get("lastFundingRate"))
            mark_price = self._safe_float(item.get("markPrice"))
            index_price = self._safe_float(item.get("indexPrice"))
            if abs(funding_rate) < self.config.funding_rate_threshold or mark_price <= 0 or index_price <= 0:
                continue

            basis_pct = ((mark_price - index_price) / index_price) * 100.0
            if abs(basis_pct) > self.config.max_funding_basis_pct:
                continue

            gross_yield_8h = abs(funding_rate) * 100.0
            gross_annual_pct = gross_yield_8h * 3 * 365
            fee_pct = self.config.per_hop_cost * 4 * 100.0
            net_yield_8h = gross_yield_8h - (fee_pct / (3 * 365))
            net_annual_pct = net_yield_8h * 3 * 365

            basis_penalty = min(0.45, abs(basis_pct) / max(self.config.max_funding_basis_pct, 0.01) * 0.45)
            confidence = round(max(0.1, min(1.0, abs(funding_rate) / 0.002 - basis_penalty)), 2)
            if net_yield_8h < self.config.min_funding_period_profit_pct or confidence < self.config.min_confidence:
                continue

            direction = "Short Futures + Long Spot" if funding_rate > 0 else "Long Futures + Short Spot"
            opportunities.append({
                "type": "funding_rate",
                "path": f"Funding: {item['symbol']} - {direction}",
                "symbol": item["symbol"],
                "funding_rate": round(funding_rate * 100.0, 4),
                "basis_pct": round(basis_pct, 4),
                "raw_profit": round(gross_annual_pct, 2),
                "net_profit": round(net_annual_pct, 2),
                "trade_profit_pct": round(net_yield_8h, 4),
                "gross_yield_8h": round(gross_yield_8h, 4),
                "fee_pct": round(fee_pct, 4),
                "confidence": confidence,
            })

        opportunities.sort(key=lambda item: (item["trade_profit_pct"], item["confidence"]), reverse=True)
        return opportunities[:10]

    def _rank_and_filter(self, opportunities, scan_id):
        ranked = []
        allocation_usdt = self.config.default_trade_allocation_usdt

        for index, original in enumerate(opportunities, start=1):
            opportunity = dict(original)
            trade_return_pct = self._trade_return_pct(opportunity)
            confidence = max(0.0, min(1.0, float(opportunity.get("confidence", 0.0))))
            execution_buffer_pct = self._execution_buffer_pct(opportunity)
            realistic_return_pct = trade_return_pct - execution_buffer_pct
            estimated_pnl_usdt = allocation_usdt * (realistic_return_pct / 100.0)
            min_return_pct = self._minimum_return_pct(opportunity)

            if realistic_return_pct < min_return_pct or realistic_return_pct > getattr(self.config, "max_display_profit_pct", 1.0):
                continue
            if confidence < self.config.min_confidence:
                continue
            if estimated_pnl_usdt < self.config.min_estimated_pnl_usdt:
                continue

            opportunity["opportunity_id"] = f"scan-{scan_id}-{index}-{opportunity['type']}"
            opportunity["allocation_usdt"] = round(allocation_usdt, 2)
            opportunity["paper_return_pct"] = round(realistic_return_pct, 4)
            opportunity["paper_estimated_pnl_usdt"] = round(estimated_pnl_usdt, 2)
            opportunity["execution_buffer_pct"] = round(execution_buffer_pct, 4)
            opportunity["paper_fee_pct"] = round(self._fee_pct(opportunity), 4)
            opportunity["paper_trade_ready"] = True
            opportunity["score"] = round(estimated_pnl_usdt * max(confidence, 0.1), 4)

            ranked.append(opportunity)

        ranked.sort(
            key=lambda item: (
                item.get("score", 0.0),
                item.get("paper_return_pct", 0.0),
                item.get("confidence", 0.0),
            ),
            reverse=True,
        )
        return ranked[:self.config.max_opportunities_display]

    def _trade_return_pct(self, opportunity):
        return float(
            opportunity.get(
                "trade_profit_pct",
                opportunity.get("net_profit", opportunity.get("profit_pct", 0.0)),
            )
        )

    def _fee_pct(self, opportunity):
        if opportunity["type"] in ["cross_broker", "spatial_arbitrage"]:
            return float(opportunity.get("total_fees_pct", 0.0))
        if opportunity["type"] == "funding_rate":
            return float(opportunity.get("fee_pct", 0.0))
        if opportunity["type"] == "statistical":
            return float(opportunity.get("fee_pct", self.config.per_hop_cost * 2 * 100.0))

        hops = int(opportunity.get("hops", 3))
        return round(hops * self.config.per_hop_cost * 100.0, 4)

    def _execution_buffer_pct(self, opportunity):
        if opportunity["type"] in ["cross_broker", "spatial_arbitrage"]:
            return self.config.cross_execution_buffer_pct
        if opportunity["type"] == "statistical":
            return self.config.stat_execution_buffer_pct
        if opportunity["type"] == "funding_rate":
            return self.config.funding_execution_buffer_pct

        hops = int(opportunity.get("hops", 3))
        return self.config.execution_buffer_pct + max(0, hops - 3) * 0.01

    def _minimum_return_pct(self, opportunity):
        if opportunity["type"] in ["cross_broker", "spatial_arbitrage"]:
            return self.config.cross_broker_min_profit * 100.0
        if opportunity["type"] == "funding_rate":
            return self.config.min_funding_period_profit_pct
        return self.config.min_display_profit_pct

    def _extract_live_prices(self, market_data):
        prices = {}
        for item in market_data:
            symbol = item.get("symbol", "")
            if symbol in HEADER_SYMBOLS:
                prices[symbol] = item.get("askPrice", "0")
        return prices

    def _display(self, opportunities):
        if not opportunities:
            self.logger.info("No realistic opportunities found.")
            return

        print("\n" + "=" * 80)
        print("  TOP REALISTIC ARBITRAGE OPPORTUNITIES")
        print("=" * 80)

        counts = {}
        for index, opportunity in enumerate(opportunities, start=1):
            opportunity_type = opportunity["type"]
            counts[opportunity_type] = counts.get(opportunity_type, 0) + 1

            print(f"  {index}. [{opportunity_type.upper()}] {opportunity['path']}")
            print(
                f"     Net: {opportunity.get('paper_return_pct', 0):+.4f}%"
                f"  |  Est PnL: ${opportunity.get('paper_estimated_pnl_usdt', 0):+.2f}"
                f"  |  Conf: {opportunity.get('confidence', 0):.0%}"
            )
            print()

        print("-" * 80)
        summary = " | ".join(f"{key}: {value}" for key, value in counts.items())
        print(f"  Summary: {summary}")
        print("=" * 80)

        for signal in opportunities[:5]:
            self.logger.signal(
                f"Realistic signal: {signal['path']} | "
                f"{signal.get('paper_return_pct', 0):+.4f}% | "
                f"${signal.get('paper_estimated_pnl_usdt', 0):+.2f}"
            )

    def _publish_snapshot(
        self,
        opportunities,
        live_prices,
        network_graph,
        predictions,
        broker_status,
        scan_state,
        errors,
        scan_started_at,
        scan_finished_at,
        source_counts,
    ):
        payload = {
            "top_opportunities": [dict(item) for item in opportunities],
            "logs": list(self.logger.history),
            "live_prices": dict(live_prices),
            "network_graph": dict(network_graph),
            "predictions": dict(predictions),
            "broker_status": dict(broker_status),
            "paper_account": self._paper_state(),
            "timestamp": scan_finished_at,
            "scan_started_at": scan_started_at,
            "scan_finished_at": scan_finished_at,
            "scan_state": scan_state,
            "errors": list(errors),
            "scan_count": self.scan_count,
            "source_counts": dict(source_counts),
            "stale": scan_state != "live",
        }

        with self.snapshot_lock:
            self.latest_snapshot = payload
            self.latest_opportunities = {
                item["opportunity_id"]: dict(item)
                for item in opportunities
                if item.get("opportunity_id")
            }

        os.makedirs("web", exist_ok=True)
        with open("web/data.json", "w", encoding="utf-8") as handle:
            json.dump(payload, handle)

    def _paper_state(self):
        return self.paper_state_provider() if self.paper_state_provider else None

    @staticmethod
    def _safe_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
