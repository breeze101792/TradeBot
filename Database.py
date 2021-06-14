import sqlite3
import os


class StockPool:
    __db_lock = False
    __db_connection = None
    __cursor = None
    __db_path = "./stockpool.db"
    def db__init(self):
        if not os.path.isfile(self.__db_path):
            conn = sqlite3.connect(self.__db_path)
            c = conn.cursor()
            # Create table
            # c.execute('''CREATE TABLE WORD
            #              (word text, times real, familiar real)''')
            # info table
            c.execute('''CREATE TABLE Info
                         (StockID text NOT NULL, Name text)''')

            # Historical Data
            c.execute('''CREATE TABLE HistoricalData
                         (StockID text NOT NULL, Date date, Open int, High int, Low int, Close int, Volume int)''')

            # Insert testing data
            c.execute("INSERT INTO Info VALUES ('0','TEST')")
            c.execute("INSERT INTO HistoricalData VALUES ('0', '2021-06-01', 100, 108, 94, 95, 10000)")

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
    def query_for_all_stock(self):
        if self.__is_locked():
            # print('db is locked')
            return False
        else:
            self.__lock()
            query_str = """SELECT * FROM Info;"""
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
    # pass---------------------------------------------------
    # def get_word(self, word):
    #     if self.__is_locked():
    #         # print('db is locked')
    #         return False
    #     else:
    #         self.__lock()
    #         query_str = "SELECT times, familiar FROM WORD WHERE word == '%s'" % word
    #         result = self.__cursor.execute(query_str)
    #         self.__unlock()
    #         ret_data = result.fetchall()
    #         if len(ret_data) != 0:
    #             return ret_data[0]
    #         else:
    #             return False
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
    # def insert(self, word, familiar = 0):
    #     query_str = "SELECT word FROM WORD WHERE word == '%s'" % word
    #     # print(query_str)
    #     if self.__is_locked():
    #         # print('db is locked')
    #         return False
    #     else:
    #         self.__lock()
    #         result = self.__cursor.execute(query_str).fetchone()
    #         # print(result)
    #         if result is not None:
    #             # word is already in the wordbank
    #             self.__unlock()
    #             return False
    #         else:
    #             query_str = "INSERT INTO WORD (word, times, familiar) VALUES ('%s', %i, %i)" % (word, 1, familiar)
    #             # print(query_str)
    #             result = self.__cursor.execute(query_str).fetchone()
    #         self.__unlock()
    #         return result #.fetchone()
    # def update_familiar(self, word, familiar = 0):
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
    #             query_str = "UPDATE WORD SET familiar = %i WHERE word == '%s'" % (familiar, word)
    #             result = self.__cursor.execute(query_str).fetchone()
    #         self.__unlock()
    #         return True

def db_main():
    test = StockPool()
    test.db__init()
    test.connect()
    # test.insert('test')
    # print(test.update('test', 1))
    print(test.query_for_all_stock())
    print(test.query_for_all_historicaldata())
    test.close()
if __name__ == '__main__':
    db_main()
