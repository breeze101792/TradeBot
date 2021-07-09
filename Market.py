# Nead to add additional info
from common import *
from debug import *
from stockPool import *
from HalInterface import *

class Market(DataSrc):
    def __init__(self):
        pass
    def search_product(self, query_str):
        stockid = StockID(2454, "Mediatek")
        return stockid

    def get_product_list(self):
        stock_list=[]
        stockid = StockID(2454, "Mediatek")
        stock_list.append(stockid)
        stockid = StockID(2330, "TSMC")
        stock_list.append(stockid)
        return stock_list

    # def get_stock_info(self, stockID, startDate = -1, endDate = -1):
    #     return [[1,2,3,4],[5,6,7,8],[9,10,11,12,13]]
    def get_product_data(self, stockID, startDate = -1, endDate = -1):
        return [[1,2,3,4],[5,6,7,8],[9,10,11,12,13]]

def mkt_main():
    tw_mkt = Market()
    stockid = tw_mkt.search_product("Mediatek")
    print("StockID: ", stockid)

    print("## Function Test: search_product")
    print("#############################################")
    stock_str = "2454"
    stock_id = tw_mkt.search_product(stock_str.__str__())
    print("Stock: ", stock_id)

    print("\n## Function Test: get_stock_info")
    print("#############################################")
    stock_list = tw_mkt.get_product_list()
    for each_stock in stock_list:
        print("StockID: ", each_stock)

    print("\n## Function Test: get_product_data")
    print("#############################################")
    stock_str = "2454"
    stock_id = tw_mkt.search_product(stock_str.__str__())
    print("Stock: ", stock_id)
    stock_data = tw_mkt.get_product_data(stock_id)

if __name__ == '__main__':
    mkt_main()


# import urllib.request, json, urllib
# import base64
# class StockID:
#     code = None
#     name = None
#     def __init__(self, code=None, name=None):
#         self.code = code
#         self.name = name
#     def __str__(self):
#         return "{}({})".format(self.name, self.code)

#class Stock:
#    def __init__(self):
#        self.web_url = None
#        pass
#    def __connect(self):

#        pass
#    def search_stock(self, stock_name):
#        # stock_name is string, could be name or stock code
#        stock_list = []
#        web_url = "http://mis.tse.com.tw/stock/api/getStockNames.jsp?n={}".format(urllib.parse.quote(stock_name))
#        with urllib.request.urlopen(web_url) as url:
#            json_data = json.loads(url.read().decode())
#            dbg_debug(json_data['rtcode'])
#            if json_data['rtcode'] != "0000":
#                return RetValue.error
#            dbg_debug(json_data['datas'][0]['n'])
#            if json_data['datas'][0]['c'] == stock_name or json_data['datas'][0]['n'] == stock_name:
#                stock_list.append(StockID(json_data['datas'][0]['c'], json_data['datas'][0]['n']))
#                return stock_list

#            for each_stock in json_data['datas']:
#                stock_list.append(StockID(each_stock['c'], each_stock['n']))

#        return stock_list
#    def get_stock_info(self, stock_id):
#        # stock_id is class stockID
#        stock_list = []
#        # 
#        web_url = "http://mis.tse.com.tw/stock/api/getStock.jsp?ch={}.tw&json={}".format(stock_id.code, 1)
#        dbg_debug(web_url)
#        with urllib.request.urlopen(web_url) as url:
#            json_data = json.loads(url.read().decode())
#            dbg_debug(json_data['rtcode'])
#            print(json_data)
#            if json_data['rtcode'] != "0000":
#                return RetValue.error
#        pass


