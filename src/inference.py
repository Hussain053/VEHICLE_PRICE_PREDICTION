"""Input validation shared by the web app and lightweight project checks."""

import pandas as pd


def build_input_row(values, expected_features):
    """Validate one submitted car and preserve the pipeline's feature order."""
    missing = [name for name in expected_features if name not in values]
    if missing:
        raise ValueError(f"Missing required car details: {missing}")
    row = pd.DataFrame([{name: values[name] for name in expected_features}],
                       columns=expected_features)
    for name in ("myear", "km", "Seats", "Max Power Delivered"):
        if pd.isna(row.loc[0, name]):
            raise ValueError(f"{name} is required and must be numeric.")
        if float(row.loc[0, name]) < 0:
            raise ValueError(f"{name} cannot be negative.")
    if int(row.loc[0, "myear"]) != float(row.loc[0, "myear"]):
        raise ValueError("Manufacturing year must be a whole number.")
    return row


def format_inr(value):
    """Format a nonnegative integer using Indian digit grouping."""
    amount = str(int(round(float(value))))
    if len(amount) <= 3:
        return f"₹{amount}"
    last_three, leading = amount[-3:], amount[:-3]
    groups = []
    while leading:
        groups.insert(0, leading[-2:])
        leading = leading[:-2]
    return "₹" + ",".join(groups + [last_three])
