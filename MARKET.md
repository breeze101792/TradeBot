# MARKET.md — Data Source Evaluation

**Status**: Working doc. Last audit run 2026-06-14.
**Source of truth**: `lab/data_availability_audit.py` (raw CSV samples and
`report.md` in `/tmp/claude-1000/data_audit_<ts>/`).
**Goal**: Decide which data sources to integrate into TradeBot's
strategy / trading pipeline to close the 1.3pp gap to 0050 ETF.

This document is a **decision log** (what we use, why, expected value).
The implementation reference for providers lives in
[`docs/market-data.md`](docs/market-data.md). The long-form research
notes live in [`DATA_RESEARCH.md`](DATA_RESEARCH.md).

---

## 1. What we already have

OHLCV + Turnover + Change + Transaction count, daily, going back to
~1994 for 1,000+ TWSE/TPEx names. This is the only input every
existing strategy (HPTrend, KeltnerHP, Confluence, etc.) consumes.

| What | Source | Status |
|---|---|---|
| OHLCV (raw) | FinMind `TaiwanStockPrice` | ✓ live, in cache |
| OHLCV (dividend/split-adjusted) | FinMind, manually adjusted in `findmind.py::fetch_adjusted_data` | ✓ live, in cache |
| Market cap + P/E + P/B + dividend yield | FinMind `TaiwanStockMarketValue` | ⚠ endpoint exists but the audit probe hit `NET_ERROR` on the run; `fetch_market_value` is implemented but the dataset returns 0 rows on `data_id=2330` recently — needs follow-up |
| TAIEX total-return index | FinMind `TaiwanStockTotalReturnIndex` | ✓ live |

**Important**: the only data we *actually use* today for trading
decisions is **OHLCV**. Everything else (PER/PBR, market cap,
institutional flows, margin balance) is in cache or fetchable but
**no strategy consumes it**. That is the gap.

---

## 2. Data audit (probed 2026-06-14, free tier)

The full comparison table:

| # | Dataset | Source | Cost | Tier | Status | Rows (1y) | Latency | What it gives us |
|---|---|---|---|---|---|---|---|---|
| 1 | Institutional investors (三大法人) | FinMind | free | **1** | ✓ OK | 1,215 | 13.9s | Foreign / Trust / Dealer net buy, daily |
| 2 | Margin + short balance (融資融券) | FinMind | free | **1** | ✓ OK | 243 | 10.0s | Retail leverage gauge |
| 3 | Monthly revenue (月營收) | FinMind | free | **1** | ✓ OK | 12 | 11.5s | **Unique TWSE fundamental signal** |
| 4 | Foreign shareholding % (外資持股) | FinMind | free | 2 | ✓ OK | 245 | 18.5s | Slow-moving positioning |
| 5 | PER/PBR/dividend yield | FinMind | free | 2 | ✓ OK | 243 | 9.5s | Already implemented, needs re-probe |
| 6 | Financial statements (IS/BS/CF) | FinMind | free | 2 | ✓ OK | 68 | 11.4s | Quarterly fundamentals |
| 7 | Dividend announcement (ex-div schedule) | FinMind | free | 2 | ✓ OK | 4 | 9.2s | Real ex-div dates (not just announcement) |
| 8 | TAIEX total-return index | FinMind | free | 2 | ✓ OK | 243 | 19.9s | Buy-and-hold benchmark |
| 9 | Shareholder distribution (1-999 / 1000+ tiers) | FinMind | free | 2 | ✗ NET_ERROR | — | 15.3s | Retail-vs-institutional breakdown |
| 10 | Trading by investor type (aggregate) | FinMind | **Backer ~$30/mo** | 2 | ✗ NET_ERROR (free-tier gated) | — | 28.0s | Per-investor-type flow |
| 11 | Market cap daily | FinMind | free | 2 | ✗ NET_ERROR (intermittent) | — | 10.4s | Already in `fetch_market_value` |
| 12 | News headlines | FinMind | free (rate-limited) | 3 | ✗ NET_ERROR | — | 17.2s | NLP-sentiment candidate |
| 13 | Tick-level trades | FinMind | **Backer+** | 3 | ✗ NET_ERROR (free-tier gated) | — | 13.7s | Intraday microstructure |
| 14 | 1-minute K-bar | FinMind | **Sponsor ~$100/mo** | 3 | ✗ NET_ERROR (free-tier gated) | — | 8.5s | Intraday signals |
| 15 | US Insider sentiment | Finnhub | needs API key | 3 | ✗ NO_KEY | — | — | US-only reference |

**Pacing note**: FinMind's free tier throttles aggressively under
concurrent load. The audit was redesigned to pace calls at 2s with
60s timeouts (see `lab/data_availability_audit.py:65-77`). Real
production integration must do the same — see §5.

---

## 3. International comparison (for context)

| Dataset | Taiwan (TWSE) | Japan (TSE) | US (NYSE/Nasdaq) |
|---|---|---|---|
| Institutional investors | ✓ FinMind free, daily | ✓ J-Quants ¥3,300/mo | ✓ SEC 13F quarterly, free (45-day delay) |
| Margin + short | ✓ FinMind free, daily | ✓ J-Quants Standard | ~ FINRA short interest bi-monthly, no clean API |
| **Monthly revenue** | ✓ **UNIQUE to TWSE** | ✗ Not mandatory (quarterly only) | ✗ Not disclosed (10-Q quarterly only) |
| Per-investor-type trades | ✓ FinMind Backer tier | ✓ J-Quants Standard | ✓ Form 4 insider (EDGAR) |
| 13F-equivalent | n/a | n/a | ✓ 13F itself is the gold standard |

**Key insight**: Taiwan is the only major market with mandatory
monthly revenue disclosure. **No equivalent signal exists in JP or
US.** This is a structural edge for any strategy that uses revenue
as a fundamental-timing filter.

