# AI Market Regime Monitor

An unsupervised machine learning system that uses a **Hidden Markov Model (HMM)** to detect hidden market regimes in S&P 500 data and provide automated risk management signals via a web dashboard.

---

## How It Works

The system identifies distinct "regimes" in the market (e.g., bull, bear, high-volatility) by training a Gaussian HMM on technical features. Once trained, the model classifies any new market data into a regime and outputs a simple **Safe to Invest** or **High Risk (Move to Cash)** signal based on the average VIX of each regime.

The pipeline has three stages:

1. **Training** (`src/train.py`) — Trains the HMM, selects the optimal number of regimes via AIC/BIC, backtests a regime-aware strategy, and saves model artifacts.
2. **Backend** (`backend/main.py`) — A FastAPI server that loads the saved model and exposes a `/api/market-status` endpoint for inference.
3. **Frontend** (`frontend/`) — A static HTML/JS dashboard where users upload a processed CSV and see the regime signal + an interactive Plotly chart.

---

## Project Structure

```
├── backend/
│   └── main.py              # FastAPI inference server
├── data/
│   └── processed/           # Place processed_market_data.csv here
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/script.js
├── notebooks/               # For exploratory analysis
├── outputs/
│   ├── models/              # Saved hmm_model.pkl and scaler.pkl
│   └── figures/             # Generated analysis plots
├── src/
│   └── train.py             # Full training pipeline
├── requirements.txt
└── README.md
```

---

## Setup & Installation

**Prerequisites:** Python 3.9+

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
```

---

## Usage

### Step 1 — Prepare Data

Place your processed market data CSV at:

```
data/processed/processed_market_data.csv
```

The CSV must contain these columns:

| Column       | Description                        |
|--------------|------------------------------------|
| `Date`       | Trading date                       |
| `Close`      | S&P 500 closing price              |
| `returns`    | Daily log or simple returns        |
| `volatility` | Rolling volatility                 |
| `RSI`        | Relative Strength Index            |
| `momentum`   | Price momentum indicator           |
| `VIX`        | CBOE Volatility Index              |

### Step 2 — Train the Model

```bash
python src/train.py
```

This will:
- Select the optimal number of HMM regimes (2–6) using BIC
- Train the final model on 80% of the data
- Save `outputs/models/hmm_model.pkl` and `outputs/models/scaler.pkl`
- Generate analysis plots in `outputs/figures/`
- Backtest a regime-aware strategy vs. buy-and-hold

### Step 3 — Start the Backend

```bash
uvicorn backend.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### Step 4 — Open the Dashboard

Open `frontend/index.html` directly in your browser, upload your processed CSV, and click **Analyze Market Data**.

The dashboard will display:
- Current regime signal (Safe / High Risk)
- Current regime ID and latest VIX reading
- Interactive S&P 500 chart with data points colored by detected regime

---

## API Reference

### `POST /api/market-status`

Accepts a CSV file upload and returns the current market regime signal.

**Request:** `multipart/form-data` with a `file` field containing the processed CSV.

**Response:**
```json
{
  "current_status": "Safe to Invest (Bull/Calm Market)",
  "current_regime_id": 2,
  "latest_vix": 14.73,
  "chart_data": {
    "dates": ["2024-01-02", "..."],
    "prices": [4742.83, "..."],
    "regimes": [2, "..."]
  }
}
```

---

## Generated Outputs

After training, the following plots are saved to `outputs/figures/`:

| File | Description |
|------|-------------|
| `SP500_Price_over_the_years.png` | Raw S&P 500 price history |
| `Model_selection_using_AICbyBIC.png` | AIC/BIC curve for regime count selection |
| `regime_overlay_plot.png` | Price chart with regime-colored scatter points |
| `Market_regime_timeline.png` | Timeline with regime fill bands |
| `Average_vix_by_market.png` | Average VIX per regime |
| `RSI_Distribution_across_market_regimes.png` | RSI boxplot by regime |
| `Volatility_vs_Regime_plot.png` | Returns vs. volatility colored by regime |
| `transition_matrix.png` | HMM state transition probability heatmap |
| `HMM_Regime_Based_Trading_Strategy.png` | Strategy vs. buy-and-hold cumulative returns |
| `Drawdown_comparison.png` | Drawdown comparison: strategy vs. market |

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.104.1 | REST API framework |
| `uvicorn` | 0.24.0 | ASGI server |
| `python-multipart` | 0.0.6 | File upload support |
| `pandas` | 2.1.3 | Data manipulation |
| `hmmlearn` | 0.3.0 | Hidden Markov Model |
| `scikit-learn` | 1.3.2 | Feature scaling |
