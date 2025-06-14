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
    """
    Volume Weighted Average Price (VWAP) Indicator.

    VWAP is a trading benchmark used by traders that gives the average price
    a security has traded at throughout the day, based on both volume and price.
    It is typically used by long-term investors to ensure that they are getting
    a fair price, or by short-term traders to identify entry and exit points.
    """
    lines = ('vwap',)

    def __init__(self, period=20):
        """
        Initializes the VWAP indicator.

        Args:
            period (int): The number of periods (e.g., days) over which to calculate VWAP.
                          This defines the look-back window for the calculation.
        """
        self.period = period
        # Ensure that there is enough historical data available for the calculation.
        # The indicator needs at least 'period' number of data points.
        self.addminperiod(self.period)

    def next(self):
        """
        Calculates the VWAP for the current data point.
        """
        # Check if enough data points have accumulated to perform the calculation.
        # If not, set VWAP to 0 or a default value until the 'period' is met.
        if len(self) < self.period:
            self.lines.vwap[0] = 0
        else:
            # Calculate the sum of (price * volume) for the specified period.
            # self.data.close[i] refers to the closing price 'i' periods ago (0 is current, -1 is previous, etc.)
            # self.data.volume[i] refers to the volume 'i' periods ago.
            cumulative_volume_price = sum([self.data.close[i] * self.data.volume[i] for i in range(-self.period, 0)])
            
            # Calculate the total volume for the specified period.
            cumulative_volume = sum([self.data.volume[i] for i in range(-self.period, 0)])
            
            # Calculate VWAP: (Sum of Price * Volume) / (Sum of Volume)
            # Ensure cumulative_volume is not zero to avoid division by zero error.
            if cumulative_volume != 0:
                self.lines.vwap[0] = cumulative_volume_price / cumulative_volume
            else:
                # If there's no volume in the period, VWAP cannot be calculated, set to 0 or previous value.
                # Here, we set it to 0, but depending on strategy, one might prefer self.lines.vwap[-1]
                self.lines.vwap[0] = 0

