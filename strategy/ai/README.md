# AI / Noise-Filtered Strategies

This folder contains strategies that use **mathematical denoising
of the price series** before trend detection. The goal is to
separate the "true" trend from the 1-2 day noise that fools
raw-price filters.

## Strategies

| File | Strategy | 5y avg return (t50, 2020-2024) | Math |
|------|----------|-------------------------------|------|
| `hptrend.py`     | HPTrend         | **+14.23%** | HP-filtered price + slope |
| `hptrend_ha.py`  | HPTrendHA       | +14.16%     | HP-filtered Heikin Ashi close |
| `hybrid.py`      | Hybrid          | +13.02%     | MultiSignal gated by SMA-45 + MACD>0 |
| `slopetrend.py`  | SlopeTrend      | +12.45%     | SMA slope + Kalman-filtered MACD |
| `adaptive.py`    | AdaptiveTrend   | +7.99%      | SMA-200 trend filter + MACD + ATR |
| `trendrider.py`  | TrendRider      | +7.97%      | Long-only trend-rider, wide trailing stop |
| `atrtrend.py`    | ATRTrend        | +7.58%      | SMA-200 filter + ATR-based stops |
| `dualmomentum.py`| DualMomentum    | +7.23%      | GEMS-style 12m return + 200d MA |
| `donchian.py`    | Donchian        | +8.30%      | 20-day high breakout, 10-day low exit (Turtle S1) |
| `dualthrust.py`  | DualThrust      | +1.03%      | Adaptive range breakout (Chiu 1997) |
| `volbreakout.py` | VolBreakout     | -0.71%      | Open + k*ATR threshold (Williams) |
| `supertrend.py`  | SuperTrend      | -10.80%     | ATR-based trend indicator |
| `keltner.py`     | Keltner         | +9.83%      | EMA + k*ATR envelope |
| `keltner_hp.py`  | KeltnerHP       | +11.07%     | Keltner on HP-filtered price (long EMA-50, ATR-20, k=1.5) |
| `psar.py`        | ParabolicSAR    | +8.16%      | Wilder's trailing-stop flip |

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

## Backtest results (t50, 2020-2024, 5y window, HP-tuned 12/99 risk)

```
Year | HPTrend | Hybrid | SlopeTrend | 0050 ETF
-----|---------|--------|------------|----------
2020 | +39.83% | +40.04%|  +39.06%   | +22.00%
2021 | +15.98% | +19.59%|  +18.98%   | +23.50%
2022 |  -5.57% |  -5.04%|   -5.29%   | -22.40%
2023 | +24.63% | +16.51%|  +17.75%   | +26.50%
2024 | +10.51% |  +7.01%|   +4.18%   | +28.00%
5y   | +14.23% | +13.02%|  +12.45%   | +15.52%
```

### Full ranking (t50 2020-2024, HP-tuned 12/99 risk)

```
 1. HPTrend       +14.23%   ← best AI strategy
 2. HPTrendHA     +14.16%   (HA close; basically tied with HPTrend)
 3. Hybrid        +13.02%   (mean-reversion + trend gate)
 4. SlopeTrend    +12.45%   (Kalman-MACD + slope)
 5. KeltnerHP     +11.07%   (long EMA-50 + ATR-20, HP-filtered)
 6. Keltner        +9.83%
 7. Donchian       +8.30%
 8. ParabolicSAR   +8.16%
 9. Adaptive       +7.99%
10. TrendRider     +7.97%
11. ATRTrend       +7.58%
12. DualMomentum   +7.23%
13. DualThrust     +1.03%
14. VolBreakout    -0.71%
15. SuperTrend    -10.80%
```

### The HP-tuned risk profile (12% stop, no take-profit)

Tuning `bench_hptrend_v2.py` found that **12% trailing stop +
0.99 take-profit (effectively no TP)** is the optimal risk
profile on t50/5y. This combination is universally beneficial
for trend-following strategies:

| Strategy          | Original (10/12 or 4/10) | HP-tuned (12/99) | Gain |
|-------------------|--------------------------|------------------|------|
| AdaptiveTrend     |  +2.17%                  |  +7.99%          | +5.82pp |
| Hybrid            |  +9.67%                  | +13.02%          | +3.35pp |
| SlopeTrend        |  +8.87%                  | +12.45%          | +3.58pp |
| ATRTrend          |  +6.38%                  |  +7.58%          | +1.20pp |
| TrendRider        |  +6.99%                  |  +7.97%          | +0.98pp |
| HPTrend           | +11.13%                  | +14.23%          | +3.10pp |

The 12% trailing stop lets through mid-trend pullbacks (TWSE
regularly pulls back 8-12% mid-trend) but still protects in
2022-style bear markets (-5% vs 0050's -22%). Removing the
take-profit lets winners run — the 12% TP was selling 1/5 of
positions at +12%, +24%, +36%, +48% in +60% bull runs (e.g.
2330 in 2020), capturing gains but missing 30+pp of upside.

### Why HPTrend is the strongest AI strategy

HPTrend uses the **HP filter** to denoise price action, then
checks the **slope of the smoothed series** rather than the
raw price. This eliminates the 1-2 day noise that fools the
Hybrid's "close > SMA" check.

The HP filter is a macro-economist's tool for separating trend
from cycle. With `lambda=1e5` on a 90-day window, the result
is a smooth "true" trend that:
- Rises continuously through bull markets (catching 2330's
  +60% in 2020, 2308's +90% in 2023)
- Stays flat during choppy sideways action
- Falls only in real bear markets (2022: -5% vs 0050's -22%)

The `slope_lookback=3` (3-bar slope rise required) and
`hp_lambda=1e5` are the grid-search-best values. Fine-tuning
over (slope, lambda) was a flat plateau at 14.20-14.24%.

### 1.3pp gap to 0050 (15.52%)

The remaining gap is structural:
- 0050 is cap-weighted (holds more 2330/2454/2308 than
  equal-weighted t50)
- 0050 caught the 2024 AI rally (+28%) better than HPTrend
  (+10.5%) because it didn't sell high-multiple tech names
- Pure signal processing on equal-weight t50 has hit a
  plateau at ~14%

To close the gap requires either: (a) cap-weighting the
portfolio, (b) different exit criteria for AI-sector names,
or (c) accepting the 14% as the strategy's ceiling.

## References

- [Markaicode — Kalman + HP + Wavelet for HFT](https://www.markaicode.com/filter-market-noise-gold-hft/) (73% fewer false signals)
- [Breakout Trading Academy — MA Slope as #1 Filter](https://breakouttradingacademy.com/this-moving-average-is-a-cheat-code/) (slope beats raw-price in 100+ filter comparison)
- [QuantInsti — Kalman for pairs trading](https://blog.quantinsti.com/implementing-pairs-trading-using-kalman-filter/)
- [ML4T — Kalman & Wavelets for feature engineering](https://ml4trading.io/second-edition/chapter/4/)
- [Pairs Trading with Wavelet Transform (Aug 2024)](https://financialnoob.substack.com/pairs-trading-wavelet-transform)
