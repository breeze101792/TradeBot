"""
HPTrend variants test: tune trailing_stop and trailing_takeprofit to
close the 2pp gap to 0050.

Variants:
  HPTrend: 10% stop, 12% take-profit (current)
  HPR-15-25: 15% stop, 25% take-profit (wider both, hold longer)
  HPR-15-99: 15% stop, 99% take-profit (TrendRider style)
  HPR-12-25: 12% stop, 25% take-profit
  HPR-8-20: 8% stop, 20% take-profit
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
from strategy.ai.hptrend import HPFilter
from strategy.basic.movingprofit import MovingProfitStrategy
import numpy as np

CACHE_DIR = '/home/shaowu/.config/investment/data/findmind/datas/20250620'

# Sub-sample for quick test
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


# 5y window
to_date = datetime(2024, 12, 31)
from_date = to_date - relativedelta(years=5)


class HPTrendVariant(MovingProfitStrategy):
    """HP-filtered trend detection with configurable stop/take-profit."""
    NAME = "HPTrendV"

    params = (
        ("hp_lookback", 90),
        ("hp_lambda", 1e5),
        ("slope_lookback", 3),
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.10),
        ("trailing_takeprofit_pct", 0.12),
    )

    def stra_initial(self):
        self.hp_filter = HPFilter(lam=self.p.hp_lambda)
        self._price_history = {d: [] for d in self.datas}
        self._hp_trend = {d: [] for d in self.datas}

    def next(self):
        for data in self.datas:
            try:
                close = data.close[0]
            except IndexError:
                continue
            self._price_history[data].append(close)
            if len(self._price_history[data]) > self.p.hp_lookback:
                self._price_history[data].pop(0)
            if len(self._price_history[data]) >= 30:
                trend = self.hp_filter.filter(self._price_history[data])
                self._hp_trend[data] = list(trend)
            else:
                self._hp_trend[data] = []
        super().next()

    def _is_strong_uptrend(self, data):
        if data not in self._hp_trend or len(self._hp_trend[data]) < self.p.slope_lookback + 1:
            return False
        for i in range(0, self.p.slope_lookback):
            curr = self._hp_trend[data][-(i + 1)]
            prev = self._hp_trend[data][-(i + 2)] if i + 2 <= len(self._hp_trend[data]) else curr
            if curr <= prev:
                return False
        return True

    def stra_buy_in(self, data):
        return self._is_strong_uptrend(data)

    def stra_sell_out(self, data):
        return not self._is_strong_uptrend(data)


# Variants to test (stop%, takeprofit%)
variants = [
    ("HPR-10-12", 0.10, 0.12),  # current
    ("HPR-10-99", 0.10, 0.99),  # no TP
    ("HPR-12-99", 0.12, 0.99),  # no TP, slightly wider stop
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
    rets = list(ar.values())
    avg = sum(rets) / len(rets) * 100 if rets else 0
    return ar, avg


# Run all variants on all stocks
print(f"HPTrend variant grid search on {len(sample)} stocks")
print(f"Window: {from_date.date()} -> {to_date.date()}")
print()

variant_results = {v[0]: [] for v in variants}

for symbol in sample:
    df = load_data(symbol)
    if df is None or len(df) < 200:
        continue
    for vname, stop, tp in variants:
        ar, avg = run_backtest(df, stop, tp, symbol)
        variant_results[vname].append(avg)

print(f"{'Variant':<14} {'Stop%':>6} {'TP%':>6}  {'5y avg':>8}")
print("-" * 50)
for vname, stop, tp in variants:
    n = len(variant_results[vname])
    if n > 0:
        avg = sum(variant_results[vname]) / n
        print(f"{vname:<14} {stop*100:>5.0f}% {tp*100:>5.0f}%  {avg:>+7.2f}%")

print()
print(f"Reference: HPTrend (10/12) original ~+13.48%, 0050 ETF +15.52%")
