import backtrader as bt
import pandas as pd
from utility.debug import *
from strategy.experiment import *
from strategy.test import TestStrategy

class py_prop:
        pass
class StrategyManager:
    def __init__(self, test):
        self.strategy_dict = dict()
        
        # Strategy registration.
        # Experiment.
        self.register_strategy(MovingAverageCrossover)
        self.register_strategy(BreakoutMomentum)
        self.register_strategy(BreakoutMomentumEn)
        self.register_strategy(TestStrategy)
        # print(f'Init StrategyManager {self.strategy_dict}, {test}', )

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
