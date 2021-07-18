# Nead to add additional info
import sys
sys.path.insert(0, '../')

from utility.common import *
# from utility.debug import *
# from market.stockPool import *
from market.hal_twstock import *
from market.hal_database import *

class Market:
    def __init__(self):
        # self.default_src = TWSESrc()
        self.default_src = DBSrc()
    def search_product(self, query_str):
        return self.default_src.search_product(query_str)
    def get_product_list(self):
        product_list = []
        for each_product in self.default_src.get_product_list():
            product_list.append(Product(each_product))
        return product_list
        # return self.default_src.get_product_list()
    def get_product(self, product_code):
        target_product = Product()
        target_product.set_info(self.default_src.get_product_info(product_code))
        target_product.set_data(self.default_src.get_product_data(product_code))
        return target_product
    # def get_product_info(self, product_code):
    #     return self.default_src.get_product_info(product_code)
    # def get_product_data(self, product_code, startDate = -1, endDate = -1):
    #     return self.default_src.get_product_data( product_code)

def mkt_main():
    tw_mkt = Market()
    stock_str = "2330"

    print("## Function Test: search_product")
    print("#############################################")
    product_info = tw_mkt.search_product(stock_str.__str__())
    print("Stock: ", product_info['name'])
    product_code=product_info['code']

    print("\n## Function Test: get_product")
    print("#############################################")
    product_ins = tw_mkt.get_product(product_code.__str__())
    print(product_ins)
    product_ins.data.dump()

    print("\n## Function Test: get_product_list")
    print("#############################################")
    stock_list = tw_mkt.get_product_list()
    for each_stock in stock_list[0:10]:
        # print("StockID: ", each_stock['code'], ", name: ", each_stock['name'])
        print(each_stock)

    # End of test
    return

    print("\n## Function Test: get_product_info")
    print("#############################################")
    product_info = tw_mkt.get_product_info(product_code.__str__())
    print("code: ", product_info['code'], ", name: ", product_info['name'], ", industry: ", product_info['industry'])

    print("\n## Function Test: get_product_data")
    print("#############################################")
    stock_data = tw_mkt.get_product_data(product_code)
    for each_data in stock_data[0:10]:
        print("date: ", each_data['date'], ", open: ", each_data['open'], ", close: ", each_data['close'], ", high: ", each_data['high'], ", low: ", each_data['low'], ", volume: ", each_data['volume'])

if __name__ == '__main__':
    mkt_main()

