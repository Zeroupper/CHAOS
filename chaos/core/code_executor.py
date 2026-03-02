"""Centralized code execution for CHAOS agents."""

import contextlib
import io
import json
import pickle
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..data.registry import DataRegistry
from ..types import ExecutionResult
from .config import Config
from .logger import get_logger

_SANDBOX_IMAGE = "chaos-sandbox"
_CONTAINER_TIMEOUT = 30


def serialize_result(result: Any) -> str:
    if isinstance(result, (pd.DataFrame, pd.Series)):
        return result.to_json(default_handler=str)
    return str(result)


class CodeExecutor:
    """Executes LLM-generated Python code against registered data sources.

    Keeps raw step results in memory so subsequent steps can reference them
    directly. Routes to sandbox (Docker) or direct (in-process) execution
    depending on ``config.sandbox``.
    """

    def __init__(self, config: Config, data_registry: DataRegistry) -> None:
        self._config = config
        self._registry = data_registry
        self._logger = get_logger("CodeExecutor")
        self._step_results: dict[str, Any] = {}

    def execute(self, code: str, step_num: int | None = None, capture_stdout: bool = False) -> ExecutionResult:
        if self._config.sandbox:
            return self._execute_sandboxed(code, step_num)
        return self._execute_direct(code, step_num, capture_stdout)

    def _execute_sandboxed(self, code: str, step_num: int | None = None) -> ExecutionResult:
        payload = json.dumps({"code": code})
        datasets_path = str(self._config.datasets_dir.resolve())

        with tempfile.TemporaryDirectory() as step_dir:
            for name, value in self._step_results.items():
                with open(Path(step_dir) / f"{name}.pkl", "wb") as f:
                    pickle.dump(value, f)

            cmd = [
                "docker", "run", "--rm", "-i",
                "--network=none",
                "-v", f"{datasets_path}:/data:ro",
                "-v", f"{step_dir}:/step_results",
                _SANDBOX_IMAGE,
            ]
            self._logger.info(f"Spinning up sandbox container (image={_SANDBOX_IMAGE})")

            try:
                proc = subprocess.run(cmd, input=payload, capture_output=True, text=True, timeout=_CONTAINER_TIMEOUT)
            except FileNotFoundError:
                return ExecutionResult(error="Docker is not installed or not in PATH")
            except subprocess.TimeoutExpired:
                return ExecutionResult(error=f"Sandbox execution timed out after {_CONTAINER_TIMEOUT}s")

            if proc.returncode != 0:
                return ExecutionResult(error=f"Sandbox container failed (exit {proc.returncode}): {proc.stderr.strip()}")

            try:
                output = json.loads(proc.stdout)
            except json.JSONDecodeError:
                return ExecutionResult(error=f"Sandbox returned invalid JSON: {proc.stdout[:1000]}")

            if output.get("error"):
                self._logger.error(f"Sandbox exec failed: {output['error']}")
                return ExecutionResult(error=output["error"])

            result_path = Path(step_dir) / "result.pkl"
            if not result_path.exists():
                return ExecutionResult(error="Sandbox did not produce a result file")

            with open(result_path, "rb") as f:
                raw = pickle.load(f)

        if step_num is not None and raw is not None:
            self._step_results[f"step_{step_num}_result"] = raw
        return ExecutionResult(result=serialize_result(raw))

    def _execute_direct(self, code: str, step_num: int | None = None, capture_stdout: bool = False) -> ExecutionResult:
        namespace: dict[str, Any] = {
            "pd": pd, "np": np, "result": None,
            **{n: df.copy() for n, df in self._registry.get_all_dataframes().items()},
            **self._step_results,
        }
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf) if capture_stdout else contextlib.nullcontext():
                exec(code, namespace)
            raw = namespace.get("result")
            if raw is None and capture_stdout:
                stdout = buf.getvalue().strip()
                if stdout:
                    return ExecutionResult(result=stdout)
            if step_num is not None and raw is not None:
                self._step_results[f"step_{step_num}_result"] = raw
            return ExecutionResult(result=serialize_result(raw))
        except Exception as e:
            self._logger.error(f"Exec failed: {e}")
            return ExecutionResult(error=f"Code execution failed: {e}")

    # -- step result management --

    def describe_step_results(self) -> str:
        if not self._step_results:
            return "\nNo previous step results available. Do NOT reference any step_N_result variables."
        lines = []
        for name, val in sorted(self._step_results.items()):
            hint = type(val).__name__
            if isinstance(val, pd.DataFrame):
                hint = f"DataFrame{val.shape}"
            elif isinstance(val, pd.Series):
                hint = f"Series(len={len(val)})"
            lines.append(f"- `{name}` ({hint}): {str(val)[:200]}")
        return (
            "\nAvailable step results (ONLY these variables exist — do not reference any others):\n"
            + "\n".join(lines)
        )

    def reset_step(self, step_num: int) -> None:
        self._step_results.pop(f"step_{step_num}_result", None)

    def reset(self) -> None:
        self._step_results.clear()
