#!/bin/env python3
from utility.debug import *
# from hal_common import Stock
# from utility.common import *
from graphic.UIManager import UIManager

def UI_main():
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
