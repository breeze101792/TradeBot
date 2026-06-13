"""
Diagnostic: detailed 2024 trade analysis for HPTrend on t50.

Why is 2024 only +9.34% vs 0050's +28.00%? Check what HPTrend
does during 2024 on the strong names.
"""
import sys
sys.path.insert(0, '.')

import os
os.environ.setdefault('MPLBACKEND', 'Agg')

import pandas as pd
import backtrader as bt
from datetime import datetime

from utility.debug import DebugSetting
os.makedirs('/tmp/claude-1000/tradebot-log', exist_ok=True)
DebugSetting.setDbgPath('/tmp/claude-1000/tradebot-log')

from backtest.datafeed import ExtPandasDataFeed
from strategy.ai.hptrend import HPTrendStrategy

CACHE_DIR = '/home/shaowu/.config/investment/data/findmind/datas/20250620'

# 2024 only
to_date = datetime(2024, 12, 31)
from_date = datetime(2024, 1, 1)

# Focus on the strong 2024 names
strong_2024 = ['2330', '2454', '2308', '2882', '2317', '2382', '2891', '2303']


def load_data(symbol):
    path = os.path.join(CACHE_DIR, f'{symbol}.csv')
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    return df


class DetailedTracker(bt.Analyzer):
    """Track daily state, in/out events, and broker value."""
    def __init__(self):
        self.days_in = 0
        self.days_out = 0
        self.events = []  # (date, action, price, position_size)
        self.daily = []  # (date, broker_value, position_size)
        self.buy_count = 0
        self.sell_count = 0

    def next(self):
        pos_size = sum(self.strategy.getposition(d).size for d in self.strategy.datas)
        broker_value = self.strategy.broker.getvalue()
        date = self.strategy.datas[0].datetime.date(0)
        if pos_size > 0:
            self.days_in += 1
        else:
            self.days_out += 1
        self.daily.append((date, broker_value, pos_size))

    def notify_order(self, order):
        if order.status == order.Completed:
            date = bt.num2date(order.executed.dt).date()
            price = order.executed.price
            size = order.executed.size
            action = 'BUY' if order.isbuy() else 'SELL'
            self.events.append((date, action, price, size))
            if order.isbuy():
                self.buy_count += 1
            else:
                self.sell_count += 1


print(f"2024 detail: HPTrend behavior on {strong_2024}")
print()

for symbol in strong_2024:
    df = load_data(symbol)
    if df is None or len(df) < 50:
        print(f"  {symbol}: skip")
        continue

    # 2024 only but with enough history for HP filter (need ~120 bars)
    start = datetime(2023, 6, 1)  # ~6mo warmup for HP
    end = to_date

    cerebro = bt.Cerebro()
    cerebro.broker.set_cash(1_000_000_000)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.broker.set_slippage_perc(perc=0.001)

    data = ExtPandasDataFeed(dataname=df, fromdate=start, todate=end)
    cerebro.adddata(data, name=symbol)
    cerebro.addstrategy(HPTrendStrategy)
    cerebro.addanalyzer(DetailedTracker, _name='dt')

    results = cerebro.run()
    strat = results[0]
    dt = strat.analyzers.dt

    # Print summary
    total_2024_days = sum(1 for d, _, _ in dt.daily if d.year == 2024)
    in_2024 = sum(1 for d, _, sz in dt.daily if d.year == 2024 and sz > 0)
    out_2024 = total_2024_days - in_2024

    # Start/end value for 2024
    vals_2024 = [(d, v) for d, v, _ in dt.daily if d.year == 2024]
    if vals_2024:
        start_v = vals_2024[0][1]
        end_v = vals_2024[-1][1]
        ret = (end_v / start_v - 1) * 100
    else:
        ret = 0

    # Buy-and-hold return for 2024
    df2024 = df[(df.index >= '2024-01-01') & (df.index <= '2024-12-31')]
    if len(df2024) > 1:
        bh_ret = (df2024['Close'].iloc[-1] / df2024['Close'].iloc[0] - 1) * 100
    else:
        bh_ret = 0

    print(f"  {symbol}: HPTrend {ret:+.2f}% vs buy&hold {bh_ret:+.2f}% | in {in_2024}/{total_2024_days} = {in_2024/total_2024_days*100:.0f}% | buys={dt.buy_count}, sells={dt.sell_count}")

    # Show first 5 buy events in 2024
    events_2024 = [e for e in dt.events if e[0].year == 2024]
    if events_2024:
        print(f"    First 3 events: {[(str(e[0]), e[1], f'{e[2]:.1f}', e[3]) for e in events_2024[:3]]}")
        print(f"    Last 3 events:  {[(str(e[0]), e[1], f'{e[2]:.1f}', e[3]) for e in events_2024[-3:]]}")
