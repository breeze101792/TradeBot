from stockPool import *
from HalInterface import *

class DBSrc(DataBaseSrc):
    def __init__(self):
        self.database=StockPool()
        self.database.db__init()
        self.database.connect()

    def __src_init(self):
        pass
    def search_product(self, query_str):
        product_info=self.database.query_for_productinfo(query_str)
        return product_info
    def get_product_list(self):
        product_info_list=self.database.query_for_all_productinfo()
        return product_info_list
    def get_product_info(self, product_code):
        product_info=self.database.query_for_productinfo(product_code)
        return product_info
    def get_product_data(self, product_code):
        product_data=self.database.query_for_historicaldata(product_code)
        return product_data

    def insert_product_info(self, product_code):
        pass
    def insert_product_data(self, product_code):
        pass


def db_test():
    hal_src = DBSrc()
    product_code='2330'
    print(hal_src.get_product_list()[0:10])
    print(hal_src.search_product(product_code))
    print(hal_src.get_product_info(product_code))
    print(hal_src.get_product_data(product_code)[0])
    # twse.search_stock()

if __name__ == '__main__':
    db_test()
