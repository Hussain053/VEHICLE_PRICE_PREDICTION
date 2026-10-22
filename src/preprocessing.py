"""Dataset loading, quality checks, and reusable preprocessing pipeline."""

from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_ROOT / "Dataset" / "cars_data_clean.csv"
TARGET = "listed_price"
NUMERIC_FEATURES = ["myear", "km", "Seats", "Max Power Delivered"]
CATEGORICAL_FEATURES = [
    "oem", "model", "body", "transmission", "fuel", "owner_type"
]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def load_dataset(path=DEFAULT_DATA_PATH):
    """Load a CSV and fail early if the expected target/features are absent."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}. Place cars_data_clean.csv in Dataset/."
        )
    data = pd.read_csv(path)
    required = set(FEATURES + [TARGET])
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")
    return data


def prepare_data(data):
    """Remove unusable targets and clearly invalid records; return X, y, audit."""
    original_rows = len(data)
    work = data.copy()
    work[TARGET] = pd.to_numeric(work[TARGET], errors="coerce")
    work = work.dropna(subset=[TARGET])
    # A 550-million-rupee EcoSport entry is a clear data-entry anomaly. The
    # 100-million ceiling preserves the other premium listings in this file.
    work = work.loc[work[TARGET].between(1, 100_000_000)]
    work = work.loc[work["myear"].between(1980, 2026)]
    work = work.loc[work["km"].ge(0)]
    # Keep one copy of exact duplicate listings, if any are present.
    work = work.drop_duplicates()
    X = work[FEATURES].copy()
    y = work[TARGET].astype(float).copy()
    audit = {
        "input_rows": original_rows,
        "usable_rows": len(work),
        "dropped_rows": original_rows - len(work),
        "target_missing_rows": int(data[TARGET].isna().sum()),
        "target_outlier_rule": "1 <= listed_price <= 100,000,000 INR",
        "features": FEATURES.copy(),
    }
    return X, y, audit


def make_preprocessor():
    """Create a train-fitted transformer safe for missing and new categories."""
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
