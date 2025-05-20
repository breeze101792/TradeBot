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
