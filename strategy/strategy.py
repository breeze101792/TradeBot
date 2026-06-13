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
from strategy.candidate.adaptive import AdaptiveTrendStrategy
from strategy.candidate.hybrid import HybridStrategy
from strategy.candidate.trendrider import TrendRiderStrategy

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
