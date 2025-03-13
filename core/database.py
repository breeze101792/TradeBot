
# Local file
from utility.udb import *
from utility.debug import *

class Database(uDatabase):
    # def __init__(self):
    #     pass
    def setup_tables(self):
        dbg_info("Initiialize Tablse")

        # Stock ID
        #####################################################
        # ID, ProductID, Tracking
        # 0000, 0050.TW, True
        # query_str='''
        #             CREATE TABLE ProductTracking (
        #                 ID INTEGER PRIMARY KEY AUTOINCREMENT,
        #                 ProductID TEXT NOT NULL,
        #                 Tracking BOOLEAN NOT NULL
        #             );
        #             '''
        query_str='''
                    CREATE TABLE ProductTracking (
                            ID INTEGER PRIMARY KEY AUTOINCREMENT,
                            ProductID TEXT NOT NULL,
                            Tracking BOOLEAN NOT NULL,
                            Type TEXT NOT NULL,
                            Name TEXT NOT NULL,
                            Market TEXT NOT NULL,
                            Country TEXT NOT NULL,
                            Category TEXT NOT NULL,
                            Start DATE
                    );
                    '''
                    # INSERT INTO ProductTracking (ProductID, Tracking, Type, Name, Start, Market, category, Country) 
                    # VALUES ('2911', 1, '股票', '潤泰新', '1992-04-30', '上市', '其他業', 'TW');

        self.execute(query_str)

        # market: listed, otc, emerging

        self.add_product('2330', 'stock', '台積電', start='1993-09-05', market='listed', country='TW', category='半導體業', tracking=True)  
        self.add_product('2454', 'stock', '聯發科', start='2001-07-23', market='listed', country='TW', category='半導體業', tracking=True)  
        # self.add_product('3702', 'stock', '大聯大', start='2002-12-17', market='otc', country='TW', Category='電子通路', tracking=True)  
        # self.add_product('AAPL', 'stock', 'Apple Inc.', start='1980-12-12', market='listed', country='US', Category='科技業', tracking=True)  
        # self.add_product('TSLA', 'stock', 'Tesla Inc.', start='2010-06-29', market='listed', country='US', Category='電動車', tracking=True)  
        return True

    def add_product(self, productid, producttype, name, market, country, category = None ,start = None, tracking = True):
        # Check if the product exists
        query_str = "SELECT ID FROM ProductTracking WHERE ProductID = '{}'".format(productid)
        result = self.execute(query_str)  # Expecting a list

        if result:  # If the list is not empty, product exists
            # Update Tracking if product exists
            # query_str = "UPDATE ProductTracking SET Tracking = {} WHERE ProductID = '{}'".format(tracking, productid)
            # self.execute(query_str)
            # dbg_info(f"Updated ProductID {productid} with Tracking {tracking}")
            dbg_error(f"Fail to insert ProductID {productid} with Tracking {tracking}, already exist.")
            raise
        else:
            # Insert new product if not exist
            # query_str = "INSERT INTO ProductTracking (ProductID, Tracking) VALUES ('{}', {})".format(productid, tracking)
            query_str = f"""
                        INSERT INTO ProductTracking (ProductID, Tracking, Type, Name, Start, Market, Category, Country) 
                        VALUES ('{productid}', {tracking}, '{producttype}', '{name}', '{start}', '{market}', '{category}', '{country}');
                        """

            # new_id = self.generate_unique_id()  # Assume a function to generate unique ID
            self.execute(query_str)
            dbg_info(f"Inserted new ProductID {productid} with Tracking {tracking}")

        return True

    def update_tracking_product(self, productid, tracking = True):
        # Check if the product exists
        query_str = "SELECT ID FROM ProductTracking WHERE ProductID = '{}'".format(productid)
        result = self.execute(query_str)  # Expecting a list

        if result:  # If the list is not empty, product exists
            # Update Tracking if product exists
            query_str = "UPDATE ProductTracking SET Tracking = {} WHERE ProductID = '{}'".format(tracking, productid)
            self.execute(query_str)
            dbg_info(f"Updated ProductID {productid} with Tracking {tracking}")
        else:

            # # Insert new product if not exist
            # query_str = "INSERT INTO ProductTracking (ProductID, Tracking) VALUES ('{}', {})".format(productid, tracking)
            # # new_id = self.generate_unique_id()  # Assume a function to generate unique ID
            # self.execute(query_str)
            # dbg_info(f"Inserted new ProductID {productid} with Tracking {tracking}")
            dbg_error(f"No product found. {productid}")
            raise

        return True

    def get_tracking_product(self):
        query_str = "SELECT ProductID from ProductTracking where Tracking is TRUE;"
        data_list = self.execute(query_str)
        return data_list
