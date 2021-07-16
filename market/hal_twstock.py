# from common import *
from HalInterface import *
from twstock.stock import *
import twstock
# This require twstock

class TWSESrc(DataSrc):
    def __init__(self):
        self.product_list={}

        self.__src_init()
    def __src_init(self):
        raw_list = twstock.codes
        id_list = list(twstock.codes)

        # StockCodeInfo(type='股票', code='2330', name='台積電', ISIN='TW0002330008', start='1994/09/05', market='上市', group='半導體業', CFI='ESVUFR')
        for each_id in id_list:
            each_product=raw_list[each_id]
            # if each_product.market != "上市" and each_product.market != "興櫃":
            if each_product.type != "股票":
                continue
            # print(each_product.code, each_product.name, each_product.type, each_product.market, each_product.group, each_product.start)
            self.product_list[each_product.code]={'code':each_product.code, \
                    'name':each_product.name, \
                    'type':each_product.type, \
                    'market':each_product.market, \
                    'industry':each_product.group, \
                    'startdate':each_product.start.replace("/","") }
        # print(self.product_list)
    def search_product(self, query_str):
        # {'9958': {'code': '9958', 'name': '世紀鋼', 'type': '股票', 'market': '上市', 'industry': '鋼鐵工業', 'startdate': '20080312'}}
        return self.product_list[query_str]
    def get_product_info(self, product_id):
        # {'9958': {'code': '9958', 'name': '世紀鋼', 'type': '股票', 'market': '上市', 'industry': '鋼鐵工業', 'startdate': '20080312'}}
        return self.product_list[product_id]
    def get_product_list(self):
        # return self.product_list
        return list(self.product_list.values())
    def get_product_data_by_date(self, product_id, start_mounth, end_mounth):
        pass
    def get_product_data(self, product_id):
        stock_data=[]
        # Data(date=datetime.datetime(2021, 5, 20, 0, 0), capacity=36605692, turnover=20670883290, open=567.0, high=571.0, low=560.0, close=567.0, change=0.0, transaction=32301)
        stock = Stock(product_id)
        # print(stock.data[0])
        # print(type(stock.data[0]))
        for each_data in list(stock.data):
            # print(each_data)
            # (ID int NOT NULL, Date date, Open int, High int, Low int, Close int, Volume int, Turnover int, TransactionCnt int)''')
            # tmp_data={'date':each_data.date.strftime('%Y-%m-%d %H:%M:%S'), \
            tmp_data={'date':each_data.date.strftime('%Y-%m-%d'), \
                    'open':each_data.open, \
                    'high':each_data.high, \
                    'low':each_data.low, \
                    'close':each_data.close, \
                    'volume':each_data.capacity, \
                    'turnover':each_data.turnover, \
                    'trasactioncnt':each_data.transaction }
            stock_data.append(tmp_data)
        # print(stock_data)
        return stock_data

# Data(date=datetime.datetime(2021, 6, 30, 0, 0), capacity=34021380, turnover=20301841661, open=599.0, high=599.0, low=595.0, close=595.0, change=0.0, transaction=20097)
def twse_main():
    twse = TWSESrc()
    print(twse.get_product_info('2330'))
    print(twse.get_product_data('2330')[0])
    # twse.search_stock()

if __name__ == '__main__':
    twse_main()
