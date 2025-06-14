import backtrader as bt
import pandas as pd
from utility.debug import *
from strategy.basic.basicstrategy import *
from strategy.basic.movingprofit import MovingProfitStrategy
from strategy.indicator import *

class MultiSignalStrategy(MovingProfitStrategy):
    NAME="MultiSignal"
    params = dict(
        bb_period=20, bb_stddev=2,
        rsi_period=14, rsi_entry=30, rsi_exit=70,
        macd_fast=12, macd_slow=26, macd_signal=9,
        vol_period=20,
        vwap_period=20, # Added vwap_period to params
    )

    def stra_initial(self):
        self.bb = {}
        self.rsi = {}
        self.macd = {}
        self.vol_ma = {}
        self.vwap_short = {}
        self.vwap_long = {}
        self.close_price = {}

        for data in self.datas:
            self.bb[data] = bt.indicators.BollingerBands(
                data.close, period=self.p.bb_period, devfactor=self.p.bb_stddev)
            self.rsi[data] = bt.indicators.RSI(
                data.close, period=self.p.rsi_period)
            self.macd[data] = bt.indicators.MACD(
                data.close, period_me1=self.p.macd_fast,
                period_me2=self.p.macd_slow,
                period_signal=self.p.macd_signal)
            self.vwap_short[data] = VWAP(data, period=1)
            self.vwap_long[data] = VWAP(data, period=self.params.vwap_period)
            self.vol_ma[data] = bt.indicators.SMA(data.volume, period=self.p.vol_period, plot=False)

    def stra_bb_buy(self, data):
        check_days = 20

        # Check if we have enough data points
        if len(data) < check_days + 1:
            return False

        # Check if the price was below or equal to the lower band for at least one day
        # within the previous 'check_days' period.
        previous_days_below = False
        for i in range(1, check_days + 1):
            if data.close[-i] <= self.bb[data].bot[-i]:
                previous_days_below = True
                break # Found a day below or equal, condition met for this part

        # Check if today's close is above the lower band
        today_above = data.close[0] > self.bb[data].bot[0]

        # print('bb: ', previous_days_below , today_above)
        # Return True if price was below/equal in the recent past AND today is above the lower band
        return previous_days_below and today_above
    def stra_bb_sell(self, data):
        check_days = 20

        # Check if we have enough data points
        if len(data) < check_days + 1:
            return False

        # Check if the price was below or equal to the lower band for at least one day
        # within the previous 'check_days' period.
        previous_days_above = False
        for i in range(1, check_days + 1):
            if data.close[-i] >= self.bb[data].top[-i]:
                previous_days_above = True
                break # Found a day below or equal, condition met for this part

        # Check if today's close is above the lower band
        today_above = data.close[0] < self.bb[data].top[0]

        # print('bb: ', previous_days_above , today_above)
        # Return True if price was below/equal in the recent past AND today is above the lower band
        return previous_days_above and today_above

    def stra_rsi_buy(self, data):
        check_days = 20

        # Check if we have enough data points
        if len(data) < check_days + 1:
            return False

        # Check if RSI was above the entry threshold for the previous 'check_days'
        previous_days_below_threshold = False
        for i in range(1, check_days + 1):
            if self.rsi[data][-i] <= self.p.rsi_entry:
                previous_days_below_threshold = True
                break # No need to check further if any day was below/equal

        # Check if today's RSI is below or equal to the entry threshold
        today_below_threshold = self.rsi[data][0] > self.p.rsi_entry

        # print(f'rsi: {self.rsi[0]:.2f}, {previous_days_below_threshold} , {today_below_threshold}')
        # Return True if previous days were above AND today is below/equal
        return previous_days_below_threshold and today_below_threshold

    def stra_rsi_sell(self, data):
        check_days = 20
        # Check if we have enough data points
        if len(data) < check_days + 1:
            return False

        # Check if RSI was above the entry threshold for the previous 'check_days'
        previous_days_above_threshold = False
        for i in range(1, check_days + 1):
            if self.rsi[data][-i] >= self.p.rsi_exit:
                previous_days_above_threshold = True
                break # No need to check further if any day was below/equal

        # Check if today's RSI is below or equal to the entry threshold
        today_below_threshold = self.rsi[data][0] < self.p.rsi_exit

        # print(f'rsi: {self.rsi[0]:.2f}, {previous_days_above_threshold} , {today_below_threshold}')
        # Return True if previous days were above AND today is below/equal
        return previous_days_above_threshold and today_below_threshold

    def stra_macd_buy(self, data):
        check_days = 20

        # Check if we have enough data points
        if len(data) < check_days + 1:
            return False

        # Check if MACD was below or equal to the signal line for the previous 'check_days'
        previous_days_below_signal = False
        for i in range(1, check_days + 1):
            if self.macd[data].macd[-i] < self.macd[data].signal[-i]:
                previous_days_below_signal = True
                break # No need to check further if any day was above

        # Check if today's MACD is above the signal line (bullish crossover)
        today_above_signal = self.macd[data].macd[0] > self.macd[data].signal[0]

        # print('macd: ', previous_days_below_signal , today_above_signal)
        # Return True if previous days were below/equal AND today is above
        return previous_days_below_signal and today_above_signal
    def stra_macd_sell(self, data):
        check_days = 20

        # Check if we have enough data points
        if len(data) < check_days + 1:
            return False

        # Check if MACD was below or equal to the signal line for the previous 'check_days'
        previous_days_above_signal = False
        for i in range(1, check_days + 1):
            if self.macd[data].macd[-i] >= self.macd[data].signal[-i]:
                previous_days_above_signal = True
                break # No need to check further if any day was above

        # Check if today's MACD is above the signal line (bullish crossover)
        today_above_signal = self.macd[data].macd[0] < self.macd[data].signal[0]

        # print('macd: ', previous_days_above_signal , today_above_signal)
        # Return True if previous days were below/equal AND today is above
        return previous_days_above_signal and today_above_signal

    def stra_vwrp_buy(self, data):
        if self.vwap_short[data][0] > self.vwap_long[data][0]:
            # 當價格高於 VWAP 時，買入
            # dbg_log(f"Buy signal at {self.data.close[0]:.2f}")
            return True
        else:
            return False
    def stra_vwrp_sell(self, data):
        if self.vwap_short[data][0] < self.vwap_long[data][0]:
            # 當價格低於 VWAP 時，賣出
            # dbg_log(f"Sell signal at {self.data.close[0]:.2f}")
            return True
        else:
            return False

    def stra_buy_in(self, data):
        if (
            self.stra_bb_buy(data) and
            self.stra_rsi_buy(data) and
            # self.stra_vwrp_buy(data) and
            # not self.stra_macd_sell(data)
            # self.stra_macd_buy(data) and
            # data.volume[0] > self.vol_ma[data][0] # Updated to use data.volume and self.vol_ma[data]
            True
            ):
            return True
        else:
            return False

    def stra_sell_out(self, data):
        if (
            self.stra_bb_sell(data) or
            self.stra_rsi_sell(data) or
            # self.stra_vwrp_sell(data) or
            # self.stra_macd_sell(data) or
            False
            ):
            return True
        else:
            return False

        # if (self.rsi[data][0] > 70 or # Updated to use self.rsi[data]
        #     data.close[0] > self.bb[data].top[0] or # Updated to use data.close and self.bb[data]
        #     self.macd[data].macd[0] < self.macd[data].signal[0] or # Updated to use self.macd[data]
        #     data.close[0] > self.bb[data].top[0]): # Updated to use data.close and self.bb[data]
        #     return True
        # else:
        #     return False
