# Additional Data Sources for TradeBot — Research Report

## Current state

What you have today (from `findmind.py` provider):
- OHLC + Volume + **Turnover** + **Change** + **Transaction count** (daily)
- **Adjusted prices** (dividend/split-adjusted)
- **Market value** (daily market cap, P/E, P/B, dividend yield) — method exists
- **Capital reduction** events — method exists
- **Dividend results** — method exists
- 1,000+ stocks going back to 1994 (findmind cache has 20250620 snapshot)

What's missing that FinMind can already provide (free, you have a token in `~/.findmind.key`):
- Institutional investor flows (三大法人買賣超) — **foreign / investment trust / dealer**
- Margin trading & short sale balances
- Foreign shareholding ratios
- **Monthly revenue** (月營收) — unique TWSE signal
- Financial statements (IS / BS / CF) — quarterly
- Real dividend payment schedule
- Shareholder distribution tiers
- Trading by investor type (retail vs institutional)
- Intraday tick data (1-min K-bar)
- Index data (TAIEX, sector indices)
- Block trades / day trading data

---

## Tier 1 — Highest expected value (should get this next)

These are the datasets most likely to close the 1.3pp gap to 0050 because they capture **information that price-only signals miss**.

### 1.1 Institutional Investors Buy/Sell (三大法人買賣超)
- **Dataset**: `TaiwanStockInstitutionalInvestorsBuySell`
- **Fields**: `date, stock_id, buy, sell, name` (where `name` ∈ {`Foreign_Investor`, `Investment_Trust`, `Dealer_Self_Proprietary`})
- **History**: 2012+ on FinMind; full T86 history via TWSE since 2004
- **Cost**: Free with FinMind token
- **Update**: Daily ~14:50 GMT+8

**Why it's valuable for TradeBot**:
- Foreign investors are a major TWSE price driver (NT$523B net sold YTD on TWSE-listed shares as of 2026-05; macro-level capital flows directly affect t50 names)
- Investment trust (投信) flows are famously lead indicators — funds position before retail
- 20-day rolling sum of foreign net buy is a documented signal in TWSE quant literature

**Possible strategies**:
- Add foreign-net-buy as a 6th signal in Confluence (or replace the weakest current signal)
- "Foreign accumulation" filter: only buy when 5-day foreign net > 0
- Divergence signal: price up + foreign net down = distribution

### 1.2 Margin Purchase / Short Sale (融資融券)
- **Dataset**: `TaiwanStockMarginPurchaseShortSale`
- **Fields**: Margin buy/sell, today/yesterday balance, short sale buy/sell/balance, SBL data
- **History**: 2004+ on TWSE, 2012+ on FinMind
- **Cost**: Free
- **Update**: Daily ~21:00 GMT+8

**Why it's valuable**:
- **Margin balance change** is a strong contrary indicator — when margin balance spikes, retail is over-leveraged and a pullback is likely
- **Short sale balance ratio** (券資比) > 30% historically precedes squeeze rallies
- The 2022 bear saw margin balance drop ~40% from peak — a "wash-out" signal

**Possible strategies**:
- Avoid entries when margin balance is at 90-day high (over-leverage warning)
- Buy when券資比 (short balance / margin balance) is extreme (>30%) and price is turning up
- Use margin balance as the "exit crowd" signal — when retail is forced out, the bottom is in

### 1.3 Monthly Revenue (月營收) — unique TWSE signal
- **Dataset**: `TaiwanStockMonthRevenue`
- **Fields**: `revenue, revenue_month, revenue_year, country, create_time`
- **History**: Long (most companies go back 20+ years)
- **Cost**: Free
- **Update**: Monthly by the 10th of next month (mandatory TWSE disclosure)

**Why it's valuable**:
- **Globally unique requirement** — no other major market mandates monthly revenue
- **Pre-earnings edge**: arrives 8-10 weeks before quarterly EPS
- **FinLab's "revenue new-high + price new-high" dual-momentum strategy** historically returns **~37% annualized** with Sharpe ~1.3
- Day Ten Data's "Momo Score" (revenue acceleration + persistence + consistency) is documented to beat TWSE

**Possible strategies**:
- Revenue acceleration filter: buy only stocks where latest month revenue > 2-month rolling avg
- Revenue new-high in last 3 months AND price > SMA-50
- Combine with HPTrend: only enter on HP-confirmed uptrend AND positive revenue acceleration

---

## Tier 2 — Useful for confirmation / risk management

