from data.cross_broker_aggregator import CrossBrokerAggregator
from utils.logger import Logger

agg = CrossBrokerAggregator(Logger())
data = agg.fetch_all_market_data()

# Check symbol normalization for BTCUSDT
target_pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']

for pair in target_pairs:
    print(f"\n=== Looking for {pair} ===")
    prices = {}
    
    for broker_name, broker_data in data.items():
        if not broker_data:
            continue
            
        for item in broker_data:
            original_symbol = item.get('symbol', '')
            normalized = agg.normalize_symbol(original_symbol, broker_name)
            
            if normalized == pair or normalized == pair.replace('USDT', 'USD') or normalized == pair.replace('USDT', '-USD'):
                try:
                    bid_price = float(item.get('bidPrice', 0))
                    ask_price = float(item.get('askPrice', 0))
                    
                    if bid_price > 0 and ask_price > 0:
                        prices[broker_name] = {
                            'bid': bid_price,
                            'ask': ask_price,
                            'original_symbol': original_symbol,
                            'normalized': normalized
                        }
                        print(f"  {broker_name}: {original_symbol} -> {normalized} | Bid: {bid_price} Ask: {ask_price}")
                except (ValueError, TypeError):
                    continue
    
    print(f"  Found {pair} on {len(prices)} exchanges: {list(prices.keys())}")
    
    # Check for arbitrage
    if len(prices) >= 2:
        broker_names = list(prices.keys())
        for i in range(len(broker_names)):
            for j in range(i + 1, len(broker_names)):
                b1 = broker_names[i]
                b2 = broker_names[j]
                
                ask1 = prices[b1]['ask']
                bid2 = prices[b2]['bid']
                
                if ask1 > 0 and bid2 > 0:
                    profit = ((bid2 - ask1) / ask1) * 100
                    if profit > 0.001:
                        print(f"    ARBITRAGE: Buy on {b1} @ {ask1}, Sell on {b2} @ {bid2} = {profit:.3f}%")
