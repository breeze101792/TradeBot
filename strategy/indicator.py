import backtrader as bt

class OnBalanceVolume(bt.Indicator):
    lines = ('obv',)

    def __init__(self):
        self.addminperiod(2)  # 至少需要 2 天的數據來計算 OBV

    def next(self):
        if len(self) == 1:
            self.lines.obv[0] = 0
        else:
            if self.data.close[0] > self.data.close[-1]:
                self.lines.obv[0] = self.lines.obv[-1] + self.data.volume[0]
            elif self.data.close[0] < self.data.close[-1]:
                self.lines.obv[0] = self.lines.obv[-1] - self.data.volume[0]
            else:
                self.lines.obv[0] = self.lines.obv[-1]


class AccumulationDistribution(bt.Indicator):
    lines = ('ad',)

    def __init__(self):
        self.addminperiod(2)  # 至少需要 2 天的數據來計算 A/D 線

    def next(self):
        if len(self) == 1:
            self.lines.ad[0] = 0  # 初始化 A/D 線
        else:
            # 檢查 High 和 Low 之間的差異，防止除以零
            high_low_diff = self.data.high[0] - self.data.low[0]
            
            if high_low_diff != 0:  # 確保不會除以零
                money_flow_multiplier = ((self.data.close[0] - self.data.low[0]) - (self.data.high[0] - self.data.close[0])) / high_low_diff
            else:
                money_flow_multiplier = 0  # 當 High 和 Low 相等時，設置為 0

            # 計算 Money Flow Volume
            money_flow_volume = money_flow_multiplier * self.data.volume[0]
            
            # 更新 A/D 線
            self.lines.ad[0] = self.lines.ad[-1] + money_flow_volume


class ChaikinMoneyFlow(bt.Indicator):
    lines = ('cmf',)

    def __init__(self, period=20):
        self.period = period
        self.addminperiod(self.period)  # 至少需要一定的歷史數據來計算 CMF

    def next(self):
        if len(self) < self.period:
            self.lines.cmf[0] = 0  # 直到累積足夠的數據為止，保持 CMF 為 0
        else:
            # 計算 Money Flow Multiplier
            high_low_diff = self.data.high[0] - self.data.low[0]

            if high_low_diff != 0:  # 確保不會除以零
                money_flow_multiplier = ((self.data.close[0] - self.data.low[0]) - (self.data.high[0] - self.data.close[0])) / high_low_diff
            else:
                money_flow_multiplier = 0  # 如果 High 和 Low 相等，設為 0

            # 計算 Money Flow Volume
            money_flow_volume = money_flow_multiplier * self.data.volume[0]
            
            # 計算 CMF
            # 當前 CMF 是過去 period 天的 Money Flow Volume 的總和，並除以這些天的總成交量
            cmf_value = sum([money_flow_multiplier * self.data.volume[i] for i in range(-self.period, 0)]) / sum([self.data.volume[i] for i in range(-self.period, 0)])
            self.lines.cmf[0] = cmf_value


class VWAP(bt.Indicator):
    lines = ('vwap',)

    def __init__(self, period=20):
        self.period = period
        self.addminperiod(self.period)

    def next(self):
        if len(self) < self.period:
            self.lines.vwap[0] = 0
        else:
            cumulative_volume_price = sum([self.data.close[i] * self.data.volume[i] for i in range(-self.period, 0)])
            cumulative_volume = sum([self.data.volume[i] for i in range(-self.period, 0)])
            self.lines.vwap[0] = cumulative_volume_price / cumulative_volume