---

## 4. Recommendation: what to integrate

### Tier 1 (integrate now — high expected value, all free)

| Dataset | Expected gain | Why | Effort |
|---|---|---|---|
| **Monthly revenue** (月營收) | +0.5–1.0pp | Unique TWSE signal; FinLab's "revenue new-high + price new-high" historically 37% CAGR; arrives 8–10 weeks before quarterly EPS | Low — single dataset, one new method |
| **Institutional investors** (三大法人) | +0.3–0.5pp | Foreign net-buy is a documented TWSE lead indicator; investment trust (投信) flows are famously predictive | Low — single dataset, one new method |
| **TAIEX total-return index** | benchmark | Closest available proxy for 0050 buy-and-hold (0050 isn't directly in FinMind). Useful for relative-strength strategies and as a sanity check | Trivial — already a single endpoint |

### Tier 2 (integrate when Tier 1 pays off)

| Dataset | Expected gain | Why | Effort |
|---|---|---|---|
| Foreign shareholding % (外資持股) | +0.2–0.4pp | Slow-moving; good for portfolio-level ranking, not entry timing | Low |
| PER/PBR/dividend yield | +0.2–0.3pp | Value filter; already implemented in `fetch_market_value` but not consumed | Low |
| Financial statements | +0.3–0.5pp | Quarterly IS/BS/CF — deep fundamental signals (ROE, accruals) | Medium — needs derived ratios |

### Tier 3 (skip — insufficient evidence or effort too high)

| Dataset | Why skip |
|---|---|
| News / PTT sentiment | Needs Chinese FinBERT/FinGPT pipeline; +0.3–0.5pp upside but weeks of work |
| Tick / 1-min K-bar | Requires paid tier; trend-following on EOD is structurally weaker only in 1% of regimes |
| US Finnhub insider | Not relevant for TWSE strategies; needs API key + account |

### Skipped on cost/availability

| Dataset | Why |
|---|---|
| Trading by investor type | Backer tier ($30/mo); not enough expected value to justify cost |
| Shareholder distribution | NET_ERROR on free tier; re-test if we upgrade |
| Market cap daily | Already implemented in `fetch_market_value`; intermittent failure — needs caching layer |

---

## 5. Implementation plan (Tier 1)

### 5.1 New `FindMind` methods

Add three methods to `market/provider/findmind.py`, following the
same pattern as the existing `fetch_market_value` and
`fetch_capital_reduction_data`:

```python
def fetch_institutional_investors(self, stock_id, start_date, end_date)
    """TaiwanStockInstitutionalInvestorsBuySell → DataFrame
    indexed by date with columns:
    Foreign_Investor_buy/sell/net,
    Investment_Trust_buy/sell/net,
    Dealer_self_buy/sell/net,
    Dealer_Hedging_buy/sell/net,
    Foreign_Dealer_Self_buy/sell/net."""

def fetch_monthly_revenue(self, stock_id, start_date, end_date)
    """TaiwanStockMonthRevenue → DataFrame indexed by date with
    columns: revenue (raw NT$), revenue_yoy, revenue_mom, revenue_period."""

def fetch_taiex_index(self, start_date, end_date)
    """TaiwanStockTotalReturnIndex (data_id='TAIEX') → DataFrame
    indexed by date with column 'price'."""
```

Reference implementation lives in `lab/fetch_stock_extra.py:67-176`
as a standalone prototype.

### 5.2 Pacing / caching

FinMind free tier is 600 req/hr. For t50 + 5y backtest:
- Institutional: 5y × 250d × 50 stocks = 62,500 rows. With caching, 50 API calls (one per stock) = OK.
- Revenue: 5y × 12m × 50 stocks = 3,000 rows. 50 API calls. OK.
- TAIEX: 1 call, 5y × 250d = 1,250 rows.

Add a 1.5s delay between calls and use the existing per-stock CSV
cache layout under `~/.config/investment/data/findmind/extras/`.

### 5.3 New strategies (TBD after data lands)

Two candidates to backtest once data is cached:

1. **`InstFlow`**: HP-confirmed uptrend AND 5-day foreign net buy > 0.
2. **`RevMomentum`**: HP-confirmed uptrend AND latest monthly revenue > 2-month rolling average AND latest revenue > 1 year ago (positive YoY).
3. **`InstRevGated`**: Both above — HP trend AND positive foreign flow AND positive revenue MoM.

Expected ranking (predicted, not measured):
`HPTrend` (current best 14.23%) ≤ `InstFlow` ≤ `RevMomentum` ≤ `InstRevGated` ≤ 0050 (15.52%).

If `InstRevGated` clears 15.5% on 5y t50, we've closed the gap.

---

## 6. Open questions / follow-ups

- [ ] **Market cap daily NET_ERROR**: is `TaiwanStockMarketValue` free-tier or paid? Re-probe with smaller window.
- [ ] **Why is `TradingDailyReportSecIdAgg` NET_ERROR on free tier?** The `Backer` description says it requires Backer; verify pricing page.
- [ ] **Can we get 0050 directly?** Currently no — FinMind's ETF list (we filter them out in `findmind.py:124-129`). If we want a 0050 benchmark column for the report, fetch it via `taiwan_etf_daily` or pull from `twstock`.
- [ ] **Revenue acceleration stability**: is MoM or YoY more predictive? Need to backtest both.
- [ ] **Backtest in-sample vs out-of-sample**: use 2010-2014 + 2015-2019 to train, 2020-2024 to test the new strategies.

---

## 7. Changelog

| Date | Change | Author |
|---|---|---|
| 2026-06-14 | Initial audit + decision doc | audit + this file |
| 2026-06-14 | Moved scripts to `lab/` | session |
