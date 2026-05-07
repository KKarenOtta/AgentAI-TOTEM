from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


MODEL_DIR = Path("data/ml/business/models")
_MODEL_CACHE: dict[str, Any] = {}


def load_model(company_id: str):
    if company_id in _MODEL_CACHE:
        return _MODEL_CACHE[company_id]

    model_path = MODEL_DIR / f"{company_id}_conversion_model.joblib"

    if not model_path.exists():
        _MODEL_CACHE[company_id] = None
        return None

    model = joblib.load(model_path)
    _MODEL_CACHE[company_id] = model
    return model


def predict_conversion_score(company_id: str, campaign: dict[str, Any]) -> float:
    model = load_model(company_id)

    if model is None:
        return 0.0

    try:
        discount_value = float(campaign.get("discount_value") or 0)
    except Exception:
        discount_value = 0.0

    row = {
        "campaign_id": campaign.get("campaign_id") or campaign.get("id") or campaign.get("code"),
        "discount_value": discount_value,
        "has_discount": 1 if discount_value > 0 else 0,
        "hour": datetime.now().hour,
    }

    frame = pd.DataFrame([row])

    try:
        probability = model.predict_proba(frame)[0][1]
    except Exception:
        return 0.0

    return round(float(probability), 4)
