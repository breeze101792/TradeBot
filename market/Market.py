# Nead to add additional info
import sys
sys.path.insert(0, '../')

from utility.common import *
# from debug import *
# from market.stockPool import *
from market.hal_twstock import *

class Market:
    def __init__(self):
        self.net_src = TWSESrc()
        pass
    def search_product(self, query_str):
        return self.net_src.search_product(query_str)
    def get_product_list(self):
        return self.net_src.get_product_list()
    def get_product_info(self, stockID):
        return self.net_src.get_product_info(stockID)
    def get_product_data(self, stockID, startDate = -1, endDate = -1):
        return self.net_src.get_product_data( stockID)

def mkt_main():
    tw_mkt = Market()
    stock_str = "2454"

    print("## Function Test: search_product")
    print("#############################################")
    product_info = tw_mkt.search_product(stock_str.__str__())
    print("Stock: ", product_info['name'])
    product_id=product_info['code']

    print("\n## Function Test: get_product_info")
    print("#############################################")
    product_info = tw_mkt.get_product_info(product_id.__str__())
    print("code: ", product_info['code'], ", name: ", product_info['name'], ", industry: ", product_info['industry'])

    print("\n## Function Test: get_product_list")
    print("#############################################")
    stock_list = tw_mkt.get_product_list()
    # print(stock_list)
    # return
    for each_stock in stock_list[0:10]:
        print("StockID: ", each_stock['code'], ", name: ", each_stock['name'])

    print("\n## Function Test: get_product_data")
    print("#############################################")
    stock_data = tw_mkt.get_product_data(product_id)
    for each_data in stock_data[0:10]:
        print("date: ", each_data['date'], ", open: ", each_data['open'], ", close: ", each_data['close'], ", high: ", each_data['high'], ", low: ", each_data['low'], ", volume: ", each_data['volume'])

if __name__ == '__main__':
    mkt_main()

