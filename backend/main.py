"""FastAPI service for the trained 13-feature car-price pipeline."""

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import PredictionRequest, PredictionResponse


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = Path(os.getenv("CAR_MODEL_PATH", ROOT / "models" / "car_price_model.joblib"))
METADATA_PATH = Path(os.getenv("CAR_MODEL_METADATA", ROOT / "models" / "model_metadata.json"))
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("car-price-api")
app_state = {"model": None, "metadata": None}


def _origins():
    configured = os.getenv(
        "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not MODEL_PATH.is_file() or not METADATA_PATH.is_file():
        raise RuntimeError(
            "The trained model artifacts are missing. Run `python -m backend.train_model` first."
        )
    try:
        app_state["model"] = joblib.load(MODEL_PATH)
        app_state["metadata"] = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        expected = app_state["metadata"].get("features", [])
        actual = list(getattr(app_state["model"], "feature_names_in_", []))
        if not expected or expected != actual:
            raise ValueError("Model input columns do not match the saved metadata.")
    except Exception as exc:
        logger.exception("Model artifacts could not be loaded")
        raise RuntimeError("Could not load the trained model artifacts.") from exc
    yield
    app_state["model"] = None
    app_state["metadata"] = None


app = FastAPI(
    title="Car Price Prediction API",
    version="1.0.0",
    description="Estimates used-car listing prices from 13 vehicle details.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _model_options():
    metadata = app_state.get("metadata")
    if not metadata:
        raise HTTPException(status_code=503, detail="Prediction service is starting up.")
    return metadata["options"]


def _format_inr(value):
    amount = str(int(round(float(value))))
    if len(amount) <= 3:
        return f"₹{amount}"
    leading, last = amount[:-3], amount[-3:]
    groups = []
    while leading:
        groups.insert(0, leading[-2:])
        leading = leading[:-2]
    return "₹" + ",".join(groups + [last])


@app.get("/api/health")
def health():
    return {
        "status": "ok" if app_state.get("model") is not None else "unavailable",
        "model_loaded": app_state.get("model") is not None,
    }


@app.get("/api/options")
def get_options():
    return _model_options()


@app.post("/api/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    if app_state.get("model") is None:
        raise HTTPException(status_code=503, detail="Prediction service is unavailable.")
    options = _model_options()
    companies = {item["value"]: item for item in options["companies"]}
    selected_company = companies.get(request.company)
    if selected_company is None:
        raise HTTPException(status_code=422, detail="Choose a company from the available options.")
    if request.model not in {item["value"] for item in selected_company["models"]}:
        raise HTTPException(
            status_code=422,
            detail="Choose a car model that belongs to the selected company.",
        )

    vehicle_age = options["reference_year"] - request.year_of_purchase
    if vehicle_age < 0 or vehicle_age > 100:
        raise HTTPException(status_code=422, detail="Year of purchase must be between 100 years ago and the reference year.")
    if request.fuel_type not in options["fuel_options"]:
        raise HTTPException(status_code=422, detail="Choose a fuel type available in the training data.")
    if request.transmission not in options["transmission_options"]:
        raise HTTPException(status_code=422, detail="Choose a transmission type available in the training data.")
    for field, option_key in (("owner_type", "owner_options"), ("city", "city_options"), ("seller_type", "seller_options")):
        if getattr(request, field) not in options[option_key]:
            raise HTTPException(status_code=422, detail=f"Choose a {field.replace('_', ' ')} available in the training data.")
    input_values = {
        "company": request.company,
        "model": request.model,
        "vehicle_age": vehicle_age,
        "fuel_type": request.fuel_type,
        "transmission": request.transmission,
        "owner_type": request.owner_type,
        "city": request.city,
        "seller_type": request.seller_type,
        "km_driven": request.km_driven,
        "mileage": request.mileage,
        "seating_capacity": request.seating_capacity,
        "horsepower": request.horsepower,
        "engine_cc": request.engine_cc,
    }
    try:
        ordered = app_state["metadata"]["features"]
        row = pd.DataFrame([{key: input_values[key] for key in ordered}], columns=ordered)
        estimate = float(app_state["model"].predict(row)[0])
        if not np.isfinite(estimate):
            raise ValueError("Non-finite model result")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Prediction failed")
        raise HTTPException(
            status_code=500,
            detail="We could not estimate this car right now. Please try again.",
        ) from None

    estimate = max(0.0, estimate)
    return PredictionResponse(
        predicted_price_inr=round(estimate, 2),
        formatted_price_inr=_format_inr(estimate),
        inputs=request,
        reference_year=options["reference_year"],
    )
