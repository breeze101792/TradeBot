import pandas as pd
from utility.debug import *

class StockID:
    code = None
    name = None
    def __init__(self, code=None, name=None):
        self.code = code
        self.name = name
    def __str__(self):
        return "{}({})".format(self.name, self.code)

class ProductData:
    # {'date': '2021-05-26', 'open': 587.0, 'high': 588.0, 'low': 581.0, 'close': 585.0, 'volume': 19555305, 'turnover': 11433686898, 'trasactioncnt':
    def __init__(self):
        self.data=[{'date': '2021-07-01', 'open': 0, 'high': 0, 'low': 0, 'close': 0, 'volume': 0, 'turnover': 0, 'trasactioncnt':0}]


    def dump(self):
        # print(self.data)
        for each_data in self.data:
            print("date: " + each_data['date'].__str__() + \
                    ", open: " + each_data['open'].__str__() + \
                    ", close: " + each_data['close'].__str__() + \
                    ", high: " + each_data['high'].__str__() + \
                    ", low: " + each_data['low'].__str__() + \
                    ", close: " + each_data['close'].__str__() + \
                    ", volume: " + each_data['volume'].__str__() + \
                    ", turnover: " + each_data['turnover'].__str__() + \
                    ", trasactioncnt: " + each_data['trasactioncnt'].__str__())

    def set_data(self, data):
        if data is None:
            self.data=[{'date': '2021-07-01', 'open': 0, 'high': 0, 'low': 0, 'close': 0, 'volume': 0, 'turnover': 0, 'trasactioncnt':0}]
        else:
            self.data = data

    @property
    def pdata(self):
        # dbg_info("Data",len(self.data), " ->\n", self.data)
        if len(self.data) == 0:
            return None
        tmp_data = self.data
        # dbg_warning("Remove 30 days restriction")
        # if len(self.data) > 45:
        #     tmp_data = self.data[:45]

        # print([print(list(d.values()), "\n") for d in self.data])
        # print("-------------------------------------------------------\n")
        # df = pd.DataFrame([list(d.values()) for d in self.data], columns=self.data[0].keys())
        df = pd.DataFrame([list(d.values()) for d in tmp_data], columns=tmp_data[0].keys())
        # print(df.head)

        # df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df.set_index('date', inplace=True)
        df.sort_index(ascending=True, inplace=True)
        # print(df.head)
        return df

    @property
    def ndata(self):
        return [d.date for d in self.data]

    @property
    def date(self):
        return [d.date for d in self.data]
    @property
    def volume(self):
        return [d.volume for d in self.data]
    @property
    def turnover(self):
        return [d.turnover for d in self.data]
    @property
    def trasactioncnt(self):
        return [d.trasactioncnt for d in self.data]
    @property
    def high(self):
        return [d.high for d in self.data]
    @property
    def low(self):
        return [d.low for d in self.data]
    @property
    def open(self):
        return [d.open for d in self.data]
    @property
    def close(self):
        return [d.close for d in self.data]

class Product:
    # {'code': '2330', 'name': '台積電', 'type': '股票', 'market': '上市', 'industry': '半導體業', 'startdate': '19940905'}
    def __init__(self, info=None):
        self.info = {'code': '', 'name': '', 'type': '', 'market': '', 'industry': '', 'startdate': ''}
        self.__data = ProductData() 

        if info is not None:
            self.set_info(info)

    def __str__(self):
        return str("code: " + self.info['code'] + \
                ", name: " + self.info['name'] + \
                ", type: " + self.info['type'] + \
                ", market: " + self.info['market'] + \
                ", industry: " + self.info['industry'] + \
                ", startdate: " + self.info['startdate'].__str__())

    def set_info(self, product_info):
        self.info = dict(product_info)

    def set_data(self, data):
        self.__data.set_data(data)

    # Product Infomation
    @property
    def name(self):
        return self.info['name']
    @property
    def code(self):
        return self.info['code']
    @property
    def type(self):
        return self.info['type']
    @property
    def market(self):
        return self.info['market']
    @property
    def industry(self):
        return self.info['industry']
    @property
    def startdate(self):
        return self.info['startdate']
    @property
    def data(self):
        return self.__data

