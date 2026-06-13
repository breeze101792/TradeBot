"""
HPTrend variants: tune trailing_stop and trailing_takeprofit using the
same averaging method as the README (mean of all (stock × year) cells).

This matches what `_prepare_annual_return_data` reports as the
"Average" row's year columns.
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
from strategy.basic.movingprofit import MovingProfitStrategy
import numpy as np

CACHE_DIR = '/home/shaowu/.config/investment/data/findmind/datas/20250620'

# Full t50 (excluding 2301 which has missing data)
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


class HPTrendVariant(HPTrendStrategy):
    """Same as HPTrend but with configurable stop/take-profit."""
    NAME = "HPTrendV"

    params = (
        # HP filter (inherited, but restate for clarity)
        ("hp_lookback", 90),
        ("hp_lambda", 1e5),
        ("slope_lookback", 3),
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.10),
        ("trailing_takeprofit_pct", 0.12),
        # Inherited
        ("bb_period", 20), ("bb_stddev", 2),
        ("rsi_period", 14), ("rsi_entry", 30), ("rsi_exit", 70),
        ("macd_fast", 12), ("macd_slow", 26), ("macd_signal", 9),
        ("vol_period", 20),
        ("vwap_period", 20),
    )


variants = [
    ("HPR-10-12", 0.10, 0.12),  # current baseline
    ("HPR-10-99", 0.10, 0.99),  # no TP
    ("HPR-12-25", 0.12, 0.25),  # wider stop, wider TP
    ("HPR-12-99", 0.12, 0.99),  # no TP, slightly wider stop
    ("HPR-13-99", 0.13, 0.99),  # in-between
    ("HPR-14-99", 0.14, 0.99),  # in-between
    ("HPR-15-99", 0.15, 0.99),  # wide stop, no TP
    ("HPR-08-99", 0.08, 0.99),  # tight stop, no TP
]


def run_backtest(df, stop, tp, name):
    cerebro = bt.Cerebro()
    cerebro.broker.set_cash(1_000_000_000)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.broker.set_slippage_perc(perc=0.001)
    data = ExtPandasDataFeed(dataname=df, fromdate=from_date, todate=to_date)
    cerebro.adddata(data, name=name)
    cerebro.addstrategy(HPTrendVariant, trailing_stop_pct=stop, trailing_takeprofit_pct=tp)
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='ar')
    results = cerebro.run()
    ar = results[0].analyzers.ar.get_analysis()
    return ar


# Use the same averaging as README: collect ALL (stock, year) cells, average per year, then mean of years
print(f"HPTrend variant grid search on {len(sample)} stocks (t50, 2020-2024)")
print()

variant_yearly = {v[0]: {} for v in variants}  # variant -> year -> [returns]

for symbol in sample:
    df = load_data(symbol)
    if df is None or len(df) < 200:
        continue
    for vname, stop, tp in variants:
        ar = run_backtest(df, stop, tp, symbol)
        for year_str, ret in ar.items():
            y = int(year_str)
            if y not in variant_yearly[vname]:
                variant_yearly[vname][y] = []
            variant_yearly[vname][y].append(ret * 100)

print(f"{'Variant':<14} ", end='')
all_years = sorted(set(y for v in variant_yearly.values() for y in v))
for y in all_years:
    print(f" {y:>7}", end='')
print(f" {'5y avg':>7}")
print("-" * 75)

for vname, stop, tp in variants:
    yearly_avgs = []
    print(f"{vname:<14} ", end='')
    for y in all_years:
        if y in variant_yearly[vname]:
            avg = sum(variant_yearly[vname][y]) / len(variant_yearly[vname][y])
            yearly_avgs.append(avg)
            print(f" {avg:>+6.2f}%", end='')
        else:
            print(f" {'N/A':>7}", end='')
    five_y = sum(yearly_avgs) / len(yearly_avgs) if yearly_avgs else 0
    print(f" {five_y:>+6.2f}%")

print()
print("Reference: HPTrend (10/12) original was 13.48% 5y avg, 0050 ETF 15.52%")