### 2.1 Foreign Shareholding Ratio (外資持股)
- **Dataset**: `TaiwanStockShareholding`
- **Fields**: `ForeignInvestmentShares, ForeignInvestmentSharesRatio, ForeignInvestmentRemainRatio, ForeignInvestmentUpperLimitRatio, ChineseInvestmentUpperLimitRatio, NumberOfSharesIssued`
- **Why**: Foreign ownership changes slowly — large drops signal foreign distribution. Useful for portfolio-level ranking.

### 2.2 Trading by Investor Type (投資人類別交易)
- **Dataset**: `TaiwanStockTradingDailyReportSecIdAgg` (or aggregate)
- **Fields**: per-stock `buy_volume, sell_volume, buy_price, sell_price` for each investor type
- **Why**: Distinguishes retail flow from institutional. Retail capitulation is a known bottom signal.
- **Tier**: Sponsorship/Backer in FinMind; raw T86 file from TWSE is ~NT$1,000/month

### 2.3 Real PER/PBR with dividend yield
- **Dataset**: `TaiwanStockPER` (you already have P/E, P/B, dividend_yield in `fetch_market_value`)
- **Why**: Value filter — buy stocks with P/E < 15 and P/B < 1.5 in a confirmed uptrend
- **Status**: Already implemented in findmind.py (`fetch_market_value`)

### 2.4 TAIEX / Sector Index
- **Dataset**: `TaiwanVariousIndicators5Seconds` or daily index
- **Why**: A relative-strength strategy: buy stocks outperforming TAIEX in last 20 days. This is the closest to what 0050 ETF actually does.

---

## Tier 3 — Alternative / Sentiment data (experimental, harder to use)

### 3.1 News + PTT Sentiment
- **Source**: `TaiwanStockNews` (free), PTT stock board scrapers
- **Academic evidence**: 
  - Wei, Lu, Chen, Hsu (2017) — weekly ANSI Granger-causes market returns
  - Hsieh et al. (2026) — PatchTST with sentiment: +526% cumulative, Sharpe 0.40
  - **TAIEX direction accuracy**: 87.5% (no sentiment) → 90.62% (with PTT sentiment) per Chen & Hsu 2025
- **Cost**: News free, PTT scraping needs maintenance
- **Hurdle**: Need a Chinese-language FinBERT/FinGPT for sentiment scoring — adds significant complexity
- **Verdict**: High upside, but a separate research project

### 3.2 Intraday / Tick data
- **Datasets**: `TaiwanStockPriceTick`, `TaiwanStockKBar` (1-min)
- **Tier**: Backer/Sponsor on FinMind (~$30/month); real-time 5-second snapshots are Sponsorship tier
- **Hypothetical value**: Could detect opening range breakouts, VWAP reversion, etc.
- **Verdict**: Not needed for end-of-day strategies; only valuable if switching to intraday

### 3.3 Block Trades / Day Trading
- **Datasets**: `TaiwanStockBlockTrade`, `TaiwanStockDayTrading`
- **Why**: Block trades often signal insider/private-equity positioning
- **Verdict**: Low expected value for trend-following; better for event-driven strategies

### 3.4 Tickers unavailable: 0050 ETF, Sector ETFs
- 0050 (the benchmark) is not in the findmind cache and not directly available as a stock.
- Could potentially get TAIEX index data as a proxy, or fetch 0050 from a different source.

---

## Where the gap to 0050 is most likely closed

The 1.3pp gap to 0050's 15.52% 5y avg is structural:
- 0050 is cap-weighted (heavy 2330 / 2454 / 2308)
- 2024 AI rally rewarded high-multiple tech that HPTrend's 12% stop took profits on

The cheapest way to close it isn't cap-weighting (architectural) but **adding fundamental timing** to entries:

| Approach | Expected gain | Difficulty |
|---|---|---|
| Add monthly revenue acceleration filter to HPTrend | +0.5-1pp | Low (free data, simple filter) |
| Add foreign net-buy as confirmation signal | +0.3-0.5pp | Low (free data, single threshold) |
| Replace dualthrust/PSAR strategies with revenue-momentum variants | +0.5-1pp | Medium |
| Cap-weight the portfolio (mirror 0050 weights) | +1-1.5pp | High (architectural) |
| News/PTT sentiment | +0.3-0.5pp | Very High (NLP pipeline) |

