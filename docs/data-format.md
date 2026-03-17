# Data Format

## Required CSV Schema

The input CSV must contain the following columns. Column names are **case-insensitive** — the backend auto-maps common variants (e.g. `date` → `Date`, `close` → `Close`).

| Column | Type | Description |
|--------|------|-------------|
| `Date` | string / date | Trading date (any parseable format) |
| `Close` | float | S&P 500 closing price |
| `returns` | float | Daily simple or log return |
| `volatility` | float | Rolling volatility (~20-day std of returns) |
| `RSI` | float | Relative Strength Index (0–100) |
| `momentum` | float | 10-day price change in points |
| `VIX` | float | CBOE Volatility Index |

Additional columns are allowed and will be ignored.

---

## Example Rows

```csv
Date,Close,returns,volatility,RSI,momentum,VIX
2024-01-02,4742.83,0.0012,0.0082,61.3,18.4,13.29
2024-01-03,4704.81,-0.0080,0.0091,54.7,-12.1,14.16
2024-01-04,4697.24,-0.0016,0.0089,52.1,-19.8,14.53
```

---

## Feature Descriptions

### `returns`
Daily percentage change in the closing price.

```
returns = (Close_today - Close_yesterday) / Close_yesterday
```

Typical range: -0.10 to +0.10 (i.e. -10% to +10%)
Crisis days can exceed ±10%.

### `volatility`
Rolling standard deviation of returns over approximately 20 trading days.

```python
data["volatility"] = data["returns"].rolling(20).std()
```

Typical range: 0.003 (very calm) to 0.08+ (crisis)

### `RSI`
Relative Strength Index — a momentum oscillator measuring the speed and magnitude of recent price changes.

```
RSI = 100 - (100 / (1 + RS))
RS  = avg_gain / avg_loss  over 14 periods
```

Range: 0–100
- Below 30: oversold / bearish
- 30–70: neutral
- Above 70: overbought / bullish

### `momentum`
10-day price change in absolute points (not percentage).

```
momentum = Close_today - Close_10_days_ago
```

Typical range in this dataset: -732 to +426
Positive = uptrend, negative = downtrend.

> Note: This is point-based, not percentage-based. The scale depends on the absolute price level of the index.

### `VIX`
CBOE Volatility Index — the market's "fear gauge". Measures expected 30-day volatility implied by S&P 500 options.

Typical ranges:
- Below 15: calm / complacent market
- 15–20: normal conditions
- 20–30: elevated uncertainty
- 30–40: significant stress
- 40+: crisis / extreme fear

VIX is the **strongest regime driver** in this model.

---

## Preparing Your Own Data

If you have raw OHLCV data, here's a minimal preprocessing script:

```python
import pandas as pd
import yfinance as yf

# Download S&P 500 and VIX
sp500 = yf.download("^GSPC", start="2015-01-01", end="2024-12-31")
vix   = yf.download("^VIX",  start="2015-01-01", end="2024-12-31")

df = pd.DataFrame()
df["Date"]       = sp500.index
df["Close"]      = sp500["Close"].values
df["returns"]    = df["Close"].pct_change()
df["volatility"] = df["returns"].rolling(20).std()
df["RSI"]        = compute_rsi(df["Close"], period=14)   # implement or use ta-lib
df["momentum"]   = df["Close"] - df["Close"].shift(10)
df["VIX"]        = vix["Close"].values

df = df.dropna().reset_index(drop=True)
df.to_csv("data/processed_market_data.csv", index=False)
```

---

## Sample Data

A synthetic 500-row dataset is included at `data/sample_data.csv` for testing without real market data.

To regenerate it:
```bash
python data/generate_sample.py
```

The sample data uses a simple regime-switching simulation and is **not suitable for real analysis** — it is only for verifying the pipeline works end-to-end.

---

## Minimum Data Requirements

- The backend accepts CSVs with at least 30 rows (enforced by `days` parameter minimum)
- Training requires enough data for an 80/20 split — at least 200 rows recommended, 1000+ for reliable regime detection
- The real dataset used in this project covers 2015–2024 (~2,342 trading days)
