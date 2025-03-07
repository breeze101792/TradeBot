
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
        query_str='''
                    CREATE TABLE ProductTracking (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        ProductID TEXT NOT NULL,
                        Tracking BOOLEAN NOT NULL
                    );
                    '''
        self.execute(query_str)

        self.add_tracking_product('0050.TW', True)
        self.add_tracking_product('0056.TW', False)
        return True

    def add_tracking_product(self, productid, tracking = True):
        # Check if the product exists
        query_str = "SELECT ID FROM ProductTracking WHERE ProductID = '{}'".format(productid)
        result = self.execute(query_str)  # Expecting a list

        if result:  # If the list is not empty, product exists
            # Update Tracking if product exists
            query_str = "UPDATE ProductTracking SET Tracking = {} WHERE ProductID = '{}'".format(tracking, productid)
            self.execute(query_str)
            dbg_info(f"Updated ProductID {productid} with Tracking {tracking}")
        else:
            # Insert new product if not exist
            query_str = "INSERT INTO ProductTracking (ProductID, Tracking) VALUES ('{}', {})".format(productid, tracking)
            # new_id = self.generate_unique_id()  # Assume a function to generate unique ID
            self.execute(query_str)
            dbg_info(f"Inserted new ProductID {productid} with Tracking {tracking}")

        return True

    def get_tracking_product(self):
        query_str = "SELECT ProductID from ProductTracking where Tracking is TRUE;"
        data_list = self.execute(query_str)
        return data_list
