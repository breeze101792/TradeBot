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
| `hptrend.py`   | HPTrend      | **+13.48%** | Hodrick-Prescott filtered price + slope |

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
Year |  Hybrid | HPTrend | 0050 ETF
-----|---------|---------|----------
2020 | +29.85% | +27.45% | +22.00%
2021 | +15.90% | +18.61% | +23.50%
2022 |  -4.19% |  -4.60% | -22.40%
2023 | +10.58% | +16.59% | +26.50%
2024 |  +6.48% |  +9.34% | +28.00%
5y   | +11.73% | +13.48% | +15.52%
```

HPTrend is the strongest of the AI strategies at +13.48% 5y avg
(within 2pp of 0050's 15.52%). The remaining gap is the
"in-trend time" — HPTrend is in cash ~40% of the time, 0050
is held continuously.

## References

- [Markaicode — Kalman + HP + Wavelet for HFT](https://www.markaicode.com/filter-market-noise-gold-hft/) (73% fewer false signals)
- [Breakout Trading Academy — MA Slope as #1 Filter](https://breakouttradingacademy.com/this-moving-average-is-a-cheat-code/) (slope beats raw-price in 100+ filter comparison)
- [QuantInsti — Kalman for pairs trading](https://blog.quantinsti.com/implementing-pairs-trading-using-kalman-filter/)
- [ML4T — Kalman & Wavelets for feature engineering](https://ml4trading.io/second-edition/chapter/4/)
- [Pairs Trading with Wavelet Transform (Aug 2024)](https://financialnoob.substack.com/p/pairs-trading-with-wavelet-transform)
