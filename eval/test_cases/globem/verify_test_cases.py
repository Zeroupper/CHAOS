"""Ground truth expected answers for GLOBEM objective benchmark cases.

Each function computes the expected answer independently from the GLOBEM
INS-W_1 cohort. The OBJECTIVE_GROUND_TRUTH dict maps case IDs to
(compute_fn, expected_value).

"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATASETS_DIR = Path(
    "datasets/globem-dataset-multi-year-datasets-for-longitudinal-human-behavior-modeling-generalization-1.1"
)
COHORT = "INS-W_1"
PID = "INS-W_009"


def load(subdir: str, name: str) -> pd.DataFrame:
    """Load a CSV for the target participant."""
    df = pd.read_csv(DATASETS_DIR / COHORT / subdir / f"{name}.csv", low_memory=False)
    return df[df["pid"] == PID]


def load_all(subdir: str, name: str) -> pd.DataFrame:
    """Load a full CSV (all participants)."""
    return pd.read_csv(DATASETS_DIR / COHORT / subdir / f"{name}.csv", low_memory=False)


# ============================================================
# OBJECTIVE — Simple
# ============================================================


def obj_001() -> float:
    """Max screen unlock episodes in any 14-day period across all participants."""
    df = load_all("FeatureData", "screen")
    return float(df["f_screen:phone_screen_rapids_countepisodeunlock:14dhist"].max())


def obj_002() -> float:
    """Mean outgoing call count across all participants and 14-day periods."""
    df = load_all("FeatureData", "call")
    return round(float(df["f_call:phone_calls_rapids_outgoing_count:14dhist"].dropna().mean()), 4)


def obj_003() -> float:
    """Min unique Bluetooth devices in any 14-day period across all participants."""
    df = load_all("FeatureData", "bluetooth")
    return float(df["f_blue:phone_bluetooth_rapids_uniquedevices:14dhist"].min())


def obj_004() -> int:
    """Total number of records in the location dataset."""
    df = load_all("FeatureData", "location")
    return len(df)


def obj_005() -> int:
    """Total number of participants in INS-W_1."""
    df = load_all("ParticipantsInfoData", "platform")
    return len(df)


# ============================================================
# OBJECTIVE — Medium
# ============================================================


def obj_006() -> float:
    """Average sleep efficiency (main, 14-day rolling) for INS-W_009."""
    df = load("FeatureData", "sleep")
    return float(
        df["f_slp:fitbit_sleep_summary_rapids_avgefficiencymain:14dhist"].dropna().mean()
    )


def obj_007() -> float:
    """Percentage of participants using iOS in INS-W_1."""
    df = load_all("ParticipantsInfoData", "platform")
    return round((df["platform"] == "ios").sum() / len(df) * 100, 2)


def obj_008() -> int:
    """Number of participants flagged as depressed at end-of-term in INS-W_1."""
    df = load_all("SurveyData", "dep_endterm")
    return int(df["dep"].sum())


def obj_009() -> float:
    """Average BDI-II score at end-of-term across all participants in INS-W_1."""
    df = load_all("SurveyData", "dep_endterm")
    return round(float(df["BDI2"].dropna().mean()), 4)


def obj_010() -> float:
    """Pre-study PSS-10 score for INS-W_009."""
    df = load("SurveyData", "pre")
    return float(df["PSS_10items_PRE"].iloc[0])


# ============================================================
# OBJECTIVE — Complex
# ============================================================


def obj_011() -> float:
    """Difference in mean 14-day screen unlock count: depressed vs not-depressed at end-of-term."""
    dep = load_all("SurveyData", "dep_endterm")[["pid", "dep"]]
    screen = load_all("FeatureData", "screen")[["pid", "f_screen:phone_screen_rapids_countepisodeunlock:14dhist"]]
    merged = pd.merge(dep, screen, on="pid")
    col = "f_screen:phone_screen_rapids_countepisodeunlock:14dhist"
    means = merged.groupby("dep")[col].mean()
    return round(float(means[True] - means[False]), 4)


def obj_012() -> float:
    """BDI-II score of the participant with the highest avg 14-day intraday step count."""
    steps = load_all("FeatureData", "steps")[["pid", "f_steps:fitbit_steps_intraday_rapids_sumsteps:14dhist"]]
    per_pid = steps.groupby("pid")["f_steps:fitbit_steps_intraday_rapids_sumsteps:14dhist"].mean()
    top_pid = per_pid.idxmax()
    dep = load_all("SurveyData", "dep_endterm")
    row = dep[dep["pid"] == top_pid]
    if row.empty or pd.isna(row["BDI2"].iloc[0]):
        return -1.0
    return float(row["BDI2"].iloc[0])


def obj_013() -> float:
    """Pearson correlation: weekly feel_depressed vs weekly avg screen unlock for INS-W_009."""
    dep_w = load("SurveyData", "dep_weekly")[["date", "feel_depressed"]].copy()
    dep_w["date"] = pd.to_datetime(dep_w["date"])
    dep_w["iso_week"] = dep_w["date"].dt.isocalendar().week.astype(int)
    dep_w = dep_w[["iso_week", "feel_depressed"]].dropna()

    screen = load("FeatureData", "screen")[["date", "f_screen:phone_screen_rapids_countepisodeunlock:14dhist"]].copy()
    screen.columns = ["date", "unlocks"]
    screen["date"] = pd.to_datetime(screen["date"])
    screen["iso_week"] = screen["date"].dt.isocalendar().week.astype(int)
    weekly_screen = screen.groupby("iso_week")["unlocks"].mean().reset_index()

    merged = pd.merge(dep_w, weekly_screen, on="iso_week").dropna()
    return round(float(merged["feel_depressed"].corr(merged["unlocks"])), 4)


def obj_014() -> int:
    """Count of depressed participants with above-median avg screen unlock count."""
    screen = load_all("FeatureData", "screen")[["pid", "f_screen:phone_screen_rapids_countepisodeunlock:14dhist"]]
    per_pid = screen.groupby("pid")["f_screen:phone_screen_rapids_countepisodeunlock:14dhist"].mean().reset_index()
    per_pid.columns = ["pid", "screen_mean"]

    dep = load_all("SurveyData", "dep_endterm")[["pid", "dep"]]
    merged = pd.merge(per_pid, dep, on="pid")
    median_val = merged["screen_mean"].median()
    return int(((merged["dep"]) & (merged["screen_mean"] > median_val)).sum())


def obj_015() -> float:
    """Pearson correlation: pre-study PSS-10 vs avg 14-day sleep duration across participants."""
    sleep = load_all("FeatureData", "sleep")[["pid", "f_slp:fitbit_sleep_summary_rapids_sumdurationasleepmain:14dhist"]]
    per_pid = sleep.groupby("pid")["f_slp:fitbit_sleep_summary_rapids_sumdurationasleepmain:14dhist"].mean().reset_index()
    per_pid.columns = ["pid", "sleep_mean"]

    pre = load_all("SurveyData", "pre")[["pid", "PSS_10items_PRE"]]
    merged = pd.merge(per_pid, pre, on="pid").dropna()
    return round(float(merged["PSS_10items_PRE"].corr(merged["sleep_mean"])), 4)


# Maps objective case ID -> (compute_function, expected_value)
OBJECTIVE_GROUND_TRUTH: dict[str, tuple] = {
    "obj_001": (obj_001, 3955.0),
    "obj_002": (obj_002, 15.372),
    "obj_003": (obj_003, 1.0),
    "obj_004": (obj_004, 14260),
    "obj_005": (obj_005, 201),
    "obj_006": (obj_006, 92.5508),
    "obj_007": (obj_007, 79.6),
    "obj_008": (obj_008, 51),
    "obj_009": (obj_009, 12.8273),
    "obj_010": (obj_010, 28.0),
    "obj_011": (obj_011, 160.9465),
    "obj_012": (obj_012, 10.0),
    "obj_013": (obj_013, -0.5337),
    "obj_014": (obj_014, 27),
    "obj_015": (obj_015, -0.1096),
}


