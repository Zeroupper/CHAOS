"""In-container executor for sandboxed code execution.

Reads JSON from stdin, executes code, writes JSON result to stdout.
"""

import json
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


def serialize_result(result: object) -> tuple[str, bool]:
    """Serialize a result to a JSON string, matching base.py logic."""
    try:
        if hasattr(result, "to_dict"):
            result_str = json.dumps(result.to_dict())
        elif hasattr(result, "tolist"):
            result_str = json.dumps(result.tolist())
        else:
            result_str = json.dumps(result, default=str)
    except (TypeError, ValueError):
        result_str = str(result)

    max_chars = 5000
    truncated = len(result_str) > max_chars
    if truncated:
        result_str = result_str[:max_chars]

    return result_str, truncated


def main() -> None:
    try:
        raw = sys.stdin.read()
        request = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        json.dump({"result": None, "error": f"Invalid JSON input: {e}", "truncated": False}, sys.stdout)
        return

    code = request.get("code", "")
    primary_source = request.get("primary_source", "")

    if not code:
        json.dump({"result": None, "error": "No code provided", "truncated": False}, sys.stdout)
        return

    data_dir = Path("/data")
    datasets = load_datasets(data_dir)

    primary_df = datasets.get(primary_source)
    if primary_df is None and datasets:
        # Fall back to first available dataset
        primary_df = next(iter(datasets.values()))

    if primary_df is None:
        json.dump({"result": None, "error": "No datasets found in /data", "truncated": False}, sys.stdout)
        return

    namespace: dict[str, object] = {
        "df": primary_df.copy(),
        "pd": pd,
        "np": np,
        "result": None,
        **datasets,
    }

    try:
        exec(code, namespace)  # noqa: S102
    except Exception as e:
        json.dump({"result": None, "error": f"Code execution failed: {e}", "truncated": False}, sys.stdout)
        return

    result = namespace.get("result")
    result_str, truncated = serialize_result(result)
    json.dump({"result": result_str, "error": None, "truncated": truncated}, sys.stdout)


if __name__ == "__main__":
    main()
