"""Ground truth expected answers for Gloss sample objective benchmark cases.

Each function computes the expected answer independently from the Gloss sample
dataset.  The OBJECTIVE_GROUND_TRUTH dict maps case IDs to (compute_fn, expected_value).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATASETS_DIR = Path("datasets/gloss_sample")
USER_ID = "test004"


def load(name: str) -> pd.DataFrame:
    """Load data for user test004."""
    df = pd.read_csv(DATASETS_DIR / f"{name}.csv")
    return df[df["uid"] == USER_ID]


def load_all(name: str) -> pd.DataFrame:
    """Load full CSV (all users)."""
    return pd.read_csv(DATASETS_DIR / f"{name}.csv")


def obj_001() -> float:
    """What was the highest heart rate recorded in the dataset?"""
    hr = load_all("garmin_hr")
    return float(hr["heart_rate"].max())


def obj_002() -> float:
    """How many total steps were taken according to the Garmin watch?"""
    steps = load_all("garmin_steps")
    return float(steps["steps"].sum())


def obj_003() -> int:
    """How many times was the phone unlocked?"""
    lock = load_all("ios_lock_unlock")
    return int((lock["lock_state"] == 1).sum())


def obj_004() -> int:
    """How many different apps were used on the phone?"""
    app = load_all("app_usage_logs")
    return int(app["appName"].nunique())


def obj_005() -> float:
    """What was the lowest resting heart rate for user test004, ignoring any invalid readings?"""
    hr = load("garmin_hr")
    valid = hr[hr["heart_rate"] > 0]["heart_rate"]
    return float(valid.min())


def obj_006() -> int:
    """How many different WiFi networks did user test004's phone connect to?"""
    wifi = load("ios_wifi")
    valid = wifi[wifi["ssid"].notna() & (wifi["ssid"] != "nil")]
    return int(valid["ssid"].nunique())


def obj_007() -> float:
    """What is the difference between the highest and lowest valid heart rate values recorded for user test004?"""
    hr = load("garmin_hr")
    valid = hr[hr["heart_rate"] > 0]["heart_rate"]
    return float(valid.max() - valid.min())


def obj_008() -> float:
    """What was the average heart rate measured by the stress sensor during 'VALID' readings for user test004?"""
    stress = load("garmin_stress")
    valid = stress[stress["status"] == "VALID"]
    return float(valid["heart_rate"].mean())


def obj_009() -> float:
    """What was the average heart rate for user test004 during walking periods?

    Match heart rate readings within 30 seconds of each walking activity event.
    """
    hr = load("garmin_hr")
    act = load("ios_activity")

    valid_hr = hr[hr["heart_rate"] > 0]
    walking = act[act["activity"].str.contains("walking", case=False)]

    matched_ids: set[str] = set()
    for _, row in walking.iterrows():
        ts = row["timestamp"]
        nearby = valid_hr[
            (valid_hr["timestamp"] >= ts - 30)
            & (valid_hr["timestamp"] <= ts + 30)
        ]
        matched_ids.update(nearby["_id"].tolist())

    matched_hr = valid_hr[valid_hr["_id"].isin(matched_ids)]
    return float(matched_hr["heart_rate"].mean())


def obj_010() -> float:
    """What is the Pearson correlation between heart rate readings from the dedicated heart rate
    sensor and the stress sensor for user test004? Align readings by closest timestamp within 1 second.
    """
    hr = load("garmin_hr")
    stress = load("garmin_stress")

    hr_cols = hr[["timestamp", "heart_rate"]].rename(
        columns={"heart_rate": "garmin_hr"}
    )
    stress_cols = stress[["timestamp", "heart_rate"]].rename(
        columns={"heart_rate": "stress_hr"}
    )

    merged = pd.merge_asof(
        stress_cols.sort_values("timestamp"),
        hr_cols.sort_values("timestamp"),
        on="timestamp",
        tolerance=1,
    )
    merged = merged.dropna()
    return float(merged["stress_hr"].corr(merged["garmin_hr"]))


def obj_011() -> float:
    """What is the Pearson correlation between hourly step counts from the Garmin watch
    and the iPhone for user test004?
    """
    garmin = load("garmin_steps")
    ios = load("ios_steps")

    garmin["hour"] = pd.to_datetime(garmin["timestamp"], unit="s").dt.floor("h")
    g_hourly = garmin.groupby("hour")["steps"].sum().reset_index()

    ios["hour"] = pd.to_datetime(ios["start_timestamp"], unit="s").dt.floor("h")
    i_hourly = ios.groupby("hour")["steps"].sum().reset_index()

    merged = pd.merge(g_hourly, i_hourly, on="hour", suffixes=("_garmin", "_ios"))
    return float(merged["steps_garmin"].corr(merged["steps_ios"]))


# Maps objective case ID -> (compute_function, expected_value)
OBJECTIVE_GROUND_TRUTH: dict[str, tuple] = {
    "obj_001": (obj_001, 155.0),
    "obj_002": (obj_002, 14005.0),
    "obj_003": (obj_003, 334),
    "obj_004": (obj_004, 6),
    "obj_005": (obj_005, 48.0),
    "obj_006": (obj_006, 3),
    "obj_007": (obj_007, 107.0),
    "obj_008": (obj_008, 54.485),
    "obj_009": (obj_009, 105.0951),
    "obj_010": (obj_010, 0.8986),
    "obj_011": (obj_011, 0.4829),
}


