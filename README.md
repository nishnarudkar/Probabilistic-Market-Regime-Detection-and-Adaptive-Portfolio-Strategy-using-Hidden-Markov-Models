# AI Market Regime Monitor

An unsupervised machine learning system that uses a **Hidden Markov Model (HMM)** to detect hidden market regimes in S&P 500 data and provide automated risk management signals via a web dashboard.

---

## How It Works

The system identifies distinct "regimes" in the market (e.g. bull, bear, high-volatility) by training a Gaussian HMM on five technical features. Once trained, the model classifies any new market data into a regime and outputs a **Safe to Invest** or **High Risk (Move to Cash)** signal based on the average VIX of each regime, along with a confidence score derived from the HMM's posterior probabilities.

The pipeline has three stages:

1. **Training** (`src/train.py`) — Trains the HMM, selects the optimal number of regimes via AIC/BIC, backtests a regime-aware strategy, and saves model artifacts + metadata.
2. **Backend** (`backend/main.py`) — A FastAPI server that loads the saved model and exposes REST endpoints for inference, analysis, and data export.
3. **Frontend** (`frontend/`) — A static HTML/JS dashboard with two modes: CSV upload for full historical analysis, and manual input for single-point experimentation with a real-time What-If Explorer.

---

## Project Structure

```
├── .github/
│   └── workflows/
│       └── validate.yml         # CI: trains on sample data, validates artifacts
├── backend/
│   └── main.py                  # FastAPI inference server
├── data/
│   ├── processed_market_data.csv  # Your real training data (not included)
│   ├── sample_data.csv            # Synthetic data for testing (500 rows)
│   └── generate_sample.py         # Script to regenerate sample data
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/script.js
├── notebooks/                   # For exploratory analysis
├── outputs/
│   ├── models/                  # hmm_model.pkl, scaler.pkl, model_metadata.json
│   └── figures/                 # Generated analysis plots
├── src/
│   └── train.py                 # Full training pipeline
├── CONTRIBUTING.md
├── Dockerfile
├── docker-compose.yml
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

Place your processed market data CSV at `data/processed_market_data.csv`.

The CSV must contain these columns (case-insensitive — the backend auto-maps variants):

| Column | Description |
|--------|-------------|
| `Date` | Trading date |
| `Close` | S&P 500 closing price |
| `returns` | Daily log or simple returns |
| `volatility` | Rolling volatility (~20-day std of returns) |
| `RSI` | Relative Strength Index (0–100) |
| `momentum` | 10-day price change in points |
| `VIX` | CBOE Volatility Index |

To test without real data, use the included sample:
```bash
python data/generate_sample.py   # generates data/sample_data.csv
```

### Step 2 — Train the Model

```bash
python src/train.py
```

This will:
- Select the optimal number of HMM regimes (2–6) using BIC
- Train the final model on 80% of the data (20% held out)
- Save `outputs/models/hmm_model.pkl`, `scaler.pkl`, and `model_metadata.json`
- Generate analysis plots in `outputs/figures/`
- Backtest a regime-aware strategy vs. buy-and-hold

### Step 3 — Start the Backend

```bash
uvicorn backend.main:app --reload
```

API available at `http://127.0.0.1:8000`. Interactive docs at `http://127.0.0.1:8000/docs`.

### Step 4 — Open the Dashboard

Open `frontend/index.html` in your browser (double-click or `start frontend/index.html` on Windows).

---

## Dashboard Features

**CSV Upload tab**
- Upload your processed CSV and click "Analyze Market Data"
- Control how many recent trading days to display (30–2000)
- Summary stats card: total rows, date range, % time in safe vs risky regimes, longest high-risk streak
- Interactive S&P 500 price chart colored by regime, with the riskiest historical period shaded in red
- VIX chart below, also colored by regime
- Regime transition warning if the last 5 rows span 3+ different regimes
- Confidence score (HMM posterior probability) shown alongside the signal
- Click any regime pill to highlight/isolate it on the chart
- Download the CSV with `Regime` and `Regime_Label` columns appended
- Export the full report as a PDF

**Manual Input tab**
- Enter any 5 feature values and get an instant regime prediction with confidence score
- "Load Default Values" fills in typical calm market values for quick experimentation
- What-If Explorer — sliders that update the signal in real time as you drag, no re-submit needed
- Last entered values are saved in `localStorage` and restored on page refresh
- Press Enter to submit the form

**Other**
- Dark mode toggle (persisted across sessions)
- Model Info panel — shows n_regimes, training date, dataset size, feature means per regime
- User Guide panel — explains each feature, typical value ranges, and a reference table of value combinations that trigger each regime
- Training Analysis Plots grid at the bottom (collapsible), served directly from the backend

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Backend and model status |
| `GET` | `/api/model-info` | Model metadata, regime means, training info |
| `POST` | `/api/market-status?days=250` | Analyze uploaded CSV, returns signal + chart data |
| `GET` | `/api/last-result` | Returns cached result of last CSV analysis |
| `POST` | `/api/download-csv` | Returns CSV with Regime + Regime_Label columns |
| `POST` | `/api/manual-check` | Single-point regime prediction from JSON body |
| `POST` | `/api/batch-manual` | Batch predictions for multiple rows |
| `GET` | `/api/figures` | List available training plot filenames |
| `GET` | `/api/figures/{filename}` | Serve a specific training plot |

### `POST /api/market-status` response example

```json
{
  "current_status": "Safe to Invest (Bull/Calm Market)",
  "current_regime_id": 2,
  "confidence": 91.4,
  "transition_warning": false,
  "latest_vix": 14.73,
  "n_regimes": 6,
  "regime_legend": { "2": { "label": "Low Risk", "avg_vix": 11.98 } },
  "analyzed_at": "2026-03-18T10:00:00Z",
  "summary": {
    "total_rows": 2342,
    "date_range": "2015-01-02 to 2024-12-31",
    "safe_pct": 68.4,
    "risk_pct": 31.6,
    "riskiest_period": { "days": 56, "start_date": "2020-02-24", "end_date": "2020-05-08" }
  },
  "chart_data": { "dates": ["..."], "prices": ["..."], "regimes": ["..."], "vix": ["..."] }
}
```

---

## Docker

```bash
docker compose up --build
```

The backend runs on port 8000. Open `frontend/index.html` in your browser.

---

## Generated Outputs

After training, plots are saved to `outputs/figures/`:

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

| Package | Purpose |
|---------|---------|
| `fastapi` | REST API framework |
| `uvicorn` | ASGI server |
| `python-multipart` | File upload support |
| `pandas` | Data manipulation |
| `hmmlearn` | Hidden Markov Model |
| `scikit-learn` | Feature scaling |
| `matplotlib` + `seaborn` | Training plots |
| `joblib` | Model serialization |

---

## Built by

[Nishant Narudkar](https://github.com/nishnarudkar) · [Aamir Sarang](https://github.com/Aamir-Sarang31) · [Saksham Shukla](https://github.com/Saksham-3175)
