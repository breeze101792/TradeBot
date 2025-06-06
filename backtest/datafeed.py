import backtrader as bt

class ExtPandasDataFeed(bt.feeds.PandasData):
    lines = ('turnover',)
    params = (
        ('datetime', None),       # let backtrader auto-detect datetime
        ('open', 'Open'),
        ('high', 'High'),
        ('low', 'Low'),
        ('close', 'Close'),
        ('volume', 'Volume'),
        ('turnover', 'Turnover'),
        # ('change', 'Change'),
        # ('transaction', 'Transaction'),
        # ('openinterest', -1),     # not used
    )
