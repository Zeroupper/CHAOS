"""Host-side bridge for sandboxed code execution via Docker."""

import json
import logging
import subprocess
from pathlib import Path

from ..types import ExecutionResult

logger = logging.getLogger(__name__)

SANDBOX_IMAGE = "chaos-sandbox"
CONTAINER_TIMEOUT = 30


def execute_sandboxed(
    code: str, primary_source: str, datasets_dir: Path
) -> ExecutionResult:
    """Execute code inside a Docker sandbox container.

    Args:
        code: Python code to execute (must set `result` variable).
        primary_source: Name of the primary dataset (stem of CSV file).
        datasets_dir: Host path to the datasets directory.

    Returns:
        ExecutionResult with the result or error.
    """
    payload = json.dumps({"code": code, "primary_source": primary_source})
    datasets_path = str(datasets_dir.resolve())

    cmd = [
        "docker", "run", "--rm", "-i",
        "--network=none",
        "-v", f"{datasets_path}:/data:ro",
        SANDBOX_IMAGE,
    ]

    logger.info(f"Spinning up sandbox container (image={SANDBOX_IMAGE}, source={primary_source})")

    try:
        proc = subprocess.run(
            cmd,
            input=payload,
            capture_output=True,
            text=True,
            timeout=CONTAINER_TIMEOUT,
        )
    except FileNotFoundError:
        return ExecutionResult(error="Docker is not installed or not in PATH")
    except subprocess.TimeoutExpired:
        return ExecutionResult(error=f"Sandbox execution timed out after {CONTAINER_TIMEOUT}s")

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        return ExecutionResult(error=f"Sandbox container failed (exit {proc.returncode}): {stderr}")

    try:
        output = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return ExecutionResult(error=f"Sandbox returned invalid JSON: {proc.stdout[:500]}")

    error = output.get("error")
    if error:
        logger.warning(f"Sandbox execution returned error: {error}")
    else:
        logger.info("Sandbox execution completed successfully")

    return ExecutionResult(
        result=output.get("result"),
        error=error,
        truncated=output.get("truncated", False),
    )
