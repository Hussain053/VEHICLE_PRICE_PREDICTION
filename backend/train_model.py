"""Train a car price model from the supplied CSV files."""

import json
import re
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import RandomizedSearchCV, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeRegressor


ROOT = Path(__file__).resolve().parents[1]
DATA_DETAILS = ROOT / "Dataset" / "cars_details_merges.csv"
DATA_TARGET = ROOT / "Dataset" / "cars_data_clean.csv"
MODEL_DIR = ROOT / "models"
REFERENCE_YEAR = 2026
RANDOM_STATE = 42
TARGET = "listed_price"
CATEGORICAL_FEATURES = [
    "company", "model", "fuel_type", "transmission", "owner_type", "city", "seller_type",
]
TOP_CITY_COUNT = 100
NUMERIC_FEATURES = [
    "vehicle_age",
    "km_driven",
    "mileage",
    "seating_capacity",
    "horsepower",
    "engine_cc",
]
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET_MAX_INR = 100_000_000


def _read_joined_data():
    if not DATA_DETAILS.exists() or not DATA_TARGET.exists():
        raise FileNotFoundError(
            "Required CSVs are missing. Keep cars_details_merges.csv and "
            "cars_data_clean.csv in the Dataset folder."
        )
    detail_columns = [
        "usedCarSkuId", "brand_name", "model_name", "myear", "km_driven",
        "fuel_type_new", "transmission_type_new", "owner_type_new",
        "city_name_new", "seller_type_new",
        "mileage_new", "seating_capacity_new", "Max Power", "Displacement",
    ]
    details = pd.read_csv(DATA_DETAILS, usecols=detail_columns, low_memory=False)
    targets = pd.read_csv(DATA_TARGET, usecols=["usedCarSkuId", TARGET])
    return details.merge(
        targets, on="usedCarSkuId", how="inner", validate="one_to_one"
    )


def parse_horsepower(series):
    """Read the leading value and convert the recorded unit to bhp."""
    values = pd.to_numeric(
        series.astype("string").str.extract(r"^\s*([0-9]+(?:\.[0-9]+)?)")[0],
        errors="coerce",
    )
    unit = series.astype("string").str.extract(r"([A-Za-z]+)\s*@?")[0].str.lower()
    factors = {"bhp": 1.0, "hp": 1.0, "ps": 0.9863200706, "kw": 1.34102209}
    multiplier = unit.map(factors)
    return values * multiplier


def prepare_training_data(details=None):
    """Join targets, normalize units, and keep complete supported observations."""
    frame = _read_joined_data() if details is None else details.copy()
    initial_rows = len(frame)
    frame[TARGET] = pd.to_numeric(frame[TARGET], errors="coerce")
    mileage_text = frame["mileage_new"].astype("string")
    mileage_unit = mileage_text.str.extract(r"([A-Za-z/]+)\s*$")[0].str.lower()
    mileage = pd.to_numeric(
        mileage_text.str.extract(r"^\s*([0-9]+(?:\.[0-9]+)?)")[0],
        errors="coerce",
    )
    work = pd.DataFrame(index=frame.index)
    work["company"] = frame["brand_name"].astype("string").str.strip().str.lower()
    work["model"] = frame["model_name"].astype("string").str.strip().str.lower()
    work["fuel_type"] = frame["fuel_type_new"].astype("string").str.strip().str.lower()
    work["transmission"] = frame["transmission_type_new"].astype("string").str.strip().str.lower()
    work["owner_type"] = frame["owner_type_new"].astype("string").str.strip().str.lower()
    work["seller_type"] = frame["seller_type_new"].astype("string").str.strip().str.lower()
    normalized_cities = frame["city_name_new"].astype("string").str.strip().str.lower()
    top_cities = set(normalized_cities.value_counts().head(TOP_CITY_COUNT).index)
    work["city"] = normalized_cities.where(normalized_cities.isin(top_cities), "other")
    work["vehicle_age"] = REFERENCE_YEAR - pd.to_numeric(frame["myear"], errors="coerce")
    work["km_driven"] = pd.to_numeric(frame["km_driven"], errors="coerce")
    work["mileage"] = mileage.where(mileage_unit.eq("kmpl"))
    work["seating_capacity"] = pd.to_numeric(
        frame["seating_capacity_new"], errors="coerce"
    )
    work["horsepower"] = parse_horsepower(frame["Max Power"])
    work["engine_cc"] = pd.to_numeric(frame["Displacement"], errors="coerce")
    work[TARGET] = frame[TARGET]

    valid = (
        work[FEATURES].notna().all(axis=1)
        & work[TARGET].between(1, TARGET_MAX_INR)
        & work["km_driven"].ge(0)
        & work["mileage"].gt(0)
        & work["seating_capacity"].gt(0)
        & work["horsepower"].gt(0)
        # Values under 100cc are malformed in this file (one electric e2o row
        # was recorded as 48cc); real EVs are already recorded as zero cc.
        & work["engine_cc"].ge(100)
        & work["vehicle_age"].between(0, 100)
    )
    usable = work.loc[valid].copy()
    usable["seating_capacity"] = usable["seating_capacity"].astype(int)
    usable["vehicle_age"] = usable["vehicle_age"].astype(int)
    usable["km_driven"] = usable["km_driven"].astype(int)
    X = usable[FEATURES].reset_index(drop=True)
    y = usable[TARGET].astype(float).reset_index(drop=True)
    audit = {
        "joined_rows": initial_rows,
        "usable_rows": len(usable),
        "excluded_rows": initial_rows - len(usable),
        "unsupported_or_missing_mileage_rows": int((~mileage_unit.eq("kmpl")).sum()),
        "missing_mileage_rows": int(mileage.isna().sum()),
        "zero_engine_displacement_rows": int(
            pd.to_numeric(frame["Displacement"], errors="coerce").eq(0).sum()
        ),
        "malformed_engine_displacement_under_100cc_rows": int(
            pd.to_numeric(frame["Displacement"], errors="coerce").between(0, 100, inclusive="left").sum()
        ),
        "target_outlier_rule": f"1 <= listed_price <= {TARGET_MAX_INR} INR",
        "age_reference_year": REFERENCE_YEAR,
        "features": FEATURES,
    }
    return X, y, audit


