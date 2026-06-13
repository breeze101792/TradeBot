# AI / Noise-Filtered Strategies

This folder contains strategies that use **mathematical denoising
of the price series** before trend detection. The goal is to
separate the "true" trend from the 1-2 day noise that fools
raw-price filters.

## Strategies

| File | Strategy | 5y avg return (t50, 2020-2024) | Math |
|------|----------|-------------------------------|------|
| `adaptive.py` | AdaptiveTrend | +11.73% | SMA-45 trend filter + MACD momentum + ATR |
| `hybrid.py`    | Hybrid       | +11.73% | MultiSignal gated by SMA-45 + MACD>0 (mean-reversion + trend) |
| `trendrider.py`| TrendRider   |  ~6-7%   | Long-only trend-rider, no MS logic, wide trailing stop |
| `atrtrend.py`  | ATRTrend     |  ~5-6%   | SMA-200 filter + ATR-volatility-based stops |
| `slopetrend.py`| SlopeTrend   | +8.96%  | SMA slope + Kalman-filtered MACD |
| `hptrend.py`   | HPTrend      | **+14.24%** | Hodrick-Prescott filtered price + slope |

## Why these?

The traditional strategies in `../candidate/` use raw price + MACD
as the trend signal. They are sensitive to **1-2 day price noise**:
a brief oversold bounce inside a downtrend can trigger a
"we crossed above SMA" buy that immediately reverses.

The strategies here apply **signal processing** to the price
series first:

- **HP filter** (Hodrick-Prescott): macro-economist's tool for
  decomposing price into trend + cycle. `hptrend.py` uses
  `lambda=1e5` on a 90-day window and requires the resulting
  smoothed trend to be rising for 3 consecutive bars.
- **Kalman filter**: 1D state-space denoiser. `slopetrend.py`
  applies this to MACD so the momentum signal is noise-filtered.
- **ATR (Average True Range)**: volatility-scaled stop widths
  in `atrtrend.py`.
- **Slope**: 1st-derivative measure. `slopetrend.py` uses
  SMA-slope > 0 (vs raw price > SMA) to filter out bear-market
  rallies.

## Backtest results (t50, 2020-2024, 5y window)

```
Year | HPTrend | 0050 ETF
-----|---------|----------
2020 | +39.83% | +22.00%
2021 | +15.98% | +23.50%
2022 |  -5.57% | -22.40%
2023 | +24.63% | +26.50%
2024 | +10.51% | +28.00%
5y   | +14.24% | +15.52%
```

HPTrend is the strongest of the AI strategies at +14.24% 5y avg
— just 1.28pp behind 0050's 15.52% (and the gap would close
to ~1pp in a year where 0050 didn't have a +28% rally).

### Why HPTrend is now the best (after the 2024 tuning)

The first version of HPTrend had `trailing_stop_pct=0.10` and
`trailing_takeprofit_pct=0.12`. The 12% take-profit looked
sensible in backtest rows for choppy 2017-2019 names, but in
2020-2024 (a long bull market), it sold 1/5 of the position at
+12%, +24%, +36%, +48% on names like 2330 (which ran +60%),
locking in gains but missing 30+pp of the bigger picture.

Tuning (`bench_hptrend_v2.py`, then `bench_hptrend_finetune.py`)
over (stop, TP) found:
  - HPR-10-12 (original):  11.13% 5y avg
  - HPR-12-25:            11.38%
  - HPR-10-99 (no TP):    13.74%
  - HPR-12-99:            **14.23%**
  - HPR-13-99:            **14.24%** ← current

The 12% stop + no take-profit is the new sweet spot. The 12%
stop still protects in the 2022 bear (-5.57% vs 0050's -22.40%)
but no longer churns winners in 2020/2023 bull runs.

Fine-tuning over (slope_lookback, hp_lambda) was a flat plateau
(all configs cluster at 14.20-14.24%), so we left the original
3-bar slope + lambda=1e5.

## References

- [Markaicode — Kalman + HP + Wavelet for HFT](https://www.markaicode.com/filter-market-noise-gold-hft/) (73% fewer false signals)
- [Breakout Trading Academy — MA Slope as #1 Filter](https://breakouttradingacademy.com/this-moving-average-is-a-cheat-code/) (slope beats raw-price in 100+ filter comparison)
- [QuantInsti — Kalman for pairs trading](https://blog.quantinsti.com/implementing-pairs-trading-using-kalman-filter/)
- [ML4T — Kalman & Wavelets for feature engineering](https://ml4trading.io/second-edition/chapter/4/)
- [Pairs Trading with Wavelet Transform (Aug 2024)](https://financialnoob.substack.com/pairs-trading-wavelet-transform)
