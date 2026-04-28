from data.cross_broker_aggregator import CrossBrokerAggregator
from utils.logger import Logger
from config import Config

# Test the exact same logic as main system
config = Config()
logger = Logger()
agg = CrossBrokerAggregator(logger)

# Fetch data
cross_broker_data = agg.fetch_all_market_data()
print(f"Market data keys: {list(cross_broker_data.keys())}")

# Find opportunities
cross_broker_opportunities = agg.find_cross_broker_opportunities()
print(f"Cross-broker opportunities found: {len(cross_broker_opportunities)}")

# Check if opportunities meet threshold
for i, opp in enumerate(cross_broker_opportunities[:5]):
    print(f"{i+1}. {opp['path']} | Profit: {opp['profit_pct']:.3f}% | Threshold: {config.cross_broker_min_profit}")
    meets_threshold = opp['profit_pct'] > (config.cross_broker_min_profit * 100)
    print(f"   Meets threshold: {meets_threshold}")
