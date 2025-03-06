import backtrader as bt
from alpaca_backtrader_api import AlpacaStore
import datetime

# 你的 Alpaca API 金鑰
ALPACA_API_KEY = "your_api_key"
ALPACA_SECRET_KEY = "your_secret_key"
ALPACA_PAPER = False  # ⚠️ 設為 True 則是模擬交易，設為 False 則是真實交易！

# 創建交易策略
class RealTimeStrategy(bt.Strategy):
    def __init__(self):
        self.sma_fast = bt.indicators.SimpleMovingAverage(period=10)
        self.sma_slow = bt.indicators.SimpleMovingAverage(period=50)

    def next(self):
        if not self.position:  # 如果沒有持倉
            if self.sma_fast[0] > self.sma_slow[0]:  # 短均線上穿長均線
                self.buy(size=1)  # ⚠️ 這會向券商發送真實訂單
        else:
            if self.sma_fast[0] < self.sma_slow[0]:  # 短均線下穿長均線
                self.sell(size=1)  # ⚠️ 這會向券商發送真實賣出訂單

# 創建 Backtrader 的核心引擎
cerebro = bt.Cerebro()

# 連接 Alpaca Store
store = AlpacaStore(
    key_id=ALPACA_API_KEY,
    secret_key=ALPACA_SECRET_KEY,
    paper=ALPACA_PAPER
)

# 設置券商經紀人
cerebro.setbroker(store.getbroker())

# 設置實時數據源
data = store.getdata(
    dataname="AAPL",  # 交易標的
    historical=False,  # ⚠️ 這行很重要，表示 **實時交易**
    timeframe=bt.TimeFrame.Days,
    backfill_start=True,  # 確保有足夠的歷史數據來計算指標
    backfill=True
)

cerebro.adddata(data)
cerebro.addstrategy(RealTimeStrategy)

# 設定初始資金
cerebro.broker.set_cash(10000)

# 🚀 **開始實時交易**
cerebro.run()

