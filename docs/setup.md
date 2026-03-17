# Setup & Deployment

## Prerequisites

- Python 3.9 or higher
- pip
- (Optional) Docker + Docker Compose for containerized deployment

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-org/market-regime-hmm.git
cd market-regime-hmm
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Activate
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Prepare data

Place your processed market data CSV at:
```
data/processed_market_data.csv
```

See [Data Format](data-format.md) for the required columns.

To test without real data, generate synthetic sample data:
```bash
python data/generate_sample.py
# creates data/sample_data.csv (500 rows)
```

Then edit `src/train.py` line:
```python
DATA_PATH = "data/processed_market_data.csv"
```
to:
```python
DATA_PATH = "data/sample_data.csv"
```

### 5. Train the model

```bash
python src/train.py
```

Expected output:
```
outputs/models/hmm_model.pkl
outputs/models/scaler.pkl
outputs/models/model_metadata.json
outputs/figures/*.png   (10 plots)
```

Training takes ~30 seconds on a typical laptop.

### 6. Start the backend

```bash
uvicorn backend.main:app --reload
```

The API is now available at `http://127.0.0.1:8000`.
Swagger UI: `http://127.0.0.1:8000/docs`

### 7. Open the dashboard

Open `frontend/index.html` directly in your browser:
- Double-click the file in Explorer/Finder, or
- Run `start frontend/index.html` (Windows), or
- Run `open frontend/index.html` (macOS)

---

## Docker Deployment

### Build and run

```bash
docker compose up --build
```

This starts the backend on port 8000. The `outputs/` and `data/` directories are mounted as volumes so model artifacts persist between container restarts.

### Run in background

```bash
docker compose up -d --build
```

### Stop

```bash
docker compose down
```

### Notes

- The frontend is not served by Docker — open `frontend/index.html` in your browser as usual
- Make sure you have trained the model before starting Docker, or mount the training data and run `train.py` inside the container

---

## Environment Variables

No environment variables are required for local development. The backend uses hardcoded relative paths for model artifacts.

If you need to override paths (e.g. in a custom deployment), edit these constants at the top of `backend/main.py`:

```python
MODEL_PATH  = os.path.join(BASE_DIR, "../outputs/models/hmm_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "../outputs/models/scaler.pkl")
META_PATH   = os.path.join(BASE_DIR, "../outputs/models/model_metadata.json")
FIGURES_DIR = os.path.join(BASE_DIR, "../outputs/figures")
```

---

## Retraining the Model

To retrain with new data:

1. Replace or update `data/processed_market_data.csv`
2. Run `python src/train.py`
3. Restart the backend: `uvicorn backend.main:app --reload`

The backend loads model artifacts at startup — a restart is required to pick up new artifacts.

---

## Dependency Notes

| Package | Version | Notes |
|---------|---------|-------|
| `hmmlearn` | 0.3.x | Must match the version used to train the model — loading a `.pkl` trained with a different version may raise a warning |
| `scikit-learn` | 1.8.x | Same constraint — scaler.pkl is version-sensitive |
| `fastapi` | 0.100+ | Required for `list[ManualInput]` type hint syntax |
| `python-multipart` | any | Required for file upload support in FastAPI |

If you see a sklearn version mismatch warning on load, retrain the model in the same environment where the backend runs.

---

## CI/CD

The project includes a GitHub Actions workflow at `.github/workflows/validate.yml`.

It runs automatically on every push or pull request to `main`/`master` and:
1. Installs dependencies
2. Generates sample data
3. Trains the model on sample data
4. Validates that all model artifacts were created
5. Imports the backend and verifies the model loads

No configuration needed — just push to GitHub and check the **Actions** tab.
