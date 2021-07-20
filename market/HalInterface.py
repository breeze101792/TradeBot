
class DataSrc:
    def __init__(self):
        self.product_list=[]
    def __fetch_product_list(self):
        pass
    def __src_init(self):
        self.__fetch_product_list()
        pass
    def search_product(self, query_str):
        return self.product_list[query_str]
    def get_product_info(self, product_id):
        return self.product_list[product_id]
    def get_product_list(self):
        return self.product_list
    def get_product_data_by_date(self, product_id, start_date):
        pass
    def get_product_data(self, product_id):
        pass

class DataBaseSrc(DataSrc):
    def __init__(self):
        self.product_list=[]
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
