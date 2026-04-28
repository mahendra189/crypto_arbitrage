class Trade:
    def __init__(self, path, raw_profit, net_profit):
        self.path = path
        self.raw_profit = raw_profit
        self.net_profit = net_profit

    def __str__(self):
        return f"Path: {' → '.join(self.path)}, Raw Profit: {self.raw_profit:.2%}, Net Profit: {self.net_profit:.2%}"