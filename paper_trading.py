"""
Simple paper-trading account for simulated arbitrage execution.
"""

import threading
import time


class PaperTrader:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.lock = threading.RLock()
        self.starting_balance_usdt = round(config.paper_trade_starting_balance_usdt, 2)
        self._reset_locked()

    def _reset_locked(self):
        self.balance_usdt = self.starting_balance_usdt
        self.realized_pnl_usdt = 0.0
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        self.last_trade_at = None
        self.trade_history = []

    def reset(self):
        with self.lock:
            self._reset_locked()
            self.logger.info("Paper account reset to starting balance.")

    def execute(self, opportunity, allocation_usdt=None):
        try:
            allocation = float(
                allocation_usdt
                if allocation_usdt is not None
                else opportunity.get("allocation_usdt", self.config.default_trade_allocation_usdt)
            )
        except (TypeError, ValueError):
            return {"ok": False, "error": "Invalid allocation."}

        if allocation <= 0:
            return {"ok": False, "error": "Allocation must be greater than zero."}

        return_pct = float(opportunity.get("paper_return_pct", 0.0))
        max_notional = float(opportunity.get("max_notional_usdt", 0.0) or 0.0)

        if return_pct <= 0:
            return {"ok": False, "error": "This opportunity is not paper-trade ready."}

        with self.lock:
            if allocation > self.balance_usdt:
                return {"ok": False, "error": "Not enough paper balance for this trade."}

            if max_notional > 0 and allocation > max_notional:
                return {
                    "ok": False,
                    "error": f"Allocation exceeds estimated executable size (${max_notional:.2f}).",
                }

            realized_pnl = round(allocation * (return_pct / 100.0), 2)
            now = time.time()
            trade = {
                "trade_id": f"paper-{int(now * 1000)}",
                "executed_at": now,
                "opportunity_id": opportunity.get("opportunity_id"),
                "type": opportunity.get("type"),
                "path": opportunity.get("path"),
                "allocation_usdt": round(allocation, 2),
                "estimated_return_pct": round(return_pct, 4),
                "estimated_pnl_usdt": realized_pnl,
                "confidence": opportunity.get("confidence", 0.0),
                "mode": "paper",
                "status": "filled",
            }

            self.balance_usdt = round(self.balance_usdt + realized_pnl, 2)
            self.realized_pnl_usdt = round(self.realized_pnl_usdt + realized_pnl, 2)
            self.trade_count += 1
            if realized_pnl >= 0:
                self.win_count += 1
            else:
                self.loss_count += 1

            self.last_trade_at = now
            self.trade_history.insert(0, trade)
            self.trade_history = self.trade_history[:12]

            self.logger.signal(
                f"Paper trade filled: {trade['path']} | "
                f"alloc=${trade['allocation_usdt']:.2f} | pnl=${trade['estimated_pnl_usdt']:.2f}"
            )

            return {"ok": True, "trade": trade, "account": self._build_state()}

    def _build_state(self):
        win_rate = (self.win_count / self.trade_count * 100.0) if self.trade_count else 0.0
        return {
            "mode": "paper",
            "starting_balance_usdt": round(self.starting_balance_usdt, 2),
            "balance_usdt": round(self.balance_usdt, 2),
            "equity_usdt": round(self.balance_usdt, 2),
            "realized_pnl_usdt": round(self.realized_pnl_usdt, 2),
            "trade_count": self.trade_count,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "win_rate_pct": round(win_rate, 2),
            "last_trade_at": self.last_trade_at,
            "recent_trades": list(self.trade_history),
        }

    def get_state(self):
        with self.lock:
            return self._build_state()
