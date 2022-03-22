# from common import *
# import sys
# sys.path.insert(0, '../')
from market.HalInterface import *
from twstock.stock import *
from twstock.codes import *
from utility.debug import *
import twstock
import datetime
import time
# This require twstock

class TWSESrc(DataSrc):
    def __init__(self):
        self.initial_request_delay=10
        self.request_delay=3
        self.product_list={}

        self.__src_init()
    def __src_init(self):
        raw_list = twstock.codes
        id_list = list(twstock.codes)

        # StockCodeInfo(type='股票', code='2330', name='台積電', ISIN='TW0002330008', start='1994/09/05', market='上市', group='半導體業', CFI='ESVUFR')
        for each_id in id_list:
            each_product=raw_list[each_id]
            # if each_product.market != "上市" and each_product.market != "興櫃":
            # if each_product.type != "股票":
            #     continue
            # print(each_product.code, each_product.name, each_product.type, each_product.market, each_product.group, each_product.start)
            self.product_list[each_product.code]={'code':each_product.code, \
                    'name':each_product.name, \
                    'type':each_product.type, \
                    'market':each_product.market, \
                    'industry':each_product.group, \
                    'startdate':int(each_product.start.replace("/","")) }
        # print(self.product_list)
    def search_product(self, query_data):
        # {'9958': {'code': '9958', 'name': '世紀鋼', 'type': '股票', 'market': '上市', 'industry': '鋼鐵工業', 'startdate': '20080312'}}
        return self.product_list[query_data]
    def get_product_info(self, product_id):
        # {'9958': {'code': '9958', 'name': '世紀鋼', 'type': '股票', 'market': '上市', 'industry': '鋼鐵工業', 'startdate': '20080312'}}
        return self.product_list[product_id]
    def get_product_list(self):
        # twstock.codes.fetch.__update_codes()
        # twstock.codes.__update_codes()
        # __update_codes()
        # return self.product_list
        # [{'code': '9958', 'name': '世紀鋼', 'type': '股票', 'market': '上市', 'industry': '鋼鐵工業', 'startdate': '20080312'}, ]
        return list(self.product_list.values())
    def get_product_data_by_date(self, product_id, start_date=-1):
        # Data(date=datetime.datetime(2021, 5, 20, 0, 0), capacity=36605692, turnover=20670883290, open=567.0, high=571.0, low=560.0, close=567.0, change=0.0, transaction=32301)
        stock_data=[]
        start_year = 2010
        start_month = 1
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month

        if start_date != -1:
            start_year = int(start_date/10000)
            start_month = int(start_date%10000/100 )

        # if start_date == -1:
        #     product_info = self.get_product_info(product_id)
        #     start_year = int(product_info['startdate']/10000)
        #     start_month = int(product_info['startdate']%10000/100 )
        product_info = self.get_product_info(product_id)

        if start_year < int(product_info['startdate']/10000):
            start_year = int(product_info['startdate']/10000)

        if start_year < 2010:
            # twse only store year after 2010
            start_year = 2010

        if start_year > current_year:
            start_year = current_year

        if start_month < int(product_info['startdate']%10000/100 ) and start_year == int(product_info['startdate']/10000):
            start_month = int(product_info['startdate']%10000/100 )

        if start_month > 12:
            start_month = 12

        if start_month < 1:
            start_month = 1

        time.sleep(self.initial_request_delay)
        stock = Stock(product_id)
        dbg_info("Fetch from %s to %s" % (start_year, current_year))
        for each_year in range(start_year, current_year + 1):
            # print("Y: ", each_year)
            tmp_start_month=1
            tmp_end_month=12
            if each_year == start_year:
                tmp_start_month = start_month
            if each_year == current_year:
                tmp_end_month = current_month

            for each_month in range(tmp_start_month, tmp_end_month + 1):
                dbg_info("Fetch Product %s durning YD %s-%s " % (product_id, each_year, each_month))

                time.sleep(self.request_delay)
                stock.fetch(each_year, each_month)

                # print(stock.data[0])
                # print(type(stock.data[0]))
                for each_data in list(stock.data):
                    # print(each_data)
                    # (ID int NOT NULL, Date date, Open int, High int, Low int, Close int, Volume int, Turnover int, TransactionCnt int)''')
                    # tmp_data={'date':each_data.date.strftime('%Y-%m-%d %H:%M:%S'), \
                    tmp_data={'date':each_data.date.strftime('%Y%m%d'), \
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
    def get_product_data(self, product_id):
        return self.get_product_data_by_date(product_id)

# Data(date=datetime.datetime(2021, 6, 30, 0, 0), capacity=34021380, turnover=20301841661, open=599.0, high=599.0, low=595.0, close=595.0, change=0.0, transaction=20097)
def twse_main():
    hal_src = TWSESrc()
    product_code='2330'
    print(hal_src.get_product_list()[0:10])
    print(hal_src.search_product(product_code))
    print(hal_src.get_product_info(product_code))
    print(hal_src.get_product_data(product_code)[0])
    # print(hal_src.get_product_data_by_date(product_code, 20200500))

def twse_dev_main():
    hal_src = TWSESrc()
    product_code='2330'
    print(hal_src.get_product_data_by_date(product_code, 20200100))
if __name__ == '__main__':
    # twse_main()
    twse_dev_main()
