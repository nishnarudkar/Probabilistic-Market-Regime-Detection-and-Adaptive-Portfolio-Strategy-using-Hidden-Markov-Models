import warnings
warnings.filterwarnings('ignore')

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from sklearn.preprocessing import StandardScaler
from hmmlearn.hmm import GaussianHMM
import matplotlib.dates as mdates

# ==========================================
# 1. SETUP DIRECTORIES
# ==========================================
print("Setting up output directories...")
os.makedirs("outputs/models", exist_ok=True)
os.makedirs("outputs/figures", exist_ok=True)

# ==========================================
# 2. DATA LOADING
# ==========================================
print("Loading processed data...")
# Adjust this path if your CSV is in a different location
data = pd.read_csv("data/processed/processed_market_data.csv")
data["Date"] = pd.to_datetime(data["Date"])
data = data.sort_values("Date").reset_index(drop=True)

# Initial S&P 500 Price Plot
plt.figure(figsize=(14,6))
plt.plot(data["Date"], data["Close"])
plt.title("S&P 500 Price Over Time")
plt.xlabel("Date")
plt.ylabel("Price")
plt.grid(True)
plt.savefig("outputs/figures/SP500_Price_over_the_years.png", bbox_inches='tight')
plt.close()

# ==========================================
# 3. FEATURE SELECTION & SPLIT
# ==========================================
print("Scaling features and splitting data...")
features = ["returns", "volatility", "RSI", "momentum", "VIX"]

# 80/20 train/test split to prevent look-ahead bias
split_idx = int(len(data) * 0.8)
train_data = data.iloc[:split_idx]
test_data = data.iloc[split_idx:]

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(train_data[features])
X_all_scaled = scaler.transform(data[features]) 

# ==========================================
# 4. MODEL SELECTION (AIC / BIC)
# ==========================================
print("Evaluating HMM components using AIC/BIC...")
n_components_range = range(2, 7)
aic_scores = []
bic_scores = []

for n in n_components_range:
    model = GaussianHMM(n_components=n, covariance_type="full", n_iter=1000, random_state=42)
    model.fit(X_train_scaled) 
    
    log_likelihood = model.score(X_train_scaled)
    n_params = n**2 + 2*n*X_train_scaled.shape[1] - 1
    
    aic = -2 * log_likelihood + 2 * n_params
    bic = -2 * log_likelihood + n_params * np.log(len(X_train_scaled))
    
    aic_scores.append(aic)
    bic_scores.append(bic)

# Plot AIC/BIC
plt.figure(figsize=(8,5))
plt.plot(n_components_range, aic_scores, label="AIC")
plt.plot(n_components_range, bic_scores, label="BIC")
plt.xlabel("Number of Regimes")
plt.ylabel("Score")
plt.title("Model Selection using AIC/BIC")
plt.grid(True)
plt.legend()
plt.savefig("outputs/figures/Model_selection_using_AICbyBIC.png", bbox_inches='tight')
plt.close()

best_n = n_components_range[np.argmin(bic_scores)]
print(f"Optimal number of regimes selected: {best_n}")

# ==========================================
# 5. FINAL TRAINING & EXPORT
# ==========================================
print("Training final model and saving artifacts...")
final_model = GaussianHMM(n_components=best_n, covariance_type="full", n_iter=1000, random_state=42)
final_model.fit(X_train_scaled)

# Save the trained model and scaler for the FastAPI backend
joblib.dump(final_model, 'outputs/models/hmm_model.pkl')
joblib.dump(scaler, 'outputs/models/scaler.pkl')

# Predict hidden states for the entire timeline
data["Regime"] = final_model.predict(X_all_scaled)

# ==========================================
# 6. VISUALIZATIONS & PLOTS
# ==========================================
print("Generating and saving analysis plots...")

# Average VIX by Regime
data.groupby("Regime")["VIX"].mean().plot(kind="bar", figsize=(8,5))
plt.title("Average VIX by Market Regime")
plt.xlabel("Regime")
plt.ylabel("Average VIX")
plt.grid(True)
plt.savefig("outputs/figures/Average_vix_by_market.png", bbox_inches='tight')
plt.close()

# Market Regime Timeline Overlay (Scatter)
plt.figure(figsize=(14,6))
for i in range(final_model.n_components):
    state = data["Regime"] == i
    plt.scatter(data["Date"][state], data["Close"][state], label=f"Regime {i}", s=10)
