"""Run this once to generate data/sample_data.csv for UI testing."""
import numpy as np
import pandas as pd

np.random.seed(42)
n = 500
dates = pd.date_range("2022-01-03", periods=n, freq="B")

price = 4000.0
prices, returns_list = [], []
for _ in range(n):
    r = np.random.normal(0.0003, 0.012)
    price *= (1 + r)
    prices.append(round(price, 2))
    returns_list.append(round(r, 6))

returns = np.array(returns_list)
volatility = pd.Series(returns).rolling(20).std().fillna(0.01).round(6).tolist()

# RSI
def calc_rsi(r, period=14):
    gains = np.where(r > 0, r, 0)
    losses = np.where(r < 0, -r, 0)
    avg_gain = pd.Series(gains).rolling(period).mean().fillna(0.5)
    avg_loss = pd.Series(losses).rolling(period).mean().fillna(0.5)
    rs = avg_gain / (avg_loss + 1e-9)
    return (100 - 100 / (1 + rs)).round(2).tolist()

rsi = calc_rsi(returns)
momentum = pd.Series(prices).pct_change(10).fillna(0).round(6).tolist()
vix = (15 + 10 * pd.Series(volatility) / pd.Series(volatility).max() + np.random.normal(0, 1, n)).clip(9, 60).round(2).tolist()

df = pd.DataFrame({
    "Date":       dates.strftime("%Y-%m-%d"),
    "Close":      prices,
    "returns":    returns_list,
    "volatility": volatility,
    "RSI":        rsi,
    "momentum":   momentum,
    "VIX":        vix,
})

df.to_csv("data/sample_data.csv", index=False)
print(f"Saved data/sample_data.csv ({len(df)} rows)")
