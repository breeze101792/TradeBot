from market.Market import *
from market.hal_twstock import *
from market.hal_database import *

def market():
    mkt_update_main()
    mkt_main()

def hal_twstock():
    twse_dev_main()

if __name__ == '__main__':
    market()
    # hal_twstock()
