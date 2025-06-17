import backtrader as bt
import pandas as pd
from utility.debug import *

# Offical
from strategy.candidate.mac import MovingAverageCrossoverStrategy
from strategy.candidate.bm import BreakoutMomentumStrategy
from strategy.candidate.rsi import RelativeStrengthIndexStrategy
from strategy.candidate.bmr import BollingerMeanReversionStrategy
from strategy.candidate.multisignal import MultiSignalStrategy

# experiment
from strategy.experiment.experiment import *
from strategy.experiment.volumn import *
from strategy.experiment.bollinger import BollingerRebound
from strategy.experiment.test import *
from strategy.experiment.vwap import *

class StrategyManager:
    def __init__(self, test = 0):
        self.strategy_dict = dict()
        
        # adjust for win rate/profit.
        self.register_strategy(MovingAverageCrossoverStrategy)
        self.register_strategy(BreakoutMomentumStrategy)
        self.register_strategy(RelativeStrengthIndexStrategy)
        self.register_strategy(BollingerMeanReversionStrategy)

        # new added.
        # need to use the original price for it.
        # self.register_strategy(VolumeWeightedAveragePriceStrategy)
        self.register_strategy(VolumeWeightedAveragePriceCrossStrategy)

        # signal watcher
        self.register_strategy(MultiSignalStrategy)

        if False:
            # Strategy registration.
            # tested
            self.register_strategy(MovingAverageCrossoverEn)
            self.register_strategy(BreakoutMomentumEn)
            # self.register_strategy(MovingAverageCrossover)
            # self.register_strategy(BreakoutMomentum)
            self.register_strategy(PriceVolumeStrategy)
            self.register_strategy(VWAPStrategy)

            # New.
            # self.register_strategy(BollingerRebound)

            # self.register_strategy(OBVStrategy)
            # self.register_strategy(ADLineStrategy)
            # self.register_strategy(PriceVolumeBreakoutStrategy)
            # self.register_strategy(CMFStrategy)
            self.register_strategy(VolumeSpikeStrategy)

            # Test
            # self.register_strategy(TestStrategy)
            # self.register_strategy(Test2Strategy)
            # self.register_strategy(HighWinRateStrategy)

        # print(f'Init StrategyManager {self.strategy_dict}, {test}', )

    def get_default_strategy(self):
        if not self.strategy_dict:
            return None  # Or raise an exception, depending on desired behavior
        return list(self.strategy_dict.values())[0]

    def register_strategy(self, new_strategy):
        if self.strategy_dict.get(new_strategy.NAME) is not None:
            dbg_error(f'Strategy has been registerd. {new_strategy.NAME}')
            raise
        self.strategy_dict[new_strategy.NAME] = new_strategy
    def get_strategy_list(self):
        # for each_key in self.strategy_dict.keys():
        #     print(each_key)
        return [self.strategy_dict[each_key] for each_key in self.strategy_dict.keys()]
    def get_strategy_by_name(self, name):
        if self.strategy_dict.get(name) is None:
            dbg_error(f"Strategy not found. {name}")
            raise
        else:
            return self.strategy_dict[name]
