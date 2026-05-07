from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


DATASET_DIR = Path("data/ml/business/datasets")
MODEL_DIR = Path("data/ml/business/models")
REPORT_DIR = Path("data/ml/business/reports")


def _load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    return json.loads(path.read_text(encoding="utf-8"))


def load_training_data(company_id: str) -> pd.DataFrame:
    real_path = DATASET_DIR / f"{company_id}.json"
    simulated_path = DATASET_DIR / f"{company_id}_simulated.json"

    real_rows = _load_json(real_path)
    simulated_rows = _load_json(simulated_path)

    for row in real_rows:
        row.setdefault("company_id", company_id)
        row.setdefault("source", "real")
        row.setdefault("hour", -1)

    rows = real_rows + simulated_rows

    if not rows:
        raise RuntimeError("Nenhum dado disponível para treino.")

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["campaign_id", "label"])

    df["discount_value"] = pd.to_numeric(df.get("discount_value", 0), errors="coerce").fillna(0)
    df["has_discount"] = pd.to_numeric(df.get("has_discount", 0), errors="coerce").fillna(0)
    df["hour"] = pd.to_numeric(df.get("hour", -1), errors="coerce").fillna(-1)
    df["label"] = pd.to_numeric(df["label"], errors="coerce").fillna(0).astype(int)

    return df


def evaluate_model(model: Pipeline, x_test: pd.DataFrame, y_test: pd.Series) -> dict[str, float]:
    predictions = model.predict(x_test)

    result = {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "precision": round(float(precision_score(y_test, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, predictions, zero_division=0)), 4),
    }

    if hasattr(model, "predict_proba") and len(set(y_test)) > 1:
        probabilities = model.predict_proba(x_test)[:, 1]
        result["roc_auc"] = round(float(roc_auc_score(y_test, probabilities)), 4)
    else:
        result["roc_auc"] = 0.0

    return result


def train(company_id: str) -> dict[str, Any]:
    df = load_training_data(company_id)

    class_counts = df["label"].value_counts().to_dict()
    if len(class_counts) < 2:
        raise RuntimeError(f"Dataset possui apenas uma classe: {class_counts}")

    features = ["campaign_id", "discount_value", "has_discount", "hour"]
    target = "label"

    x = df[features]
    y = df[target]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), ["campaign_id"]),
            ("numeric", "passthrough", ["discount_value", "has_discount", "hour"]),
        ]
    )

    candidates = {
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=6,
            random_state=42,
            class_weight="balanced",
        ),
        "gradient_boosting": GradientBoostingClassifier(
            random_state=42,
        ),
    }

    results = {}

    best_name = None
    best_score = -1.0
    best_pipeline = None

    for name, estimator in candidates.items():
        pipeline = Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("model", estimator),
            ]
        )

        pipeline.fit(x_train, y_train)
        metrics = evaluate_model(pipeline, x_test, y_test)
        results[name] = metrics

        score = metrics["f1"]
        if score > best_score:
            best_score = score
            best_name = name
            best_pipeline = pipeline

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    model_path = MODEL_DIR / f"{company_id}_conversion_model.joblib"
    report_path = REPORT_DIR / f"{company_id}_training_report.json"

    joblib.dump(best_pipeline, model_path)

    report = {
        "company_id": company_id,
        "total_rows": int(len(df)),
        "class_counts": {str(k): int(v) for k, v in class_counts.items()},
        "source_counts": {str(k): int(v) for k, v in df["source"].value_counts().to_dict().items()},
        "features": features,
        "models": results,
        "best_model": best_name,
        "best_model_path": str(model_path),
    }

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


if __name__ == "__main__":
    output = train("FLX-001")
    print(json.dumps(output, ensure_ascii=False, indent=2))
