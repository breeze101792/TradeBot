# TradeBot

# ENV
```
pip install yfinance backtrader
```

# FIXME.
1. Fix hang when market.get_data, symbole not exist.
2. FIX, when insufficient money will cause add history fail.
3. Add thread lock on backtest
4. Check thread safty on strategy.
5. strategy test of last day trade.
6. broker submodule test for different provider
7. refactor broker for more general apis.
8. test code for core module.
9. avoid small amount of selling.
10. wihen date has been skiped(market not open as uasual). the update system will crsah(fail to update data, so it require every with every get_data).
11. check all buy/sell are within the min/max value of config.
12. on buy/sell, check the price, make sure we can get the real price and if not do the error handle of it.
13. On buy, we check the transaction of this stock. we want to buy the easy sell stock.
14. Seperate svc from brokermanager, so we only need to to one connect/disconnect once.

# TODO
1. on strategy, do profit check on real time.

# Actions
## First milestone
* Find way to add stock to tracking list
* Integrate to Broker to get stock info.
## 2nd milestone
* impl buy/sell api from Broker.
* impl cli interface.
* disable buy stock, only sell mode.

* Add sizer to manager cash
* Add working strateg

## Package
```
pip instasll backtrader pandas yfinance twstock lxml
```
