# backend/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import joblib
import io
import os

app = FastAPI(title="Market Regime AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Construct absolute paths to the model artifacts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "../outputs/models/hmm_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "../outputs/models/scaler.pkl")

# Load artifacts
try:
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
except FileNotFoundError:
    print("CRITICAL: Model artifacts not found. Please run the Jupyter notebook first.")

@app.post("/api/market-status")
async def get_market_status(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    contents = await file.read()
    data = pd.read_csv(io.StringIO(contents.decode('utf-8')))
    
    features = ["returns", "volatility", "RSI", "momentum", "VIX"]
    if not all(col in data.columns for col in features):
        raise HTTPException(status_code=400, detail=f"CSV is missing required features: {features}")
    
    # Scale and Predict
    X_scaled = scaler.transform(data[features])
    data["Regime"] = model.predict(X_scaled)
    
    # Dynamic logic mapping
    regime_risk = data.groupby("Regime")["VIX"].mean().sort_values()
    safe_regimes = regime_risk.head(3).index.tolist()
    
    current_regime = int(data["Regime"].iloc[-1])
    is_safe = current_regime in safe_regimes
    status_message = "Safe to Invest (Bull/Calm Market)" if is_safe else "High Risk (Move to Cash)"
    
    # Send the last 250 trading days for the UI chart
    recent_data = data.tail(250) 
    
    return {
        "current_status": status_message,
        "current_regime_id": current_regime,
        "latest_vix": float(recent_data["VIX"].iloc[-1]),
        "chart_data": {
            "dates": recent_data["Date"].tolist(),
            "prices": recent_data["Close"].tolist(),
            "regimes": recent_data["Regime"].tolist()
        }
    }