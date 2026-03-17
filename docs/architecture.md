# Architecture

## Overview

The system has three independent layers that communicate through files and HTTP.

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                           │
│         frontend/index.html + js/script.js              │
│   (Browser — static files, no server needed)            │
└────────────────────┬────────────────────────────────────┘
                     │  HTTP (fetch API)
                     ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
│                  backend/main.py                        │
│              http://127.0.0.1:8000                      │
└────────────────────┬────────────────────────────────────┘
                     │  joblib.load()
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Model Artifacts                         │
│   outputs/models/hmm_model.pkl                          │
│   outputs/models/scaler.pkl                             │
│   outputs/models/model_metadata.json                    │
└────────────────────┬────────────────────────────────────┘
                     │  produced by
                     ▼
┌─────────────────────────────────────────────────────────┐
│                 Training Pipeline                        │
│                   src/train.py                          │
│   Input: data/processed_market_data.csv                 │
│   Output: model artifacts + outputs/figures/*.png       │
└─────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### `src/train.py`
- Loads and sorts historical market data
- Scales features with `StandardScaler`
- Selects optimal regime count (2–6) using BIC
- Trains `GaussianHMM` on 80% of data
- Saves model, scaler, and metadata to `outputs/models/`
- Generates 10 analysis plots to `outputs/figures/`
- Backtests a regime-aware strategy vs. buy-and-hold

### `backend/main.py`
- Loads model artifacts at startup
- Exposes REST API for inference and data export
- Handles CSV upload, column auto-mapping, and validation
- Prepends warmup rows before single-point HMM predictions (sequence context)
- Caches the last CSV analysis result in memory

### `frontend/`
- Communicates with the backend via `fetch()` calls to `http://127.0.0.1:8000`
- Renders interactive Plotly charts (price + VIX, colored by regime)
- Provides CSV upload tab and manual input tab
- What-If Explorer sends live requests on slider change (debounced 400ms)
- Persists theme and manual inputs in `localStorage`

---

## Data Flow — CSV Upload

```
User selects CSV
      │
      ▼
POST /api/market-status?days=N
      │
      ├─ Parse & validate CSV columns (auto-map case variants)
      ├─ scaler.transform(features)
      ├─ model.predict(scaled) → regime per row
      ├─ model.predict_proba(scaled) → confidence for last row
      ├─ Compute summary stats, riskiest period, transition warning
      └─ Return JSON with chart_data, regime_legend, summary
      │
      ▼
Frontend renders:
  - Status bar (signal + confidence, color-coded)
  - Summary stats cards
  - Regime legend pills
  - Price chart (scatter, colored by regime, riskiest period shaded)
  - VIX chart
  - Chart interpretation panel
```

## Data Flow — Manual Input

```
User fills form / moves sliders
      │
      ▼
POST /api/manual-check  { returns, volatility, RSI, momentum, VIX }
      │
      ├─ Build 30-row warmup sequence (model mean state, scaled)
      ├─ Append user row (scaled)
      ├─ model.predict(sequence) → regime of last row
      ├─ model.predict_proba(sequence) → confidence
      └─ Return signal + confidence + regime_legend
      │
      ▼
Frontend updates status bar + What-If result box
```

---

## Key Design Decisions

**Why warmup rows for single-point prediction?**
HMMs use the Viterbi algorithm which needs a sequence to decode. A single row always lands in the same regime regardless of values. Prepending 30 neutral rows (average of all model means) gives Viterbi enough context to make a meaningful prediction.

**Why VIX-based regime classification?**
After training, regimes are unlabeled. We sort them by average VIX — low VIX regimes are "Safe", high VIX regimes are "High Risk". This is done at inference time so it adapts to whatever the model learned.

**Why static frontend?**
Keeps deployment simple — no Node.js, no build step. The frontend is just files you open in a browser. The backend is the only process that needs to run.
