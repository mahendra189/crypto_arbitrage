"""
Demo Trading System for Crypto Arbitrage
Simulates real trading with paper money and realistic market conditions
"""

import time
import random
from datetime import datetime
from typing import Dict, List, Optional
from utils.logger import Logger

class DemoTrader:
    def __init__(self, config, logger: Logger):
        self.config = config
        self.logger = logger
        self.balance = config.demo_initial_balance
        self.initial_balance = config.demo_initial_balance
        self.positions = {}
        self.trade_history = []
        self.pending_orders = []
        self.total_pnl = 0.0
        
    def calculate_position_size(self, opportunity: Dict) -> float:
        """Calculate optimal position size based on risk management"""
        risk_amount = self.balance * self.config.risk_per_trade
        max_size = min(risk_amount, self.config.max_position_size)
        
        # Adjust based on opportunity confidence
        confidence = opportunity.get('confidence', 0.5)
        adjusted_size = max_size * confidence
        
        return min(adjusted_size, self.balance * 0.1)  # Max 10% of balance per trade
    
    def simulate_slippage(self, price: float, volume: float) -> float:
        """Simulate realistic slippage based on market conditions"""
        if not self.config.dynamic_slippage:
            return price * (1 + self.config.slippage)
        
        # Dynamic slippage based on volume
        volume_impact = min(volume / 10000, 0.002)  # Max 0.2% volume impact
        base_slippage = self.config.slippage
        random_factor = random.uniform(-0.0001, 0.0003)  # Random market noise
        
        total_slippage = base_slippage + volume_impact + random_factor
        return price * (1 + total_slippage)
    
    def simulate_latency(self) -> float:
        """Simulate network and exchange latency"""
        if not self.config.latency_simulation:
            return 0.1
        
        base_latency = 0.05  # 50ms base
        exchange_delay = random.uniform(0.02, 0.15)  # Exchange processing
        network_jitter = random.uniform(0, 0.05)  # Network jitter
        
        return base_latency + exchange_delay + network_jitter
    
    def check_liquidity(self, symbol: str, size: float) -> bool:
        """Check if there's enough liquidity for the trade"""
        if not self.config.liquidity_check:
            return True
        
        # Simulate liquidity check (in real implementation, this would check order book depth)
        max_liquidity = 50000.0  # $50k max liquidity per symbol
        return size <= max_liquidity
    
    def execute_trade(self, opportunity: Dict) -> Dict:
        """Execute a demo trade with realistic simulation"""
        start_time = time.time()
        
        # Calculate position size
        position_size = self.calculate_position_size(opportunity)
        
        if position_size <= 0:
            return {"success": False, "error": "Insufficient balance or risk limits"}
        
        # Check liquidity
        symbol = opportunity.get('pair', 'BTCUSDT')
        if not self.check_liquidity(symbol, position_size):
            return {"success": False, "error": "Insufficient liquidity"}
        
        # Simulate latency
        latency = self.simulate_latency()
        time.sleep(latency)
        
        # Get trade details
        trade_type = opportunity.get('type', 'unknown')
        entry_price = opportunity.get('buy_price', 0)
        exit_price = opportunity.get('sell_price', 0)
        
        # Apply slippage
        entry_price = self.simulate_slippage(entry_price, position_size)
        exit_price = self.simulate_slippage(exit_price, position_size)
        
        # Calculate fees
        total_fees = position_size * self.config.fee * 2  # Entry and exit fees
        
        # Calculate P&L
        if trade_type in ['triangular', 'cross_broker']:
            gross_profit = position_size * ((exit_price - entry_price) / entry_price)
            net_profit = gross_profit - total_fees
        elif trade_type == 'funding_rate':
            funding_rate = opportunity.get('funding_rate', 0)
            gross_profit = position_size * abs(funding_rate)
            net_profit = gross_profit - total_fees
        else:
            net_profit = -total_fees
        
        # Update balance
        if net_profit > 0 or self.balance > position_size:
            self.balance += net_profit
            self.total_pnl += net_profit
        else:
            return {"success": False, "error": "Insufficient balance for this trade"}
        
        # Record trade
        trade = {
            "id": len(self.trade_history) + 1,
            "timestamp": datetime.now().isoformat(),
            "type": trade_type,
            "pair": symbol,
            "opportunity": opportunity.get('path', 'Unknown'),
            "position_size": position_size,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "fees": total_fees,
            "latency_ms": round(latency * 1000, 2),
            "execution_time": round(time.time() - start_time, 3),
            "balance_after": self.balance
        }
        
        self.trade_history.append(trade)
        
        # Log the trade
        self.logger.info(f"DEMO TRADE EXECUTED: {trade['opportunity']} | P&L: ${net_profit:.2f} | Balance: ${self.balance:.2f}")
        
        return {
            "success": True,
            "trade": trade,
            "message": f"Trade executed successfully. P&L: ${net_profit:.2f}"
        }
    
    def get_portfolio_status(self) -> Dict:
        """Get current portfolio status and performance"""
        total_trades = len(self.trade_history)
        winning_trades = len([t for t in self.trade_history if t['net_profit'] > 0])
        losing_trades = len([t for t in self.trade_history if t['net_profit'] < 0])
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        total_return = ((self.balance - self.initial_balance) / self.initial_balance) * 100
        
        return {
            "current_balance": self.balance,
            "initial_balance": self.initial_balance,
            "total_pnl": self.total_pnl,
            "total_return_pct": total_return,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate_pct": win_rate,
            "avg_trade_pnl": self.total_pnl / total_trades if total_trades > 0 else 0,
            "largest_win": max([t['net_profit'] for t in self.trade_history], default=0),
            "largest_loss": min([t['net_profit'] for t in self.trade_history], default=0)
        }
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Get recent trade history"""
        return self.trade_history[-limit:] if self.trade_history else []
    
    def reset_demo_account(self):
        """Reset demo account to initial state"""
        self.balance = self.initial_balance
        self.positions = {}
        self.trade_history = []
        self.pending_orders = []
        self.total_pnl = 0.0
        self.logger.info("DEMO ACCOUNT RESET: Balance reset to $10,000")
