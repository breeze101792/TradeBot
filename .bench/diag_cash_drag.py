"""
Diagnostic: measure in-position fraction for HPTrend on t50.

Reads CSVs directly from the findmind cache to bypass the API quota check.
"""
import sys
sys.path.insert(0, '.')

import os
os.environ.setdefault('MPLBACKEND', 'Agg')

import pandas as pd
import backtrader as bt
from datetime import datetime

from utility.debug import DebugSetting
import os
os.makedirs('/tmp/claude-1000/tradebot-log', exist_ok=True)
DebugSetting.setDbgPath('/tmp/claude-1000/tradebot-log')

from backtest.datafeed import ExtPandasDataFeed
from strategy.ai.hptrend import HPTrendStrategy

# Cache path
CACHE_DIR = '/home/shaowu/.config/investment/data/findmind/datas/20250620'

# Window: 5y from 2019-12-31 to 2024-12-31
to_date = datetime(2024, 12, 31)
from_date = datetime(2019, 12, 31)

sample = ['2330', '2454', '2308', '2882', '1101', '1326', '6505', '1301']


class PositionTracker(bt.Analyzer):
    """Track days in-position vs. in-cash."""
    def __init__(self):
        self.days_in = 0
        self.days_out = 0

    def next(self):
        pos_size = sum(self.strategy.getposition(d).size for d in self.strategy.datas)
        if pos_size > 0:
            self.days_in += 1
        else:
            self.days_out += 1


def load_data(symbol):
    path = os.path.join(CACHE_DIR, f'{symbol}.csv')
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    return df


print(f"Diagnostic: HPTrend cash-drag analysis on {sample}")
print(f"Window: {from_date.date()} -> {to_date.date()}")
print()

total_in = 0
total_out = 0
for symbol in sample:
    df = load_data(symbol)
    if df is None or len(df) < 200:
        print(f"  {symbol}: skip (insufficient data)")
        continue

    cerebro = bt.Cerebro()
    cerebro.broker.set_cash(1_000_000_000)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.broker.set_slippage_perc(perc=0.001)

    data = ExtPandasDataFeed(dataname=df, fromdate=from_date, todate=to_date)
    cerebro.adddata(data, name=symbol)
    cerebro.addstrategy(HPTrendStrategy)
    cerebro.addanalyzer(PositionTracker, _name='pos')

    results = cerebro.run()
    strat = results[0]
    pa = strat.analyzers.pos

    total = pa.days_in + pa.days_out
    pct = pa.days_in / total * 100 if total > 0 else 0
    print(f"  {symbol}: in-position {pa.days_in}/{total} = {pct:.1f}%, days_in_cash = {pa.days_out}")
    total_in += pa.days_in
    total_out += pa.days_out

print()
g = total_in + total_out
print(f"Aggregate: in-position {total_in}/{g} = {total_in/g*100:.1f}%, days_in_cash = {total_out}")
print(f"5y avg 0050 = 15.52% (held continuously)")
print(f"5y avg HPTrend = 13.48%")
