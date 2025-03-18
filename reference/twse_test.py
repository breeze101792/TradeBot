import twstock
from twstock import Stock
# print(twstock.codes['2330'])        # 列印 2330 證券編碼資料
# StockCodeInfo(type='股票', code='2330', name='台積電', ISIN='TW0002330008', start='1994/09/05', market='上市', group='半導體業', CFI='ESVUFR')
# twstock.codes.codes.StockCodeInfo(type='股票', code='2330', name='台積電', ISIN='TW0002330008', start='1994/09/05', market='上市', group='半導體業', CFI='ESVUFR')


# print(twstock.codes['2330'].name)   # 列印 2330 證券名稱
# print(twstock.codes['2330'].start)  # 列印 2330 證券上市日期
#
# stock = Stock('2330')
# print(stock)
# print(stock.fetch_from(2024, 3))

# >>> stock.price
# [203.5, 203.0, 205.0, 205.0, 205.5, 207.0, 207.0, 203.0, 207.0, 209.0, 209.0, 212.0, 210.5, 211.5, 213.0, 212.0, 207.5, 208.0, 207.0, 208.0, 211.5, 213.0, 216.5, 215.5, 218.0, 217.0, 215.0, 211.5, 208.5, 210.0, 208.5]
# >>> stock.capacity
# [22490217, 17163108, 17419705, 23028298, 18307715, 26088748, 32976727, 67935145, 29623649, 23265323, 1535230, 22545164, 15382025, 34729326, 21654488, 35190159, 63111746, 49983303, 39083899, 19486457, 32856536, 17489571, 28784100, 45384482, 26094649, 39686091, 60140797, 44504785, 52273921, 27049234, 31709978]
# >>> stock.data[0]
# Data(date=datetime.datetime(2017, 5, 18, 0, 0), capacity=22490217, turnover=4559780051, open=202.5, high=204.0, low=201.5, close=203.5, change=-0.5, transaction=6983)
def show_stock_list():
    # print(twstock.codes)                # 列印台股全部證券編碼資料
    for each_id in twstock.codes.keys():
        each_stock = twstock.codes[each_id]
        try:
            if each_stock.type != '股票':
                continue
            # StockCodeInfo(type='股票', code='2330', name='台積電', ISIN='TW0002330008', start='1994/09/05', market='上市', group='半導體業', CFI='ESVUFR')
            print(f"Type{each_stock.type}, code={each_stock.code}, name={each_stock.name}, start={each_stock.start}, market={each_stock.market}, group={each_stock.group}")
        except Exception as e:
            print(each_stock)
            print(e)
            break
    return

def show_stock_info():
    print(twstock.codes['2330'].name)   # 列印 2330 證券名稱
    print(twstock.codes['2330'].start)  # 列印 2330 證券上市日期

    stock = Stock('2330')
    print(stock)
    print(stock.fetch_from(2024, 3))
def show_stock_realtime():
    stock = Stock('2330')
    stock = twstock.realtime.get('2330')
    # 檢查是否成功取得資料
    if stock['success']:
        print(f"股票代號: {stock['info']['code']}")
        print(f"股票名稱: {stock['info']['name']}")
        print(f"時間: {stock['info']['time']}")
        print(f"成交價格: {stock['realtime']['latest_trade_price']}")
        print(f"開盤價: {stock['realtime']['open']}")
        print(f"最高價: {stock['realtime']['high']}")
        print(f"最低價: {stock['realtime']['low']}")
        print(f"成交量: {stock['realtime']['accumulate_trade_volume']}")

def main():
    # show_stock_list()
    # show_stock_info()
    show_stock_realtime()


if __name__ == "__main__":
    main()
