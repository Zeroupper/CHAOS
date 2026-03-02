"""In-container executor for sandboxed code execution.

Reads JSON from stdin, executes code, writes result via pickle to /step_results/result.pkl.
Stdout only carries {"error": null} or {"error": "..."}.
"""

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def load_datasets(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Load all CSV files from the data directory."""
    datasets: dict[str, pd.DataFrame] = {}
    for csv_path in sorted(data_dir.glob("*.csv")):
        datasets[csv_path.stem] = pd.read_csv(csv_path)
    return datasets


def main() -> None:
    try:
        raw = sys.stdin.read()
        request = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        json.dump({"error": f"Invalid JSON input: {e}"}, sys.stdout)
        return

    code = request.get("code", "")
    if not code:
        json.dump({"error": "No code provided"}, sys.stdout)
        return

    datasets = load_datasets(Path("/data"))
    if not datasets:
        json.dump({"error": "No datasets found in /data"}, sys.stdout)
        return

    namespace: dict[str, object] = {
        "pd": pd,
        "np": np,
        "result": None,
        **datasets,
    }

    # Load step results from pickle files (written by host)
    step_dir = Path("/step_results")
    if step_dir.exists():
        for pkl_path in sorted(step_dir.glob("step_*_result.pkl")):
            with open(pkl_path, "rb") as f:
                namespace[pkl_path.stem] = pickle.load(f)

    try:
        exec(code, namespace)
    except Exception as e:
        json.dump({"error": f"Code execution failed: {e}"}, sys.stdout)
        return

    # Pickle the raw result back to the shared mount
    result = namespace.get("result")
    with open(step_dir / "result.pkl", "wb") as f:
        pickle.dump(result, f)

    json.dump({"error": None}, sys.stdout)


if __name__ == "__main__":
    main()