**Recommendation**: Start with **monthly revenue** and **institutional investors** — both are free, both have documented backtest evidence on TWSE, and both address a different dimension than your current price-only signals.

---

## Implementation sketch

### Add Institutional flow provider (mirroring `findmind.py`)

```python
# market/provider/findmind_institutional.py
def fetch_institutional_investors(self, stock_id, start_date, end_date):
    """Fetches TaiwanStockInstitutionalInvestorsBuySell for a single stock."""
    api_url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": stock_id,
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d'),
    }
    # ... same auth pattern as fetch_capital_reduction_data
    # Returns DataFrame: date, stock_id, buy, sell, name
```

### Add monthly revenue

```python
def fetch_monthly_revenue(self, stock_id, start_date, end_date):
    """Fetches TaiwanStockMonthRevenue for a single stock."""
    params = {"dataset": "TaiwanStockMonthRevenue", "data_id": stock_id, ...}
    # Returns DataFrame: date, stock_id, country, revenue, revenue_month, revenue_year
    # Compute: revenue YoY%, MoM%, 2-month MA, 12-month high
```

### Sample strategy: `RevenueMomentum`

```python
class RevenueMomentumStrategy(MovingProfitStrategy):
    """HPTrend gated by positive monthly revenue acceleration.

    Entry: HP trend rising (slope > 0) AND latest monthly revenue >
           2-month rolling average AND latest revenue > 1 year ago.
    Exit: HP slope turns negative OR trailing stop hit.
    """
    NAME = "RevMomentum"
    # ... store revenue history per data feed ...
    # ... update in next() ...
```

---

## Sources

### FinMind / TWSE / TEJ
- [FinMind Documentation](https://finmind.github.io/) — main API reference
- [FinMind GitHub](https://github.com/FinMind/FinMind) — Python SDK + dataset list
- [FinMind Technical docs](https://finmind.github.io/tutor/TaiwanMarket/Technical/) — tick / 1-min K / order book
- [FinMind Fundamental docs](https://finmind.github.io/tutor/TaiwanMarket/Fundamental/) — PER/PBR/revenue/financials
- [FinMind llms.txt](https://finmind.github.io/llms-full.txt) — machine-readable dataset list
- [TEJ API docs](https://api.tej.com.tw/documents.html) — paid alternative
- [clarifindata GitHub](https://github.com/AChao0212/clarifindata) — open-source Taiwan pipeline

### TWSE official products
- [TWSE Data E-Shop — Institutional Investors](https://eshop.twse.com.tw/en/product/detail/a3817fe0ef1540488238ca92a35f4002) — official T86 source
- [TWSE Data E-Shop — Margin Summary](https://eshop.twse.com.tw/en/product/detail/b97250fdaacf42a299612595781e0eea)
- [TWSE Data E-Shop — Daily Short Sale](https://eshop.twse.com.tw/en/product/detail/000000006e0bbe8d016f183dc3be033a)
- [TPEx Margin Portal](https://wwwov.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal.php?l=en-us)
- [Taiwan Government Open Data — Credit trading](https://data.gov.tw/en/datasets/20210)
- [OpenDataTW — Monthly Revenue](https://opendatatw.org/dataset/18420)

### Quant research
- [Day Ten Data — Monthly Revenue Edge](https://daytendata.com/)
- [FinLab — 月營收選股 strategy](https://www.finlab.tw/revenue_and_price_engine_strategy/)
- [TEJ — Jabli-Watson Factor Model](https://www.tejwin.com/en/insight/jabli-watson-factor-model-the-growth-formula-for-quantitative-momentum-investing/)
- [Apify TWSE Institutional API](https://apify.com/chamarix/twse-institutional-trades)
- [MacroMicro — TWSE Foreign Net Buy tracker](https://en.macromicro.me/series/652/net-amount-foreign-investor)

### Sentiment / NLP research
- [Chou, Chen & Lee 2025 — News sentiment & attention on TWSE](https://eduweb.sfi.org.tw/download/resh_ftp/periodical/02-203-145-1.pdf)
- [Wei et al. 2017 — Aggregate News Sentiment Index](https://www.sciencedirect.com/science/article/abs/pii/S106294081630122X)
- [Chen & Hsu 2025 — Taiwan FinBERT + CNN-BiLSTM-SA](https://link.springer.com/article/10.1007/s10791-025-09515-3)
- [Hsieh et al. 2026 — Sentiment-Augmented RNN for Mini-TAIEX Futures](https://www.mdpi.com/1999-4893/19/1/69)
