from stockPool import *
from HalInterface import *

class DBSrc(DataBaseSrc):
    def __init__(self):
        self.database=StockPool()
        self.database.db__init()
        self.database.connect()
    def __del__(self):
        self.database.close()

    def __src_init(self):
        pass
    def search_product(self, query_data):
        product_info=self.database.query_for_productinfo(query_data)
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

    def insert_product_info(self, query_data):
        result = False
        for each_data in query_data:
            # print(each_data)
            result = self.database.insert_product_info(each_data)
            if result == False:
                break
        if result == True:
            self.database.commit()
        return result

    def insert_product_data(self, product_code, query_data):
        result = False
        # print(product_code, query_data)
        for each_data in query_data:
            # print(each_data)
            result = self.database.insert_historical_data(product_code, each_data)
            if result == False:
                break
        if result == True:
            self.database.commit()
        return result


def db_test():
    hal_src = DBSrc()
    product_code='2330'
    print(hal_src.get_product_list()[0:10])
    print(hal_src.search_product(product_code))
    print(hal_src.get_product_info(product_code))
    print(hal_src.get_product_data(product_code)[0])

    tmp_info=[{'code': '2330', 'name': '台積電', 'type': '股票', 'market': '上市', 'industry': '半導體業', 'startdate': '19940905'}]
    tmp_data=[{'date': '2021-05-27', 'open': 587.0, 'high': 588.0, 'low': 581.0, 'close': 585.0, 'volume': 19555305, 'turnover': 11433686898, 'trasactioncnt': 21034}]
    hal_src.insert_product_info(tmp_info)
    hal_src.insert_product_data(product_code, tmp_data)

    print(hal_src.get_product_info(product_code))
    print(hal_src.get_product_data(product_code))


if __name__ == '__main__':
    db_test()