def make_pipeline(estimator, dense=False):
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=not dense)),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
        sparse_threshold=0 if dense else 0.3,
    )
    return Pipeline([("preprocessor", preprocessor), ("model", estimator)])


def _model_and_dense(name):
    if name == "Random Forest":
        return RandomForestRegressor(
            n_estimators=80,
            min_samples_leaf=2,
            max_features=0.8,
            n_jobs=-1,
            random_state=RANDOM_STATE,
        ), False
    if name == "HistGradientBoosting":
        return HistGradientBoostingRegressor(
            max_iter=100,
            max_leaf_nodes=15,
            learning_rate=0.08,
            l2_regularization=1.0,
            random_state=RANDOM_STATE,
        ), True
    if name == "Decision Tree":
        return DecisionTreeRegressor(min_samples_leaf=5, random_state=RANDOM_STATE), False
    if name == "Linear Regression":
        return LinearRegression(), False
    return DummyRegressor(strategy="median"), False


def _metrics(actual, predicted):
    mse = mean_squared_error(actual, predicted)
    return {
        "MAE_INR": float(mean_absolute_error(actual, predicted)),
        "RMSE_INR": float(np.sqrt(mse)),
        "MSE_INR2": float(mse),
        "R2": float(r2_score(actual, predicted)),
    }


def _format_brand(value):
    name = str(value).title()
    special = {
        "Bmw": "BMW", "Mg": "MG", "Dc": "DC", "Mini": "MINI",
        "Icml": "ICML", "Maruti": "Maruti Suzuki",
    }
    return special.get(name, name)


def _model_label(value, brand):
    text = str(value).strip()
    prefix = str(brand).strip() + " "
    if text.lower().startswith(prefix.lower()):
        text = text[len(prefix):]
    return text.title()


