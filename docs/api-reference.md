# API Reference

Base URL: `http://127.0.0.1:8000`

Interactive docs (Swagger UI): `http://127.0.0.1:8000/docs`

---

## Endpoints

### GET `/api/health`

Returns backend and model status.

**Response**
```json
{
  "status": "ready",
  "model_loaded": true
}
```

If the model hasn't been trained yet:
```json
{
  "status": "model_not_loaded",
  "model_loaded": false
}
```

---

### GET `/api/model-info`

Returns metadata about the trained model including feature means per regime.

**Response**
```json
{
  "n_regimes": 6,
  "covariance_type": "full",
  "trained_at": "2026-03-18T10:00:00Z",
  "dataset_rows": 2342,
  "date_range": "2015-03-05 to 2024-06-24",
  "train_split": "80/20",
  "features": ["returns", "volatility", "RSI", "momentum", "VIX"],
  "regime_means": {
    "0": { "returns": 0.0008, "volatility": 0.006, "RSI": 61.2, "momentum": 18.4, "VIX": 13.82 },
    "3": { "returns": -0.021, "volatility": 0.038, "RSI": 31.5, "momentum": -187.3, "VIX": 46.29 }
  },
  "regime_legend": {
    "0": { "label": "Low Risk", "avg_vix": 13.82 },
    "3": { "label": "High Risk", "avg_vix": 46.29 }
  }
}
```

---

### POST `/api/market-status`

Analyzes an uploaded CSV file and returns regime predictions for all rows.

**Query Parameters**

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `days` | int | 250 | 30–2000 | Number of recent rows to include in chart_data |

**Request**
- Content-Type: `multipart/form-data`
- Body: `file` — a `.csv` file

**Response**
```json
{
  "current_status": "Safe to Invest (Bull/Calm Market)",
  "current_regime_id": 4,
  "confidence": 39.9,
  "transition_warning": false,
  "latest_vix": 13.33,
  "n_regimes": 6,
  "regime_legend": {
    "0": { "label": "Low Risk",  "avg_vix": 13.82 },
    "1": { "label": "High Risk", "avg_vix": 20.61 },
    "2": { "label": "Low Risk",  "avg_vix": 12.05 },
    "3": { "label": "High Risk", "avg_vix": 46.29 },
    "4": { "label": "Low Risk",  "avg_vix": 17.34 },
    "5": { "label": "High Risk", "avg_vix": 27.57 }
  },
  "analyzed_at": "2026-03-18T10:00:00Z",
  "summary": {
    "total_rows": 2342,
    "date_range": "2015-03-05 to 2024-06-24",
    "safe_pct": 63.3,
    "risk_pct": 36.7,
    "riskiest_period": {
      "days": 102,
      "start_date": "2020-02-24",
      "end_date": "2020-07-17"
    }
  },
  "chart_data": {
    "dates":   ["2023-01-03", "2023-01-04", "..."],
    "prices":  [3824.14, 3852.97, "..."],
    "regimes": [4, 4, 2, "..."],
    "vix":     [21.13, 20.87, "..."]
  }
}
```

**Error responses**

| Code | Reason |
|------|--------|
| 400 | Not a CSV file |
| 400 | Missing required columns |
| 400 | Could not parse CSV |
| 503 | Model not loaded |

---

### GET `/api/last-result`

Returns the cached result of the most recent CSV analysis (in-memory, resets on server restart).

**Response:** Same schema as `/api/market-status`

**Error:** `404` if no analysis has been run yet.

---

### POST `/api/manual-check`

Predicts the market regime for a single set of manually entered feature values.

**Request body**
```json
{
  "returns":    0.0012,
  "volatility": 0.0085,
  "RSI":        58.4,
  "momentum":   0.032,
  "VIX":        16.5
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `returns` | float | any |
| `volatility` | float | any |
| `RSI` | float | 0–100 |
| `momentum` | float | any |
| `VIX` | float | ≥ 0 |

**Response**
```json
{
  "current_status":    "Safe to Invest (Bull/Calm Market)",
  "current_regime_id": 2,
  "confidence":        84.3,
  "latest_vix":        16.5,
  "n_regimes":         6,
  "regime_legend":     { "...": "..." },
  "analyzed_at":       "2026-03-18T10:05:00Z"
}
```

**Note:** Internally prepends 30 neutral warmup rows before prediction to give the Viterbi algorithm sequence context.

---

### POST `/api/batch-manual`

Predicts regimes for multiple rows at once.

**Request body**
```json
{
  "rows": [
    { "returns": 0.001, "volatility": 0.006, "RSI": 60, "momentum": 20, "VIX": 14 },
    { "returns": -0.05, "volatility": 0.04,  "RSI": 28, "momentum": -200, "VIX": 45 }
  ]
}
```

**Response**
```json
{
  "results": [
    {
      "input": { "returns": 0.001, "..." : "..." },
      "regime_id": 2,
      "label": "Low Risk",
      "current_status": "Safe to Invest (Bull/Calm Market)"
    },
    {
      "input": { "returns": -0.05, "...": "..." },
      "regime_id": 3,
      "label": "High Risk",
      "current_status": "High Risk (Move to Cash)"
    }
  ],
  "regime_legend": { "...": "..." }
}
```

---

### POST `/api/download-csv`

Returns the uploaded CSV with two extra columns: `Regime` (integer) and `Regime_Label` (string).

**Request:** Same as `/api/market-status` — multipart form with `file`

**Response:** `text/csv` file download — `market_data_with_regimes.csv`

---

### GET `/api/figures`

Lists available training plot filenames.

**Response**
```json
{
  "figures": [
    "Average_vix_by_market.png",
    "Drawdown_comparison.png",
    "HMM_Regime_Based_Trading_Strategy.png",
    "Market_regime_timeline.png",
    "Model_selection_using_AICbyBIC.png",
    "regime_overlay_plot.png",
    "RSI_Distribution_across_market_regimes.png",
    "SP500_Price_over_the_years.png",
    "transition_matrix.png",
    "Volatility_vs_Regime_plot.png"
  ]
}
```

---

### GET `/api/figures/{filename}`

Serves a specific training plot as a PNG image.

**Example:** `GET /api/figures/transition_matrix.png`

**Error:** `404` if the file doesn't exist.
