#!/bin/env python3
from optparse import OptionParser
from datetime import datetime, date, timedelta
from utility.debug import *
# from hal_common import Stock
# from utility.common import *
flag_gui_enable=True
try:
    from gui.UIManager import UIManager
    from market.Market import *
except:
    dbg_debug("No GUI Running")
    flag_gui_enable=False

def UI_main():
    window = UIManager()
    window.ui_start()

def update_all_product_data(product_id, date):
    mkt = Market()
    mkt.update_product_list()
    mkt.update_all_product_data(date)

def update_product_data(product_id, date):
    mkt = Market()
    mkt.update_product_data(product_id, date)

def get_product_list():
    mkt = Market()
    product_list = mkt.get_product_list()
    for each_product in product_list:
        print(each_product)
    print("Total :", len(product_list))


def main():
    # dbg_info("Investor")
    parser = OptionParser()
    parser.add_option("-g", "--graphic", action="store_true",
        dest="action_launch_graphic", default=False,
        help="Launch Graphic Interface")
    parser.add_option("-u", "--update-db", action="store_true",
        dest="action_update_db", default=False,
        help="Update online data to local db")
    parser.add_option("-d", "--update-date", action="store",
        dest="update_date", default=0,
        help="Specify date that you want to from")
    parser.add_option("-p", "--product", action="store",
        dest="product_code", default=None,
        help="Update indivisual product data. Please specify product code.")
    parser.add_option("--product-list", action="store_true",
        dest="product_list", default=False,
        help="Print all product list")

    (options, args) = parser.parse_args()

    if options.action_update_db==True:
        if options.product_code is None:
            dbg_info("action_update_db")
            dbg_info("Not Implement yet!")
            update_all_product_data(int(options.update_date))
        elif options.product_code is not None:
            dbg_info("product_code")
            update_product_data(options.product_code, int(options.update_date))
    elif options.product_list==True:
        dbg_info("product_list")
        get_product_list()
    elif options.action_launch_graphic==True:
        dbg_info("action_launch_graphic")
        if flag_gui_enable == True:
            UI_main()
        else:
            dbg_error("Can't start gui")
    else:
        dbg_info("Default Action")
        if flag_gui_enable == True:
            UI_main()
        else:
            dbg_info("Will run cli")

if __name__ == '__main__':
    main()
