
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
                        ID TEXT PRIMARY KEY,
                        ProductID TEXT NOT NULL,
                        Tracking BOOLEAN NOT NULL
                    );
                    '''
        self.execute(query_str)

        # Insert Example data.
        query_str='''
                    INSERT INTO ProductTracking (ID, ProductID, Tracking)
                    VALUES ('0000', '0050.TW', TRUE);
                    '''
        self.execute(query_str)
        return True
