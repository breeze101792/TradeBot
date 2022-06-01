# Nead to add additional info
# import sys
# sys.path.insert(0, '../')

from utility.common import *
from utility.debug import *
# from market.stockPool import *
from market.hal_twstock import *
from market.hal_database import *
from datetime import datetime, date, timedelta

class Market:
    def __init__(self):
        # self.default_src = TWSESrc()
        self.local_src = DBSrc()
        self.online_src = TWSESrc()
    def search_product(self, query_str):
        return self.local_src.search_product(query_str)
    ##############################################
    ##  Product Function
    ##############################################
    def prodcut_sanity_check(self, target_product):
        # dbg_info(target_product)
        if (target_product['type'] == "股票" or target_product['type'] == "ETF") and target_product['market'] == "上市":
            return True
        else:
            return False
    def get_industry_list(self):
        industry_list = []
        for each_product in self.local_src.get_product_list():
            if each_product['industry'] not in industry_list and \
                    each_product['industry'] != "" and \
                    self.prodcut_sanity_check(each_product) == True:
                industry_list.append(each_product['industry'])
        return industry_list
    def get_product_list(self, industry=""):
        product_list = []
        for each_product in self.local_src.get_product_list():
            if each_product['industry'] != industry:
                continue
            # else:
            #     dbg_info(each_product['industry'], "<->", industry)

            # dbg_info(each_product['code'], "(", each_product['code'], ")")
            if self.prodcut_sanity_check(each_product) == True:
                tmp_product = Product(each_product)
                # FIXME Only this type of procut will be showen in upper layer
                product_list.append(tmp_product)
        return product_list
        # return self.local_src.get_product_list()
    def get_product(self, product_code):
        # dbg_info("product code:", product_code)
        target_product = Product()
        target_product.set_info(self.local_src.get_product_info(product_code))
        dbg_info("product code:", target_product.code + "(" + target_product.name + ")")
        target_product.set_data(self.local_src.get_product_data(product_code))
        # dbg_info("product:", target_product.data[0])
        return target_product
    # def get_product_by_industry(self, industry):
    #     target_list = []
    #     for each_product in self.local_src.get_product_list():
    #         # dbg_info(each_product)
    #         if each_product['industry'] == industry:
    #             tmp_product = self.get_product(each_product['code'])
    #             target_list.append(tmp_product)
    #     return target_list
    ##############################################
    ##  Udate Function
    ##############################################
    def update_product_list(self):
        product_list = []
        for each_product in self.online_src.get_product_list():
            product_list.append(each_product)
        # print(product_list)
        self.local_src.insert_product_info(product_list)
    def update_product_data(self, product_code, start_date=0):
        if start_date == 0:
            start_date = int((date.today() -  timedelta(days=7)).strftime("%Y%m%d"))

        dbg_info("Update Product %s from %s" % (product_code, start_date))
        # product_data_list = self.online_src.get_product_data(product_code)
        product_data_list = self.online_src.get_product_data_by_date(product_code, start_date)
        dbg_info("product_data_list", product_data_list)
        self.local_src.insert_product_data(product_code, product_data_list)
    def update_all_product_data(self, start_date=0):
        if start_date == 0:
            start_date = int((date.today() -  timedelta(days=7)).strftime("%Y%m%d"))
        for each_product in self.online_src.get_product_list():
            # self.update_product_data(each_product['code'])
            self.update_product_data(each_product['code'], start_date)


def mkt_update_main():
    tw_mkt = Market()
    # product_code = "2603"
    # product_code = "0050"
    # product_code = "2727"
    # product_code = "8069"
    product_code = "3714"
    # product_code = "2330"
    # product_code = "2454"

    # print("\n## Function Test: update_product_list")
    # print("#############################################")
    # tw_mkt.update_product_list()

    print("\n## Function Test: get_product_list")
    print("#############################################")
    stock_list = tw_mkt.get_product_list()
    # for each_stock in stock_list[0:10]:
    for each_stock in stock_list:
        # print("StockID: ", each_stock['code'], ", name: ", each_stock['name'])
        print(each_stock)

    print("\n## Function Test: update_product_data")
    print("#############################################")
    tw_mkt.update_product_data(product_code)

    # print("\n## Function Test: update_all_product_data")
    # print("#############################################")
    # # tw_mkt.update_all_product_data(20200101)
    # tw_mkt.update_all_product_data(20210101)

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
    product_ins.data.pdata

    # End of test
    return

if __name__ == '__main__':
    # mkt_update_main()
    mkt_main()

