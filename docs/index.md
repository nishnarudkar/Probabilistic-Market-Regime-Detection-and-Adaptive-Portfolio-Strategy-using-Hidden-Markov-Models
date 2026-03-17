# AI Market Regime Monitor — Documentation

Welcome to the project documentation. Use the links below to navigate.

---

## Contents

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | System design, component overview, data flow |
| [API Reference](api-reference.md) | All backend endpoints with request/response examples |
| [Model](model.md) | HMM theory, training pipeline, feature engineering |
| [Frontend](frontend.md) | Dashboard guide, tabs, panels, keyboard shortcuts |
| [Setup & Deployment](setup.md) | Local setup, Docker, environment variables |
| [Data Format](data-format.md) | CSV schema, column descriptions, sample data |

---

## Quick Start

```bash
# 1. Install dependencies
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 2. Train the model
python src/train.py

# 3. Start the backend
uvicorn backend.main:app --reload

# 4. Open the dashboard
# Open frontend/index.html in your browser
```

---

## Project at a Glance

- **Model:** Gaussian Hidden Markov Model (HMM) with 2–6 regimes, selected via BIC
- **Features:** returns, volatility, RSI, momentum, VIX
- **Output:** Safe / High Risk signal with confidence score
- **Backend:** FastAPI (Python)
- **Frontend:** Vanilla HTML/CSS/JS with Plotly charts
- **CI:** GitHub Actions validates training pipeline on every push
