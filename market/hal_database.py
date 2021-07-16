from stockPool import *
from HalInterface import *

class DBSrc(DataBaseSrc):
    def __init__(self):
        self.product_list=[]
        self.database=StockPool()
        self.database.db__init()

    def __src_init(self):
        pass
    def search_product(self, query_str):
        return self.product_list[query_str]
    def get_product_info(self, product_id):
        return self.product_list[product_id]
    def get_product_list(self):
        return self.product_list
    def get_product_data_by_date(self, product_id, start_mounth, end_mounth):
        pass
    def get_product_data(self, product_id):
        pass
    def insert_product_info(self, product_id):
        pass
    def insert_product_data(self, product_id):
        pass


def db_test():
    dbsrc = DBSrc()
    print(dbsrc.get_product_info('2330'))
    print(dbsrc.get_product_data('2330'))
    # twse.search_stock()

if __name__ == '__main__':
    db_test()