def main():
    warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
    X, y, audit = prepare_training_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )
    candidates = [
        "Dummy Median", "Linear Regression", "Decision Tree",
        "Random Forest", "HistGradientBoosting",
    ]
    rows = []
    for name in candidates:
        estimator, dense = _model_and_dense(name)
        scores = cross_validate(
            make_pipeline(estimator, dense=dense), X_train, y_train, cv=3,
            scoring={"mae": "neg_mean_absolute_error", "r2": "r2"},
            n_jobs=1, return_train_score=False,
        )
        rows.append({
            "Model": name,
            "CV_MAE_INR": float(-scores["test_mae"].mean()),
            "CV_MAE_STD_INR": float(scores["test_mae"].std()),
            "CV_R2": float(scores["test_r2"].mean()),
        })
    comparison = pd.DataFrame(rows).sort_values("CV_MAE_INR").reset_index(drop=True)
    best_name = comparison.loc[0, "Model"]
    best_estimator, dense = _model_and_dense(best_name)
    base_pipeline = make_pipeline(best_estimator, dense=dense)

    if best_name == "Random Forest":
        search_space = {
            "model__n_estimators": [60, 100, 140],
            "model__max_features": [0.6, 0.9, 1.0],
            "model__min_samples_leaf": [1, 2, 4],
        }
    elif best_name == "HistGradientBoosting":
        search_space = {
            "model__max_iter": [80, 120, 160],
            "model__max_leaf_nodes": [15, 31],
            "model__learning_rate": [0.05, 0.08, 0.12],
        }
    elif best_name == "Decision Tree":
        search_space = {
            "model__max_depth": [None, 12, 20],
            "model__min_samples_leaf": [2, 5, 10],
        }
    else:
        search_space = {
            "model__fit_intercept": [True, False],
        }
    search = RandomizedSearchCV(
        base_pipeline,
        search_space,
        n_iter=4,
        cv=3,
        scoring="neg_mean_absolute_error",
        random_state=RANDOM_STATE,
        n_jobs=-1,
        refit=True,
        verbose=1,
    )
    search.fit(X_train, y_train)
    tuned_cv_mae = float(-search.best_score_)
    untuned_cv_mae = float(
        comparison.loc[comparison["Model"] == best_name, "CV_MAE_INR"].iloc[0]
    )
    if tuned_cv_mae < untuned_cv_mae:
        final_model = search.best_estimator_
        final_model_name = f"Tuned {best_name}"
        final_cv_mae = tuned_cv_mae
    else:
        # Keep the simpler candidate when the search does not improve training CV.
        final_model = base_pipeline.fit(X_train, y_train)
        final_model_name = best_name
        final_cv_mae = untuned_cv_mae
    predictions = final_model.predict(X_test)
    test_metrics = _metrics(y_test, predictions)
    comparison = pd.concat(
        [comparison, pd.DataFrame([{
            "Model": f"Tuned {best_name}",
            "CV_MAE_INR": tuned_cv_mae,
            "CV_MAE_STD_INR": np.nan,
            "CV_R2": np.nan,
        }])], ignore_index=True
    ).sort_values("CV_MAE_INR").reset_index(drop=True)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / "car_price_model.joblib"
    joblib.dump(final_model, model_path, compress=3)
    comparison.to_csv(MODEL_DIR / "model_comparison.csv", index=False)
    pd.DataFrame({
        "actual_price": y_test,
        "predicted_price": predictions,
    }).to_csv(MODEL_DIR / "test_predictions.csv", index=False)

    numeric_limits = {}
    for name in NUMERIC_FEATURES:
        numeric_limits[name] = {
            "min": float(X_train[name].min()),
            "max": float(X_train[name].max()),
        }
    # Mileage and mileage units are consistent only after excluding non-kmpl rows.
    # Limit odometer entry to its training 99.5th percentile to avoid implausible UI values.
    numeric_limits["km_driven"]["max"] = int(X_train["km_driven"].quantile(0.995))
    brands = []
    for company, group in X_train.groupby("company", sort=True):
        model_values = sorted(group["model"].unique().tolist())
        brands.append({
            "value": company,
            "label": _format_brand(company),
            "models": [
                {"value": value, "label": _model_label(value, company)}
                for value in model_values
            ],
        })
    options = {
        "companies": brands,
        "fuel_options": sorted(str(value) for value in X_train["fuel_type"].dropna().unique()),
        "transmission_options": sorted(str(value) for value in X_train["transmission"].dropna().unique()),
        "owner_options": sorted(str(value) for value in X_train["owner_type"].dropna().unique()),
        "city_options": sorted(str(value) for value in X_train["city"].dropna().unique()),
        "seller_options": sorted(str(value) for value in X_train["seller_type"].dropna().unique()),
        "limits": numeric_limits,
        "seating_options": sorted(int(n) for n in X_train["seating_capacity"].unique()),
        "reference_year": REFERENCE_YEAR,
    }
    metadata = {
        "features": FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "reference_year": REFERENCE_YEAR,
        "target": TARGET,
        "selected_model": final_model_name,
        "best_params": search.best_params_,
        "untuned_cv_mae_inr": untuned_cv_mae,
        "tuned_cv_mae_inr": tuned_cv_mae,
        "selected_cv_mae_inr": final_cv_mae,
        "test_metrics": test_metrics,
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "audit": audit,
        "options": options,
    }
    (MODEL_DIR / "model_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    reloaded = joblib.load(model_path)
    sample_prediction = float(reloaded.predict(X_test.iloc[[0]])[0])
    if not np.isfinite(sample_prediction):
        raise RuntimeError("The saved model did not produce a finite sample prediction.")
    print("Cross-validation comparison:")
    print(comparison.to_string(index=False))
    print("Selected model:", final_model_name)
    print("Best parameters:", search.best_params_)
    print("Held-out test metrics:", json.dumps(test_metrics, indent=2))
    print("Data audit:", json.dumps(audit, indent=2))
    print("Saved pipeline:", model_path, "bytes:", model_path.stat().st_size)
    print("Reloaded sample prediction:", sample_prediction)
    return comparison, test_metrics


if __name__ == "__main__":
    main()
