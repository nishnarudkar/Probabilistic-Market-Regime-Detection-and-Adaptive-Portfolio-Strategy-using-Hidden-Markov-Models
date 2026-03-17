import warnings
warnings.filterwarnings('ignore')

import json
import os
import logging
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from sklearn.preprocessing import StandardScaler
from hmmlearn.hmm import GaussianHMM

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

FEATURES = ["returns", "volatility", "RSI", "momentum", "VIX"]
DATA_PATH = "data/processed_market_data.csv"
MODELS_DIR = "outputs/models"
FIGURES_DIR = "outputs/figures"


# ── 1. Setup ──────────────────────────────────────────────────────────────────

def setup_dirs():
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)
    logger.info("Output directories ready.")


# ── 2. Data Loading ───────────────────────────────────────────────────────────

def load_data(path: str) -> pd.DataFrame:
    logger.info(f"Loading data from {path}")
    data = pd.read_csv(path)
    data["Date"] = pd.to_datetime(data["Date"])
    data = data.sort_values("Date").reset_index(drop=True)
    logger.info(f"Loaded {len(data)} rows from {data['Date'].min().date()} to {data['Date'].max().date()}")
    return data


# ── 3. Feature Scaling & Split ────────────────────────────────────────────────

def scale_and_split(data: pd.DataFrame):
    split_idx = int(len(data) * 0.8)
    train_data = data.iloc[:split_idx]
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(train_data[FEATURES])
    X_all_scaled = scaler.transform(data[FEATURES])
    logger.info(f"Train size: {len(train_data)}, Test size: {len(data) - len(train_data)}")
    return scaler, X_train_scaled, X_all_scaled


# ── 4. Model Selection via AIC/BIC ────────────────────────────────────────────

def select_n_components(X_train_scaled: np.ndarray) -> int:
    logger.info("Evaluating HMM components using AIC/BIC...")
    n_range = range(2, 7)
    aic_scores, bic_scores = [], []

    for n in n_range:
        m = GaussianHMM(n_components=n, covariance_type="full", n_iter=1000, random_state=42)
        m.fit(X_train_scaled)
        log_likelihood = m.score(X_train_scaled)
        n_params = n ** 2 + 2 * n * X_train_scaled.shape[1] - 1
        aic_scores.append(-2 * log_likelihood + 2 * n_params)
        bic_scores.append(-2 * log_likelihood + n_params * np.log(len(X_train_scaled)))

    plt.figure(figsize=(8, 5))
    plt.plot(n_range, aic_scores, label="AIC")
    plt.plot(n_range, bic_scores, label="BIC")
    plt.xlabel("Number of Regimes")
    plt.ylabel("Score")
    plt.title("Model Selection using AIC/BIC")
    plt.grid(True)
    plt.legend()
    plt.savefig(f"{FIGURES_DIR}/Model_selection_using_AICbyBIC.png", bbox_inches='tight')
    plt.close()

    best_n = list(n_range)[int(np.argmin(bic_scores))]
    logger.info(f"Optimal number of regimes: {best_n}")
    return best_n


# ── 5. Train & Save ───────────────────────────────────────────────────────────

def train_and_save(X_train_scaled: np.ndarray, scaler: StandardScaler, best_n: int, data: pd.DataFrame) -> GaussianHMM:
    logger.info(f"Training final HMM with {best_n} components...")
    final_model = GaussianHMM(n_components=best_n, covariance_type="full", n_iter=1000, random_state=42)
    final_model.fit(X_train_scaled)
    joblib.dump(final_model, f"{MODELS_DIR}/hmm_model.pkl")
    joblib.dump(scaler, f"{MODELS_DIR}/scaler.pkl")

    # Save metadata
    metadata = {
        "trained_at":      datetime.utcnow().isoformat() + "Z",
        "n_components":    best_n,
        "covariance_type": "full",
        "dataset_rows":    len(data),
        "date_range":      f"{data['Date'].min().date()} to {data['Date'].max().date()}",
        "features":        FEATURES,
        "train_split":     "80/20",
    }
    with open(f"{MODELS_DIR}/model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Artifacts + metadata saved to {MODELS_DIR}/")
    return final_model


# ── 6. Visualizations ─────────────────────────────────────────────────────────

