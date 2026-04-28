from data.cross_broker_aggregator import CrossBrokerAggregator
from utils.logger import Logger

agg = CrossBrokerAggregator(Logger())
data = agg.fetch_all_market_data()
opportunities = agg.find_cross_broker_opportunities()
print('Found', len(opportunities), 'cross-broker opportunities')
for i, opp in enumerate(opportunities[:5]):
    print(f'{i+1}. {opp["path"]} | Profit: {opp["profit_pct"]:.3f}%')
