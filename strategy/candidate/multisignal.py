import backtrader as bt
import pandas as pd
from utility.debug import *
from strategy.basic.basicstrategy import *
from strategy.basic.movingprofit import MovingProfitStrategy

class MultiSignalStrategy(MovingProfitStrategy):
    NAME="MultiSignal"
    params = dict(
        bb_period=20, bb_stddev=2,
        rsi_period=14, rsi_entry=30,
        macd_fast=12, macd_slow=26, macd_signal=9,
        vol_period=20,

        trail_percent=0.05,  # 移動止盈距離 (5%)
        max_loss=0.05,       # 最大單筆虧損5%
        max_add=1            # 最大加碼次數
    )

    def stra_initial(self):
        self.bb = bt.indicators.BollingerBands(
            self.data.close, period=self.p.bb_period, devfactor=self.p.bb_stddev)
        self.rsi = bt.indicators.RSI(
            self.data.close, period=self.p.rsi_period)
        self.macd = bt.indicators.MACD(
            self.data.close, period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal)
        self.vol_ma = bt.indicators.SMA(self.data.volume, period=self.p.vol_period)

    # def stra_buy_in(self, data):
    #     if (self.data.close[0] <= self.bb.bot[0] and
    #         # self.rsi[0] < self.p.rsi_entry and
    #         # self.macd.macd[0] > self.macd.signal[0] and
    #         self.data.volume[0] > self.vol_ma[0]):
    #         return True
    #     else:
    #         return False
    def stra_bb_buy(self, data):
        check_days = 20

        # Check if we have enough data points
        if len(self.data) < check_days + 1:
            return False

        # Check if the price was below or equal to the lower band for at least one day
        # within the previous 'check_days' period.
        previous_days_below = False
        for i in range(1, check_days + 1):
            if self.data.close[-i] <= self.bb.bot[-i]:
                previous_days_below = True
                break # Found a day below or equal, condition met for this part

        # Check if today's close is above the lower band
        today_above = self.data.close[0] > self.bb.bot[0]

        # print('bb: ', previous_days_below , today_above)
        # Return True if price was below/equal in the recent past AND today is above the lower band
        return previous_days_below and today_above

    def stra_rsi_buy(self, data):
        check_days = 20

        # Check if we have enough data points
        if len(self.data) < check_days + 1:
            return False

        # Check if RSI was above the entry threshold for the previous 'check_days'
        previous_days_below_threshold = False
        for i in range(1, check_days + 1):
            if self.rsi[-i] <= self.p.rsi_entry:
                previous_days_below_threshold = True
                break # No need to check further if any day was below/equal

        # Check if today's RSI is below or equal to the entry threshold
        today_below_threshold = self.rsi[0] > self.p.rsi_entry

        # print(f'rsi: {self.rsi[0]:.2f}, {previous_days_below_threshold} , {today_below_threshold}')
        # Return True if previous days were above AND today is below/equal
        return previous_days_below_threshold and today_below_threshold

    def stra_macd_buy(self, data):
        check_days = 20

        # Check if we have enough data points
        if len(self.data) < check_days + 1:
            return False

        # Check if MACD was below or equal to the signal line for the previous 'check_days'
        previous_days_below_signal = False
        for i in range(1, check_days + 1):
            if self.macd.macd[-i] < self.macd.signal[-i]:
                previous_days_below_signal = True
                break # No need to check further if any day was above

        # Check if today's MACD is above the signal line (bullish crossover)
        today_above_signal = self.macd.macd[0] > self.macd.signal[0]

        # print('macd: ', previous_days_below_signal , today_above_signal)
        # Return True if previous days were below/equal AND today is above
        return previous_days_below_signal and today_above_signal

    def stra_buy_in(self, data):
        if ( True and
            self.stra_bb_buy(data) and
            self.stra_rsi_buy(data) and
            self.stra_macd_buy(data) and
            # self.data.volume[0] > self.vol_ma[0]
            True):
            return True
        else:
            return False

    def stra_sell_out(self, data):
        return False
        if (self.rsi[0] > 70 or
            self.macd.macd[0] < self.macd.signal[0] or
            self.data.close[0] > self.bb.top[0]):
            return True
        else:
            return False
