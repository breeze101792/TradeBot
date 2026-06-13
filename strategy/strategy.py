import backtrader as bt
import pandas as pd
from utility.debug import *
from enum import Enum, auto

# Offical
from strategy.candidate.mac import MovingAverageCrossoverStrategy, MACDCrossoverStrategy, EMACrossoverStrategy
from strategy.candidate.bm import BreakoutMomentumStrategy
from strategy.candidate.rsi import RelativeStrengthIndexStrategy, RSI_SMA
from strategy.candidate.bmr import BollingerMeanReversionStrategy
from strategy.candidate.multisignal import MultiSignalStrategy

# AI / noise-filtered strategies (uses signal processing on
# price before trend detection: HP filter, Kalman, slope, etc.)
from strategy.ai.adaptive import AdaptiveTrendStrategy
from strategy.ai.hybrid import HybridStrategy
from strategy.ai.trendrider import TrendRiderStrategy
from strategy.ai.atrtrend import ATRTrendStrategy
from strategy.ai.slopetrend import SlopeTrendStrategy
from strategy.ai.hptrend import HPTrendStrategy

# Canonical quant strategies (GEMS, Turtle, Dual Thrust, etc.)
from strategy.ai.dualmomentum import DualMomentumStrategy
from strategy.ai.donchian import DonchianStrategy
from strategy.ai.dualthrust import DualThrustStrategy
from strategy.ai.volbreakout import VolatilityBreakoutStrategy
from strategy.ai.supertrend import SuperTrendStrategy
from strategy.ai.keltner import KeltnerChannelStrategy
from strategy.ai.keltner_hp import KeltnerHPStrategy
from strategy.ai.psar import ParabolicSARStrategy
from strategy.ai.hptrend_ha import HPTrendHAStrategy

# experiment
from strategy.experiment.experiment import *
from strategy.experiment.volumn import *
from strategy.experiment.bollinger import BollingerRebound
from strategy.experiment.test import *
from strategy.experiment.vwap import *

