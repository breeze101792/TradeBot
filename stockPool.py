import sqlite3
import os

class StockPool:
    __db_lock = False
    __db_connection = None
    __cursor = None
    __db_path = "./testdb.db"
    def db__init(self):
        if not os.path.isfile(self.__db_path):
            conn = sqlite3.connect(self.__db_path)
            c = conn.cursor()
            # Create table
            # c.execute('''CREATE TABLE WORD
            #              (word text, times real, familiar real)''')
            # info table
            c.execute('''CREATE TABLE ProductInfo
                         (ID int NOT NULL, Code text NOT NULL, Name text, Type text, Market text, Industry text, StartDate date)''')

            # Historical Data
            c.execute('''CREATE TABLE HistoricalData
                         (ID int NOT NULL, Date date, Open int, High int, Low int, Close int, Volume int, Turnover int, TransactionCnt int)''')

            # Insert testing data
            # c.execute("INSERT INTO ProductInfo VALUES (0, '0','TEST','股票', '上市', '測試')")
            # c.execute("INSERT INTO HistoricalData VALUES (0, '2021-06-01', 100, 108, 94, 95, 10000, 20301841661, 20097)")

            # Save (commit) the changes
            conn.commit()

            # We can also close the connection if we are done with it.
            # Just be sure any changes have been committed or they will be lost.
            conn.close()
            # print('successful init')
    def __lock(self):
        if self.__db_lock == False:
            self.__db_lock = True
            return True
        else:
            return False
    def __unlock(self):
        if self.__db_lock == True:
            self.__db_lock = False
            return True
        else:
            return False
    def __is_locked(self):
        return self.__db_lock
    def __generate_id(self, product_id):
        return product_id
    def connect(self):
        if self.__is_locked():
            # print("Database is locked!")
            return False
        elif self.__db_connection is None:
            self.__lock()
            self.__db_connection = sqlite3.connect(self.__db_path)
            self.__cursor = self.__db_connection.cursor()
            self.__unlock()
            return True
        else:
            # print("Database is already connected!")
            return True
    def close(self):
        if self.__db_lock:
            # print('database is locked!\n please unlocked first!')
            return False
        elif self.__db_connection is None:
            # print('there is nothing to do!')
            return True
        else:
            self.commit()
            self.__db_connection.close()
            return True
    def commit(self):
        if self.__is_locked():
            # print('db is locked')
            return False
        else:
            # print('sent commit')
            self.__db_connection.commit()
            return True
    def query_for_all_product(self):
        if self.__is_locked():
            # print('db is locked')
            return False
        else:
            self.__lock()
            query_str = """SELECT * FROM ProductInfo;"""
            result = self.__cursor.execute(query_str)
            self.__unlock()
            return result.fetchall()
    def query_for_all_historicaldata(self):
        if self.__is_locked():
            # print('db is locked')
            return False
        else:
            self.__lock()
            query_str = """SELECT * FROM HistoricalData;"""
            result = self.__cursor.execute(query_str)
            self.__unlock()
            return result.fetchall()
    def insert_product_info(self, product_code, insert_data):
        if insert_data is None:
            return False
        # (ID int NOT NULL, Code text NOT NULL, Name text, Type text, Market text, Industry text, StartDate date)
        # {'code': '2330', 'name': '台積電', 'type': '股票', 'market': '上市', 'industry': '半導體業', 'startdate': '19940905'}
        query_str = "SELECT Code FROM ProductInfo WHERE Code == '%s'" % product_code
        # print(insert_data)
        if self.__is_locked():
            # print('db is locked')
            return False
        else:
            self.__lock()
            result = self.__cursor.execute(query_str).fetchone()
            # print(result)
            if result is not None:
                # word is already in the wordbank
                self.__unlock()
                return False
            else:
                tmp_id=self.__generate_id(insert_data['code'])
                query_str = "INSERT INTO ProductInfo (ID, Code, Name, Type, Market, Industry, StartDate) VALUES ('%s','%s','%s','%s','%s','%s','%s')" % (tmp_id, insert_data['code'], insert_data['name'], insert_data['type'], insert_data['market'], insert_data['industry'], insert_data['startdate'])
                # print(query_str)
                result = self.__cursor.execute(query_str).fetchone()
            self.__unlock()
            return result #.fetchone()
    def insert_historical_data(self, product_code, insert_data):
        if insert_data is None:
            return False
        # (ID int NOT NULL, Date date, Open int, High int, Low int, Close int, Volume int, Turnover int, TransactionCnt int)
        # {'date': '2021-05-26', 'open': 587.0, 'high': 588.0, 'low': 581.0, 'close': 585.0, 'volume': 19555305, 'turnover': 11433686898, 'trasactioncnt':
        tmp_id=self.__generate_id(product_code)
        query_str = "SELECT ID FROM HistoricalData WHERE ID == '%s' and Date == '%s'" % (tmp_id, insert_data['date'])
        # print(insert_data)
        if self.__is_locked():
            # print('db is locked')
            return False
        else:
            self.__lock()
            result = self.__cursor.execute(query_str).fetchone()
            # print(result)
            if result is not None:
                # word is already in the wordbank
                self.__unlock()
                return False
            else:
                query_str = "INSERT INTO HistoricalData (ID, Date, Open, High, Low, Close, Volume, Turnover, TransactionCnt) VALUES ('%s','%s','%s','%s','%s','%s','%s','%s','%s')" % (tmp_id, insert_data['date'], insert_data['open'], insert_data['high'], insert_data['low'], insert_data['close'], insert_data['volume'], insert_data['turnover'], insert_data['trasactioncnt'])
                # print(query_str)
                result = self.__cursor.execute(query_str).fetchone()
            self.__unlock()
            return result #.fetchone()

    # def update(self, word, times = 1, familiar = 0):
    #     query_str = "SELECT times, familiar FROM WORD WHERE word == '%s'" % word
    #     if self.__is_locked():
    #         # print('db is locked')
    #         return False
    #     else:
    #         self.__lock()
    #         result = self.__cursor.execute(query_str).fetchone()
    #         if result is None:
    #             self.__unlock()
    #             return False
    #         else:
    #             query_str = "UPDATE WORD SET times = %i, familiar = %i WHERE word == '%s'" % (result[0] + times, result[1] + familiar, word)
    #             result = self.__cursor.execute(query_str).fetchone()
    #         self.__unlock()
    #         return result #.fetchone()

def db_main():
    pool = StockPool()
    pool.db__init()
    pool.connect()
    # pool.insert('pool')
    # print(pool.update('pool', 1))
    print(pool.query_for_all_product())
    print(pool.query_for_all_historicaldata())
    tmp_info={'code': '2330', 'name': '台積電', 'type': '股票', 'market': '上市', 'industry': '半導體業', 'startdate': '19940905'}
    tmp_data={'date': '2021-05-26', 'open': 587.0, 'high': 588.0, 'low': 581.0, 'close': 585.0, 'volume': 19555305, 'turnover': 11433686898, 'trasactioncnt': 21034}
    print(pool.insert_product_info(tmp_info['code'],tmp_info))
    print(pool.insert_historical_data(tmp_info['code'],tmp_data))

    print(pool.query_for_all_product())
    print(pool.query_for_all_historicaldata())
    pool.close()

if __name__ == '__main__':
    db_main()

