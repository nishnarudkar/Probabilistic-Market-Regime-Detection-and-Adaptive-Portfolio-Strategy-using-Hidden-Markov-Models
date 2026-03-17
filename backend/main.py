# backend/main.py
import json
import logging
import io
import os
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Market Regime AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH  = os.path.join(BASE_DIR, "../outputs/models/hmm_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "../outputs/models/scaler.pkl")
META_PATH   = os.path.join(BASE_DIR, "../outputs/models/model_metadata.json")
FIGURES_DIR = os.path.join(BASE_DIR, "../outputs/figures")

FEATURES = ["returns", "volatility", "RSI", "momentum", "VIX"]

model  = None
scaler = None
_last_result_cache: dict | None = None   # in-memory cache of last CSV result

try:
    model  = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    logger.info("Model artifacts loaded successfully.")
except FileNotFoundError:
    logger.critical("Model artifacts not found. Please run src/train.py first.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _classify_regimes(data: pd.DataFrame):
    regime_risk  = data.groupby("Regime")["VIX"].mean().sort_values()
    n            = model.n_components
    safe_regimes = regime_risk.head(max(1, n // 2 + 1)).index.tolist()
    legend = {
        int(rid): {"label": "Low Risk" if rid in safe_regimes else "High Risk",
                   "avg_vix": round(float(vix), 2)}
        for rid, vix in regime_risk.items()
    }
    return safe_regimes, legend


def _classify_regimes_from_means():
    vix_idx = FEATURES.index("VIX")
    means   = {i: float(model.means_[i][vix_idx]) for i in range(model.n_components)}
    sorted_ = sorted(means, key=lambda r: means[r])
    safe    = sorted_[: max(1, model.n_components // 2 + 1)]
    legend  = {i: {"label": "Low Risk" if i in safe else "High Risk",
                   "avg_vix": round(means[i], 2)}
               for i in range(model.n_components)}
    return safe, legend


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    ready = model is not None and scaler is not None
    return {"status": "ready" if ready else "model_not_loaded", "model_loaded": ready}


# ── Model Info ────────────────────────────────────────────────────────────────

@app.get("/api/model-info")
def model_info():
    """Returns metadata about the trained model."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")

    meta = {}
    if os.path.exists(META_PATH):
        with open(META_PATH) as f:
            meta = json.load(f)

    _, legend = _classify_regimes_from_means()
    return {
        "n_regimes":      model.n_components,
        "covariance_type": model.covariance_type,
        "regime_means":   {
            str(i): {feat: round(float(model.means_[i][j]), 6) for j, feat in enumerate(FEATURES)}
            for i in range(model.n_components)
        },
        "regime_legend":  legend,
        **meta,
    }


# ── CSV Upload ────────────────────────────────────────────────────────────────

@app.post("/api/market-status")
async def get_market_status(
    file: UploadFile = File(...),
    days: int = Query(default=250, ge=30, le=2000),
):
    global _last_result_cache

    if model is None or scaler is None:
        raise HTTPException(status_code=503, detail="Model not loaded. Run src/train.py first.")
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    contents = await file.read()
    logger.info(f"File: {file.filename} ({len(contents)} bytes), days={days}")

    try:
        data = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    required = ["Date", "Close"] + FEATURES
    missing  = [c for c in required if c not in data.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"CSV missing columns: {missing}")

    data["Regime"]  = model.predict(scaler.transform(data[FEATURES]))
    safe, legend    = _classify_regimes(data)
    current_regime  = int(data["Regime"].iloc[-1])
    is_safe         = current_regime in safe
    status_message  = "Safe to Invest (Bull/Calm Market)" if is_safe else "High Risk (Move to Cash)"
    recent          = data.tail(days)

    logger.info(f"Regime: {current_regime}, Status: {status_message}")

    result = {
        "current_status":    status_message,
        "current_regime_id": current_regime,
        "latest_vix":        float(recent["VIX"].iloc[-1]),
        "n_regimes":         model.n_components,
        "regime_legend":     legend,
        "analyzed_at":       datetime.utcnow().isoformat() + "Z",
        "chart_data": {
            "dates":   recent["Date"].tolist(),
            "prices":  recent["Close"].tolist(),
            "regimes": recent["Regime"].tolist(),
            "vix":     recent["VIX"].tolist(),
        },
    }
    _last_result_cache = result
    return result


# ── Last Result Cache ─────────────────────────────────────────────────────────

@app.get("/api/last-result")
def get_last_result():
    """Returns the cached result of the last CSV analysis."""
    if _last_result_cache is None:
        raise HTTPException(status_code=404, detail="No analysis has been run yet.")
    return _last_result_cache


# ── Manual Single Check ───────────────────────────────────────────────────────

class ManualInput(BaseModel):
    returns:    float = Field(..., description="Daily return")
    volatility: float = Field(..., description="Rolling volatility")
    RSI:        float = Field(..., ge=0, le=100)
    momentum:   float = Field(...)
    VIX:        float = Field(..., ge=0)


@app.post("/api/manual-check")
def manual_check(payload: ManualInput):
    if model is None or scaler is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")

    row    = np.array([[payload.returns, payload.volatility, payload.RSI, payload.momentum, payload.VIX]])
    regime = int(model.predict(scaler.transform(row))[0])
    safe, legend = _classify_regimes_from_means()
    is_safe = regime in safe
    status  = "Safe to Invest (Bull/Calm Market)" if is_safe else "High Risk (Move to Cash)"

    logger.info(f"Manual check — regime: {regime}, status: {status}")
    return {
        "current_status":    status,
        "current_regime_id": regime,
        "latest_vix":        payload.VIX,
        "n_regimes":         model.n_components,
        "regime_legend":     legend,
        "analyzed_at":       datetime.utcnow().isoformat() + "Z",
    }


# ── Batch Manual Check ────────────────────────────────────────────────────────

class BatchInput(BaseModel):
    rows: list[ManualInput]


@app.post("/api/batch-manual")
def batch_manual(payload: BatchInput):
    """Predict regime for multiple rows at once."""
    if model is None or scaler is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    if not payload.rows:
        raise HTTPException(status_code=400, detail="rows list is empty.")

    safe, legend = _classify_regimes_from_means()
    results = []
    for row in payload.rows:
        arr    = np.array([[row.returns, row.volatility, row.RSI, row.momentum, row.VIX]])
        regime = int(model.predict(scaler.transform(arr))[0])
        is_safe = regime in safe
        results.append({
            "input":             row.model_dump(),
            "regime_id":         regime,
            "label":             legend[regime]["label"],
            "current_status":    "Safe to Invest (Bull/Calm Market)" if is_safe else "High Risk (Move to Cash)",
        })

    logger.info(f"Batch check: {len(results)} rows processed.")
    return {"results": results, "regime_legend": legend}


# ── Figures ───────────────────────────────────────────────────────────────────

@app.get("/api/figures")
def list_figures():
    if not os.path.exists(FIGURES_DIR):
        return {"figures": []}
    files = sorted(f for f in os.listdir(FIGURES_DIR) if f.endswith(".png"))
    return {"figures": files}


@app.get("/api/figures/{filename}")
def get_figure(filename: str):
    path = os.path.join(FIGURES_DIR, os.path.basename(filename))
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Figure not found.")
    return FileResponse(path, media_type="image/png")
