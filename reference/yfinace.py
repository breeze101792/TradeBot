import yfinance as yf

ticker = "2330.TW"  # 台積電
df = yf.download(ticker, period="8d", interval="1m")  # 過去7天，1分鐘 K 線
print(df.head())

