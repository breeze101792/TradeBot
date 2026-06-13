"""
Final HPTrend tuning: combine best stop/TP with slope_lookback and hp_lambda.

Hypothesis: with no take-profit, the slope filter matters more for
entry timing. Test slope_lookback {2,3,4,5} and lambda {3e4, 1e5, 3e5}.
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
from strategy.ai.hptrend import HPFilter, HPTrendStrategy
import numpy as np

CACHE_DIR = '/home/shaowu/.config/investment/data/findmind/datas/20250620'

sample = ['2330', '2454', '2317', '2308', '2382', '2891', '2303', '2881', '3711', '6505',
       '2412', '2882', '2886', '2327', '3034', '2884', '6669', '2885', '5880', '3045',
       '2892', '2002', '3037', '2603', '3231', '1101', '1216', '1301', '1303', '1326',
       '1402', '2105', '2207', '2357', '2395', '2474', '2609', '2615', '2801',
       '2880', '2883', '2887', '2888', '2890', '2912', '3008', '3017', '4904', '4938']


def load_data(symbol):
    path = os.path.join(CACHE_DIR, f'{symbol}.csv')
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    return df


to_date = datetime(2024, 12, 31)
from_date = to_date - relativedelta(years=5)


class HPTrendV(HPTrendStrategy):
    """Same as HPTrend but with configurable stop/take-profit + HP params."""
    NAME = "HPTrendV"
    params = (
        ("hp_lookback", 90),
        ("hp_lambda", 1e5),
        ("slope_lookback", 3),
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.12),
        ("trailing_takeprofit_pct", 0.99),
        ("bb_period", 20), ("bb_stddev", 2),
        ("rsi_period", 14), ("rsi_entry", 30), ("rsi_exit", 70),
        ("macd_fast", 12), ("macd_slow", 26), ("macd_signal", 9),
        ("vol_period", 20),
        ("vwap_period", 20),
    )


# Test grid: stop, slope_lookback, hp_lambda
grid = []
for stop in [0.10, 0.12, 0.13, 0.15]:
    for slope in [2, 3, 4, 5]:
        for lam in [3e4, 1e5, 3e5]:
            grid.append((f"S{stop:.0%}-sl{slope}-lam{int(lam)}", stop, slope, lam))


def run_backtest(df, stop, slope, lam, name):
    cerebro = bt.Cerebro()
    cerebro.broker.set_cash(1_000_000_000)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.broker.set_slippage_perc(perc=0.001)
    data = ExtPandasDataFeed(dataname=df, fromdate=from_date, todate=to_date)
    cerebro.adddata(data, name=name)
    cerebro.addstrategy(HPTrendV,
                       trailing_stop_pct=stop,
                       slope_lookback=slope,
                       hp_lambda=lam)
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='ar')
    results = cerebro.run()
    ar = results[0].analyzers.ar.get_analysis()
    return ar


# 4×4×3 = 48 configs. Each runs 49 stocks. ~10 min total.
print(f"HPTrend final grid search: {len(grid)} configs x {len(sample)} stocks")
print(f"Window: {from_date.date()} -> {to_date.date()}")
print()

results = {g[0]: {} for g in grid}

# Pre-load all data
print("Loading data...")
datas = {}
for s in sample:
    df = load_data(s)
    if df is not None and len(df) >= 200:
        datas[s] = df
print(f"Loaded {len(datas)} stocks")
print()

import time
t0 = time.time()
for i, (gname, stop, slope, lam) in enumerate(grid):
    for symbol, df in datas.items():
        ar = run_backtest(df, stop, slope, lam, symbol)
        for year_str, ret in ar.items():
            y = int(year_str)
            if y not in results[gname]:
                results[gname][y] = []
            results[gname][y].append(ret * 100)
    elapsed = time.time() - t0
    print(f"  [{i+1}/{len(grid)}] {gname} done ({elapsed:.0f}s)", flush=True)

# Summarize
print()
print(f"{'Config':<24} ", end='')
all_years = sorted(set(y for v in results.values() for y in v))
for y in all_years:
    print(f" {y:>7}", end='')
print(f" {'5y avg':>7}")
print("-" * 75)

ranked = []
for gname in results:
    yearly_avgs = []
    for y in all_years:
        if y in results[gname]:
            yearly_avgs.append(sum(results[gname][y]) / len(results[gname][y]))
    if yearly_avgs:
        five_y = sum(yearly_avgs) / len(yearly_avgs)
        ranked.append((five_y, gname, yearly_avgs))

ranked.sort(reverse=True)

for five_y, gname, yearly_avgs in ranked[:15]:
    print(f"{gname:<24} ", end='')
    for avg in yearly_avgs:
        print(f" {avg:>+6.2f}%", end='')
    print(f" {five_y:>+6.2f}%")

print()
print(f"Reference: 0050 ETF +15.52%, original HPTrend +13.48% (README)")
