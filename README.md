# Cryptocurrency Arbitrage Engine

This project comprehensively detects various arbitrage opportunities in cryptocurrency markets using advanced algorithms.

## Core Features & Concepts
1. **Triangular Arbitrage**: Uses Graph/DSA Algorithms (Bellman-Ford and DFS) to find negative weight cycles representing profitable paths within a single exchange.
2. **Cross-Exchange Arbitrage**: Continuously monitors multiple broker APIs to find simultaneous Buy/Sell execution opportunities across markets.
3. **Spatial Arbitrage**: Accounts for actual transfer fees (withdrawal costs) and buffers to find profitable paths involving physically transferring assets between brokers.

## Supported Broker APIs
- Binance, BinanceUS
- Coinbase
- Kraken
- Bybit, Bitget
- KuCoin, HTX, GateIO

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python main.py
   ```

## Example Output
```
Cycle Found:
USDT → BTC → ETH → USDT
Raw Profit: 0.72%
Net Profit: 0.41%
-----------------
```