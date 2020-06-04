import numpy as np
from debug import *
from datatype import *

class Stock:
    def __init__(self):
        pass
    def search(self, target_str):
        # Return Stock basic info
        return StockID("2454", "MediaTek")
    def get_data(self, stock_id, start_date=None, end_date=None):
        # Get StockID
        # Return raw data with [[1, 2, 3, 4], [5, 6, 7, 8]]
        # handle the missing date
        dbg_info(stock_id.name, "(", stock_id.code, ")")
        result = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [1, 2, 3, 4], [5, 6, 7, 8]])
        dbg_debug("Data:\n", result)
        return result

