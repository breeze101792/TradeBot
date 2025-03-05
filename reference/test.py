import yfinance
# import pandas as pd
# import datetime as dt

stock_id = '0050.TW'
data = yfinance.Ticker(stock_id)
df = data.history(period="max")
print(df)