plt.title("Market Regimes Detected by HMM")
plt.xlabel("Date")
plt.ylabel("S&P 500 Price")
plt.legend()
plt.grid(True)
plt.savefig("outputs/figures/regime_overlay_plot.png", bbox_inches='tight')
plt.close()

# Transition Matrix Heatmap
plt.figure(figsize=(6,5))
sns.heatmap(final_model.transmat_, annot=True, cmap="Blues")
plt.title("HMM State Transition Matrix")
plt.xlabel("Next State")
plt.ylabel("Current State")
plt.savefig("outputs/figures/transition_matrix.png", bbox_inches='tight')
plt.close()

# Volatility vs Returns Space
plt.figure(figsize=(14,6))
plt.scatter(data["volatility"], data["returns"], c=data["Regime"], cmap="viridis")
plt.xlabel("Volatility")
plt.ylabel("Returns")
plt.title("Market Regimes in Return-Volatility Space")
plt.colorbar(label="Regime")
plt.savefig("outputs/figures/Volatility_vs_Regime_plot.png", bbox_inches='tight')
plt.close()

# Timeline Fill Plot
fig, ax = plt.subplots(figsize=(15,6))
ax.plot(data["Date"], data["Close"], color="black")
for regime in np.unique(data["Regime"]):
    mask = data["Regime"] == regime
    ax.fill_between(data["Date"], data["Close"].min(), data["Close"].max(), 
                    where=mask, alpha=0.2, label=f"Regime {regime}")
ax.set_title("HMM Market Regime Detection Timeline")
ax.set_xlabel("Date")
ax.set_ylabel("S&P 500")
ax.legend()
plt.savefig("outputs/figures/Market_regime_timeline.png", bbox_inches='tight')
plt.close()

# RSI Boxplot
plt.figure(figsize=(10,6))
sns.boxplot(x="Regime", y="RSI", data=data)
plt.title("RSI Distribution Across Market Regimes")
plt.savefig("outputs/figures/RSI_Distribution_across_market_regimes.png", bbox_inches='tight')
plt.close()

# ==========================================
# 7. REGIME-AWARE TRADING STRATEGY
# ==========================================
print("Backtesting regime-aware strategy...")

# Dynamically map regimes based on risk (Average VIX)
regime_risk = data.groupby("Regime")["VIX"].mean().sort_values()
safe_regimes = regime_risk.head(3).index.tolist()

# Generate signals: 1 for safe regimes, 0 for high-risk
data["signal"] = 0
data.loc[data["Regime"].isin(safe_regimes), "signal"] = 1

# Calculate returns (shifted to avoid look-ahead bias)
data["strategy_returns"] = data["signal"].shift(1) * data["returns"]

data["market_cum"] = (1 + data["returns"]).cumprod()
data["strategy_cum"] = (1 + data["strategy_returns"]).cumprod()

# Plot Strategy vs Buy & Hold
plt.figure(figsize=(14,6))
plt.plot(data["Date"], data["market_cum"], label="Buy & Hold (Market)")
plt.plot(data["Date"], data["strategy_cum"], label="HMM Regime Strategy")
plt.title("HMM Regime-Based Trading Strategy vs. Buy & Hold")
plt.xlabel("Date")
plt.ylabel("Cumulative Returns")
plt.legend()
plt.grid(True)
plt.savefig("outputs/figures/HMM_Regime_Based_Trading_Strategy.png", bbox_inches='tight')
plt.close()

# Drawdown Visualization
cum_market = (1 + data["returns"]).cumprod()
cum_strategy = (1 + data["strategy_returns"]).cumprod()

market_drawdown = cum_market / cum_market.cummax() - 1
strategy_drawdown = cum_strategy / cum_strategy.cummax() - 1

plt.figure(figsize=(14,6))
plt.plot(data["Date"], market_drawdown, label="Market Drawdown", alpha=0.7)
plt.plot(data["Date"], strategy_drawdown, label="Strategy Drawdown", alpha=0.9)
plt.title("Drawdown Comparison: Strategy vs. Market")
plt.ylabel("Drawdown")
plt.legend()
plt.grid(True)
plt.savefig("outputs/figures/Drawdown_comparison.png", bbox_inches='tight')
plt.close()

print("\n--- Training Pipeline Complete ---")
print("Models saved to:  outputs/models/")
print("Figures saved to: outputs/figures/")