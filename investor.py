#!/bin/env python3
from debug import *
from hal_common import Stock
from common import *

def UI_main():
    from UIManager import UIManager
    window = UIManager()        
    window.ui_start()

def main():
    dbg_info("Investor")
    UI_main()
    # template_sotck = Stock()
    # ret_stock = template_sotck.search("test")
    # template_sotck.get_data(ret_stock)

if __name__ == '__main__':
    main()
