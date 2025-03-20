import twstock
from twstock import Stock

product_code="1240"
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
    print(twstock.codes[product_code].name)   # 列印 2330 證券名稱
    print(twstock.codes[product_code].start)  # 列印 2330 證券上市日期

    stock = Stock(product_code)
    print(stock)
    print(stock.fetch_from(2024, 3)[0:5])
def show_stock_realtime():
    stock = Stock(product_code)
    stock = twstock.realtime.get(product_code)
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
    show_stock_info()
    # show_stock_realtime()


if __name__ == "__main__":
    main()
