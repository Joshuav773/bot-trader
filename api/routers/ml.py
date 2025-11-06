import os
from typing import Dict, Any

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from data_ingestion.polygon_client import PolygonDataClient
from ml_models.data_preprocessor import make_supervised
from ml_models.lstm_predictor import LstmPredictor


router = APIRouter()
_client = PolygonDataClient()

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ml_models", "artifacts")
ARTIFACT_DIR = os.path.abspath(ARTIFACT_DIR)
os.makedirs(ARTIFACT_DIR, exist_ok=True)


class TrainLstmRequest(BaseModel):
    ticker: str = Field(..., examples=["AAPL"])
    start_date: str = Field(..., examples=["2023-01-01"])
    end_date: str = Field(..., examples=["2023-12-31"])
    window: int = 50
    horizon: int = 1
    units: int = 32
    epochs: int = 10
    batch_size: int = 32


@router.post("/train/lstm")
def train_lstm(req: TrainLstmRequest) -> Dict[str, Any]:
    try:
        df = _client.get_daily_bars(req.ticker, req.start_date, req.end_date)
        if df.empty:
            raise HTTPException(status_code=404, detail="No data for range")

        series = df["Close"].astype("float32")
        X, y = make_supervised(series, window=req.window, horizon=req.horizon)
        if len(X) < 10:
            raise HTTPException(status_code=400, detail="Not enough samples after windowing")

        model = LstmPredictor(window=req.window, units=req.units)
        history = model.fit(X, y, epochs=req.epochs, batch_size=req.batch_size)
        val_loss = float(history.history.get("val_loss", [np.nan])[-1]) if "val_loss" in history.history else None
        train_loss = float(history.history.get("loss", [np.nan])[-1])

        model_id = f"lstm_{req.ticker}_{req.start_date}_{req.end_date}_w{req.window}_h{req.horizon}_u{req.units}".replace(" ", "")
        filepath = os.path.join(ARTIFACT_DIR, f"{model_id}.keras")
        model.model.save(filepath)

        return {
            "model_id": model_id,
            "artifact_path": filepath,
            "metrics": {"train_loss": train_loss, "val_loss": val_loss},
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PredictLstmRequest(BaseModel):
    model_id: str
    ticker: str
    end_date: str
    window: int = 50


@router.post("/predict/lstm")
def predict_lstm(req: PredictLstmRequest) -> Dict[str, Any]:
    try:
        # Lazy import - only load TensorFlow when this endpoint is called
        from tensorflow import keras

        filepath = os.path.join(ARTIFACT_DIR, f"{req.model_id}.keras")
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Model artifact not found")

        df = _client.get_daily_bars(req.ticker, "2000-01-01", req.end_date)
        if len(df) < req.window:
            raise HTTPException(status_code=400, detail="Not enough data for prediction window")

        series = df["Close"].astype("float32")
        window_vals = series.values[-req.window :].reshape(1, req.window, 1)

        model = keras.models.load_model(filepath)
        pred = float(model.predict(window_vals, verbose=0).reshape(-1)[0])

        return {"model_id": req.model_id, "prediction": pred, "asof": str(series.index[-1])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
