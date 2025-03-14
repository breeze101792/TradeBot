# system file
import traceback
import time
import threading

# FIXME, may be remove latter
import backtrader as bt
import pandas as pd
from datetime import datetime

# Local file
from utility.debug import *
from core.database import *
from market.dataprovider import *

from market.provider.yahoo import *
from market.provider.twse import *

# from backtest.backtest import *
# from strategy.strategy import *

class Market(DataProvider):
    def __init__(self):
        self.instance = None
        # self.instance = Yahoo()
        self.__set_market__(TWSE())

    def __set_market__(self, instance):
        self.instance = instance
        self.cache_data_name = self.instance.cache_data_name
        self.download_data_list = self.instance.download_data_list
        self.download_data = self.instance.download_data

    def get_top_product_list(self):
        top_tw_stocks = [
            "2330", "2454", "2317", "2881", "2308",
            "2882", "2412", "2382", "2891", "3711",
            "2886", "2303", "1301", "1303", "1216",
            "2884", "6669", "2885", "5880", "3045"
        ]
        return top_tw_stocks

