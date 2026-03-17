# Contributing

## Project structure

```
backend/main.py       — FastAPI inference server
src/train.py          — HMM training pipeline
frontend/             — Static HTML/CSS/JS dashboard
data/                 — Raw and processed market data
outputs/models/       — Saved model artifacts (generated)
outputs/figures/      — Training analysis plots (generated)
.github/workflows/    — CI validation
```

## Setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Retraining the model

1. Place your processed CSV at `data/processed_market_data.csv` with columns:
   `Date, Close, returns, volatility, RSI, momentum, VIX`

2. Run the training pipeline:
   ```bash
   python src/train.py
   ```

3. Artifacts are saved to `outputs/models/`. Restart the backend to pick them up.

## Running the backend

```bash
uvicorn backend.main:app --reload
```

## Adding a new feature to the backend

1. Add a new endpoint in `backend/main.py`
2. Follow the existing pattern — use `_classify_regimes_from_means()` for regime logic
3. Add the corresponding fetch call in `frontend/js/script.js`

## Adding a new training feature

1. Add the feature column to your CSV preparation step
2. Add the column name to `FEATURES` in both `src/train.py` and `backend/main.py`
3. Retrain the model — the scaler and HMM will automatically incorporate the new feature
4. Update the User Guide table in `frontend/index.html`

## Docker

```bash
docker compose up --build
```

The backend runs on port 8000. Open `frontend/index.html` in your browser.

## CI

GitHub Actions runs on every push to `main`/`master`:
- Installs dependencies
- Trains the model on sample data
- Validates all artifacts exist
- Validates the backend imports cleanly

See `.github/workflows/validate.yml`.