def generate_plots(data: pd.DataFrame, model: GaussianHMM):
    logger.info("Generating analysis plots...")

    # S&P 500 price history
    plt.figure(figsize=(14, 6))
    plt.plot(data["Date"], data["Close"])
    plt.title("S&P 500 Price Over Time")
    plt.xlabel("Date"); plt.ylabel("Price"); plt.grid(True)
    plt.savefig(f"{FIGURES_DIR}/SP500_Price_over_the_years.png", bbox_inches='tight')
    plt.close()

    # Average VIX by regime
    data.groupby("Regime")["VIX"].mean().plot(kind="bar", figsize=(8, 5))
    plt.title("Average VIX by Market Regime")
    plt.xlabel("Regime"); plt.ylabel("Average VIX"); plt.grid(True)
    plt.savefig(f"{FIGURES_DIR}/Average_vix_by_market.png", bbox_inches='tight')
    plt.close()

    # Regime overlay scatter
    plt.figure(figsize=(14, 6))
    for i in range(model.n_components):
        state = data["Regime"] == i
        plt.scatter(data["Date"][state], data["Close"][state], label=f"Regime {i}", s=10)
    plt.title("Market Regimes Detected by HMM")
    plt.xlabel("Date"); plt.ylabel("S&P 500 Price"); plt.legend(); plt.grid(True)
    plt.savefig(f"{FIGURES_DIR}/regime_overlay_plot.png", bbox_inches='tight')
    plt.close()

    # Transition matrix heatmap
    plt.figure(figsize=(6, 5))
    sns.heatmap(model.transmat_, annot=True, cmap="Blues")
    plt.title("HMM State Transition Matrix")
    plt.xlabel("Next State"); plt.ylabel("Current State")
    plt.savefig(f"{FIGURES_DIR}/transition_matrix.png", bbox_inches='tight')
    plt.close()

    # Volatility vs returns
    plt.figure(figsize=(14, 6))
    plt.scatter(data["volatility"], data["returns"], c=data["Regime"], cmap="viridis")
    plt.xlabel("Volatility"); plt.ylabel("Returns")
    plt.title("Market Regimes in Return-Volatility Space")
    plt.colorbar(label="Regime")
    plt.savefig(f"{FIGURES_DIR}/Volatility_vs_Regime_plot.png", bbox_inches='tight')
    plt.close()

    # Timeline fill plot
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(data["Date"], data["Close"], color="black")
    for regime in np.unique(data["Regime"]):
        mask = data["Regime"] == regime
        ax.fill_between(data["Date"], data["Close"].min(), data["Close"].max(),
                        where=mask, alpha=0.2, label=f"Regime {regime}")
    ax.set_title("HMM Market Regime Detection Timeline")
    ax.set_xlabel("Date"); ax.set_ylabel("S&P 500"); ax.legend()
    plt.savefig(f"{FIGURES_DIR}/Market_regime_timeline.png", bbox_inches='tight')
    plt.close()

    # RSI boxplot
    plt.figure(figsize=(10, 6))
    sns.boxplot(x="Regime", y="RSI", data=data)
    plt.title("RSI Distribution Across Market Regimes")
    plt.savefig(f"{FIGURES_DIR}/RSI_Distribution_across_market_regimes.png", bbox_inches='tight')
    plt.close()

    logger.info("All plots saved.")


# ── 7. Backtest ───────────────────────────────────────────────────────────────

def backtest(data: pd.DataFrame, model: GaussianHMM):
    logger.info("Backtesting regime-aware strategy...")
    regime_risk = data.groupby("Regime")["VIX"].mean().sort_values()
    safe_regimes = regime_risk.head(max(1, model.n_components // 2 + 1)).index.tolist()

    data["signal"] = 0
    data.loc[data["Regime"].isin(safe_regimes), "signal"] = 1
    data["strategy_returns"] = data["signal"].shift(1) * data["returns"]
    data["market_cum"] = (1 + data["returns"]).cumprod()
    data["strategy_cum"] = (1 + data["strategy_returns"]).cumprod()

    # Strategy vs buy & hold
    plt.figure(figsize=(14, 6))
    plt.plot(data["Date"], data["market_cum"], label="Buy & Hold (Market)")
    plt.plot(data["Date"], data["strategy_cum"], label="HMM Regime Strategy")
    plt.title("HMM Regime-Based Trading Strategy vs. Buy & Hold")
    plt.xlabel("Date"); plt.ylabel("Cumulative Returns"); plt.legend(); plt.grid(True)
    plt.savefig(f"{FIGURES_DIR}/HMM_Regime_Based_Trading_Strategy.png", bbox_inches='tight')
    plt.close()

    # Drawdown
    market_dd = data["market_cum"] / data["market_cum"].cummax() - 1
    strategy_dd = data["strategy_cum"] / data["strategy_cum"].cummax() - 1
    plt.figure(figsize=(14, 6))
    plt.plot(data["Date"], market_dd, label="Market Drawdown", alpha=0.7)
    plt.plot(data["Date"], strategy_dd, label="Strategy Drawdown", alpha=0.9)
    plt.title("Drawdown Comparison: Strategy vs. Market")
    plt.ylabel("Drawdown"); plt.legend(); plt.grid(True)
    plt.savefig(f"{FIGURES_DIR}/Drawdown_comparison.png", bbox_inches='tight')
    plt.close()

    final_market = data["market_cum"].iloc[-1]
    final_strategy = data["strategy_cum"].iloc[-1]
    logger.info(f"Backtest complete. Market return: {final_market:.2f}x | Strategy return: {final_strategy:.2f}x")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    setup_dirs()
    data = load_data(DATA_PATH)
    scaler, X_train_scaled, X_all_scaled = scale_and_split(data)
    best_n = select_n_components(X_train_scaled)
    final_model = train_and_save(X_train_scaled, scaler, best_n, data)
    data["Regime"] = final_model.predict(X_all_scaled)
    generate_plots(data, final_model)
    backtest(data, final_model)
    logger.info("--- Training Pipeline Complete ---")
    logger.info(f"Models saved to: {MODELS_DIR}/")
    logger.info(f"Figures saved to: {FIGURES_DIR}/")
