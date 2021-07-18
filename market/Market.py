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
        self.local_src = DBSrc()
        self.online_src = TWSESrc()
    def search_product(self, query_str):
        return self.local_src.search_product(query_str)
    def get_product_list(self):
        product_list = []
        for each_product in self.local_src.get_product_list():
            product_list.append(Product(each_product))
        return product_list
        # return self.local_src.get_product_list()
    def get_product(self, product_code):
        target_product = Product()
        target_product.set_info(self.local_src.get_product_info(product_code))
        target_product.set_data(self.local_src.get_product_data(product_code))
        return target_product
    def update_product_list(self):
        product_list = []
        for each_product in self.online_src.get_product_list():
            product_list.append(each_product)
        # print(product_list)
        self.local_src.insert_product_info(product_list)
    def update_product_data(self, product_code):
        product_data_list = self.online_src.get_product_data(product_code)
        self.local_src.insert_product_data(product_code, product_data_list)
    def update_all_product_data(self):
        for each_product in self.online_src.get_product_list()[0:10]:
            self.update_product_data(each_product['code'])


def mkt_update_main():
    tw_mkt = Market()
    product_code = "2330"

    print("\n## Function Test: update_product_list")
    print("#############################################")
    tw_mkt.update_product_list()

    print("\n## Function Test: get_product_list")
    print("#############################################")
    stock_list = tw_mkt.get_product_list()
    for each_stock in stock_list[0:10]:
        # print("StockID: ", each_stock['code'], ", name: ", each_stock['name'])
        print(each_stock)

    print("\n## Function Test: update_all_product_data")
    print("#############################################")
    tw_mkt.update_all_product_data()

    # print("\n## Function Test: update_product_data")
    # print("#############################################")
    # tw_mkt.update_product_data(product_code)

    return 

def mkt_main():
    tw_mkt = Market()
    # product_code = "1569"
    product_code = "2330"

    print("## Function Test: search_product")
    print("#############################################")
    product_info = tw_mkt.search_product(product_code.__str__())
    print("Stock: ", product_info['name'])
    product_code=product_info['code']

    print("\n## Function Test: get_product")
    print("#############################################")
    product_ins = tw_mkt.get_product(product_code.__str__())
    print(product_ins)
    product_ins.data.dump()

    # End of test
    return

if __name__ == '__main__':
    # mkt_update_main()
    mkt_main()

