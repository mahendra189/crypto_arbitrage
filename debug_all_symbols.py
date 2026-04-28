from data.cross_broker_aggregator import CrossBrokerAggregator
from utils.logger import Logger

agg = CrossBrokerAggregator(Logger())
data = agg.fetch_all_market_data()

print("=== All available symbols by broker ===")
for broker_name, broker_data in data.items():
    if not broker_data:
        continue
    print(f"\n{broker_name} ({len(broker_data)} items):")
    for i, item in enumerate(broker_data[:5]):
        symbol = item.get('symbol', '')
        normalized = agg.normalize_symbol(symbol, broker_name)
        bid = item.get('bidPrice', '0')
        ask = item.get('askPrice', '0')
        print(f"  {i+1}. {symbol} -> {normalized} | Bid: {bid} Ask: {ask}")
