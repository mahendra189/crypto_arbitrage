from data.cross_broker_aggregator import CrossBrokerAggregator
from utils.logger import Logger

# Test without fees to see if opportunities exist
agg = CrossBrokerAggregator(Logger())
data = agg.fetch_all_market_data()

# Temporarily set all fees to 0
agg.broker_fees = {broker: 0 for broker in agg.broker_fees}

opportunities = agg.find_cross_broker_opportunities()
print(f'Cross-broker opportunities (no fees): {len(opportunities)}')

for i, opp in enumerate(opportunities[:5]):
    print(f'{i+1}. {opp["path"]} | Profit: {opp["profit_pct"]:.3f}% | Fees: {opp.get("total_fees_pct", 0):.3f}%')

# Now test with real fees
agg.broker_fees = {
    'Binance': 0.001, 'Coinbase': 0.005, 'Kraken': 0.002, 'BinanceUS': 0.001,
    'Bybit': 0.001, 'Bitget': 0.001, 'KuCoin': 0.001, 'HTX': 0.002, 'GateIO': 0.002
}

opportunities_with_fees = agg.find_cross_broker_opportunities()
print(f'\nCross-broker opportunities (with fees): {len(opportunities_with_fees)}')

for i, opp in enumerate(opportunities_with_fees[:5]):
    print(f'{i+1}. {opp["path"]} | Profit: {opp["profit_pct"]:.3f}% | Fees: {opp.get("total_fees_pct", 0):.3f}%')
