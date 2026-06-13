"""
Benchmark: HPTrendRider vs HPTrend vs buy-and-hold on 5y window (2020-2024).

Goal: see if "HP filter + no take-profit" closes the 2pp gap to 0050.
"""
import sys
sys.path.insert(0, '.')

import os
os.environ.setdefault('MPLBACKEND', 'Agg')

import pandas as pd
import backtrader as bt
from datetime import datetime
from dateutil.relativedelta import relativedelta

from utility.debug import DebugSetting
os.makedirs('/tmp/claude-1000/tradebot-log', exist_ok=True)
DebugSetting.setDbgPath('/tmp/claude-1000/tradebot-log')

from backtest.datafeed import ExtPandasDataFeed
from strategy.ai.hptrend import HPTrendStrategy
from strategy.ai.hptrendrider import HPTrendRiderStrategy

CACHE_DIR = '/home/shaowu/.config/investment/data/findmind/datas/20250620'

# t50 sample (the standard 50)
t50 = ['2330', '2454', '2317', '2308', '2382', '2891', '2303', '2881', '3711', '6505',
       '2412', '2882', '2886', '2327', '3034', '2884', '6669', '2885', '5880', '3045',
       '2892', '2002', '3037', '2603', '3231', '1101', '1216', '1301', '1303', '1326',
       '1402', '2105', '2207', '2301', '2357', '2395', '2474', '2609', '2615', '2801',
       '2880', '2883', '2887', '2888', '2890', '2912', '3008', '3017', '4904', '4938']

# Use a representative sub-sample of 8 (matches what we know)
sample = t50  # Run all 50 for the actual benchmark


def load_data(symbol):
    path = os.path.join(CACHE_DIR, f'{symbol}.csv')
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    return df


# 5y window
to_date = datetime(2024, 12, 31)
from_date = to_date - relativedelta(years=5)


def run_backtest(strategy_cls, df, name):
    cerebro = bt.Cerebro()
    cerebro.broker.set_cash(1_000_000_000)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.broker.set_slippage_perc(perc=0.001)

    data = ExtPandasDataFeed(dataname=df, fromdate=from_date, todate=to_date)
    cerebro.adddata(data, name=name)
    cerebro.addstrategy(strategy_cls)
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='ar')
    results = cerebro.run()
    strat = results[0]
    ar = strat.analyzers.ar.get_analysis()
    # 5y avg
    rets = list(ar.values())
    avg = sum(rets) / len(rets) * 100 if rets else 0
    return ar, avg


# Per-stock benchmark
print(f"Benchmark: HPTrendRider vs HPTrend vs buy-and-hold")
print(f"Window: {from_date.date()} -> {to_date.date()}")
print(f"Sample size: {len(sample)} stocks")
print()

results = {'hptrend': [], 'hptrendrider': [], 'buyhold': []}

for symbol in sample:
    df = load_data(symbol)
    if df is None or len(df) < 200:
        print(f"  {symbol}: skip")
        continue

    # Filter to 5y window
    df5y = df[(df.index >= from_date) & (df.index <= to_date)]
    if len(df5y) < 200:
        print(f"  {symbol}: skip (insufficient 5y data)")
        continue

    # Run HPTrend
    hp_ar, hp_avg = run_backtest(HPTrendStrategy, df, symbol)
    # Run HPTrendRider
    hpr_ar, hpr_avg = run_backtest(HPTrendRiderStrategy, df, symbol)

    # Buy and hold 5y
    bh_start = df5y['Close'].iloc[0]
    bh_end = df5y['Close'].iloc[-1]
    bh_total = (bh_end / bh_start - 1) * 100
    bh_avg = bh_total / 5  # very rough 5y avg

    results['hptrend'].append(hp_avg)
    results['hptrendrider'].append(hpr_avg)
    results['buyhold'].append(bh_avg)

    # Per-year comparison
    hp_yrs = {int(k): v*100 for k, v in hp_ar.items()}
    hpr_yrs = {int(k): v*100 for k, v in hpr_ar.items()}
    yr_str = '  '.join(f"{y}:HP{hp_yrs.get(y, 0):+.1f}/HPR{hpr_yrs.get(y, 0):+.1f}" for y in sorted(set(hp_yrs) | set(hpr_yrs)))

    print(f"  {symbol}: HP 5y={hp_avg:+.2f}%  HPR 5y={hpr_avg:+.2f}%  B&H 5y={bh_total:+.1f}%")
    print(f"     {yr_str}")

print()
print("=" * 60)
print("SUMMARY (5y avg per stock, mean across t50):")
n = len(results['hptrend'])
if n > 0:
    print(f"  HPTrend:        {sum(results['hptrend'])/n:+.2f}%")
    print(f"  HPTrendRider:   {sum(results['hptrendrider'])/n:+.2f}%")
    print(f"  Buy & Hold:     {sum(results['buyhold'])/n:+.2f}%")
    print(f"  0050 ETF ref:   +15.52%")