class StrategyManager:
    class Level(Enum):
        OFFICIAL = auto()
        BETA = auto()
        TESTING = auto()
    def __init__(self, test = 0):
        self.strategies = {level: {} for level in self.Level}
        
        ## Official strategy
        # adjust for win rate/profit.
        self.register_strategy(MovingAverageCrossoverStrategy, level=self.Level.OFFICIAL)

        ## Beta strategy
        self.register_strategy(BreakoutMomentumStrategy, level=self.Level.BETA)
        self.register_strategy(RelativeStrengthIndexStrategy, level=self.Level.BETA)

        self.register_strategy(BollingerMeanReversionStrategy, level=self.Level.BETA)

        # Moving average.
        self.register_strategy(MACDCrossoverStrategy, level=self.Level.BETA)
        self.register_strategy(EMACrossoverStrategy, level=self.Level.BETA)

        # RSI .
        # self.register_strategy(RSI_SMA)

        # new added.
        # need to use the original price for it.
        # self.register_strategy(VolumeWeightedAveragePriceStrategy)
        self.register_strategy(VolumeWeightedAveragePriceCrossStrategy, level=self.Level.BETA)

        # signal watcher
        self.register_strategy(MultiSignalStrategy, level=self.Level.BETA)

        ## AI Strategy
        ########################################################################
        # Long-term trend filter + medium-term momentum entry + ATR scaling.
        self.register_strategy(AdaptiveTrendStrategy, level=self.Level.BETA)

        # MultiSignal with trend-conditioned exit (hybrid mean-reversion + trend-following).
        self.register_strategy(HybridStrategy, level=self.Level.BETA)

        # Long-only trend-rider: buy on trend filter, hold with wide trailing stop.
        self.register_strategy(TrendRiderStrategy, level=self.Level.BETA)

        # ATR-adaptive trend: long-term filter (SMA-200) + ATR-volatility-based stops.
        self.register_strategy(ATRTrendStrategy, level=self.Level.BETA)

        # SlopeTrend: SMA slope + Kalman-filtered MACD momentum. Filters out
        # bear-market rallies that the Hybrid's "price > SMA" check lets through.
        self.register_strategy(SlopeTrendStrategy, level=self.Level.BETA)

        # HPTrend: Hodrick-Prescott filtered price + slope. Denoses the
        # 1-2 day noise that fools the Hybrid's raw-price trend filter.
        self.register_strategy(HPTrendStrategy, level=self.Level.BETA)

        # GEMS-style Dual Momentum: 12m return + 200d MA filter. Famous for
        # beating buy-and-hold with less drawdown (Antonacci 2014).
        self.register_strategy(DualMomentumStrategy, level=self.Level.BETA)

        # Donchian / Turtle breakout: 20-day high entry, 10-day low exit.
        # The original trend-following system (Dennis 1983).
        self.register_strategy(DonchianStrategy, level=self.Level.BETA)

        # Dual Thrust: adaptive breakout using yesterday's range. Robust
        # across markets (Chiu 1997).
        self.register_strategy(DualThrustStrategy, level=self.Level.BETA)

        # Larry Williams' Volatility Breakout: Open + k*ATR threshold.
        # Famous overnight momentum rule.
        self.register_strategy(VolatilityBreakoutStrategy, level=self.Level.BETA)

        # SuperTrend: ATR-based trend indicator, very popular on TradingView.
        # Designed to ride trends with volatility-adjusted bands.
        self.register_strategy(SuperTrendStrategy, level=self.Level.BETA)

        # Keltner Channel: EMA + k*ATR envelope. Volatility-adaptive breakout.
        self.register_strategy(KeltnerChannelStrategy, level=self.Level.BETA)

        # KeltnerHP: Keltner Channel on HP-filtered price. Combines
        # Keltner's adaptive bands with HP's denoising.
        self.register_strategy(KeltnerHPStrategy, level=self.Level.BETA)

        # Parabolic SAR: Wilder's original trailing-stop flip indicator.
        self.register_strategy(ParabolicSARStrategy, level=self.Level.BETA)

        # HPTrendHA: HPTrend on Heikin Ashi close (HA close = (O+H+L+C)/4).
        # Doubly-smoothed trend: HA removes bar noise, HP removes longer noise.
        self.register_strategy(HPTrendHAStrategy, level=self.Level.BETA)
        ########################################################################

        # Testing, don't enable it on real world.
        if test > 0:
            # Strategy registration.
            # tested
            self.register_strategy(MovingAverageCrossoverEn, level=self.Level.TESTING)
            self.register_strategy(BreakoutMomentumEn, level=self.Level.TESTING)
            # self.register_strategy(MovingAverageCrossover)
            # self.register_strategy(BreakoutMomentum)
            self.register_strategy(PriceVolumeStrategy, level=self.Level.TESTING)
            self.register_strategy(VWAPStrategy, level=self.Level.TESTING)

            # New.
            # self.register_strategy(BollingerRebound)

            # self.register_strategy(OBVStrategy)
            # self.register_strategy(ADLineStrategy)
            # self.register_strategy(PriceVolumeBreakoutStrategy)
            # self.register_strategy(CMFStrategy)
            self.register_strategy(VolumeSpikeStrategy, level=self.Level.TESTING)

            # Test
            # self.register_strategy(TestStrategy)
            # self.register_strategy(Test2Strategy)
            # self.register_strategy(HighWinRateStrategy)

        # print(f'Init StrategyManager {self.strategies}, {test}', )

    def get_default_strategy(self):
        """
        Gets the default strategy, prioritizing OFFICIAL strategies.
        If no OFFICIAL strategies are found, it falls back to BETA.
        """
        for level in [self.Level.OFFICIAL, self.Level.BETA]:
            if self.strategies[level]:
                return list(self.strategies[level].values())[0]
        return None  # Or raise an exception, depending on desired behavior

    def register_strategy(self, new_strategy, level=None):
        if level is None:
            level = self.Level.TESTING

        for lvl in self.Level:
            if new_strategy.NAME in self.strategies[lvl]:
                dbg_error(f'Strategy has been registered: {new_strategy.NAME} in level {lvl.name}')
                raise

        self.strategies[level][new_strategy.NAME] = new_strategy

    def get_strategy_list(self, levels=None):
        if levels is None:
            levels = [self.Level.OFFICIAL]

        strategies = []
        for level in levels:
            if level in self.strategies:
                strategies.extend(self.strategies[level].values())
        return strategies

    def get_strategy_by_name(self, name):
        for level in self.Level:
            strategy = self.strategies[level].get(name)
            if strategy:
                return strategy
        
        dbg_error(f"Strategy not found. {name}")
        raise
