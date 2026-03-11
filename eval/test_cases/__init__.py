"""Ground truth loading based on test cases path."""

from __future__ import annotations

from pathlib import Path


def load_ground_truth(test_cases_path: str) -> dict[str, tuple]:
    """Load the ground truth dict for the dataset folder containing test_cases_path."""
    folder = Path(test_cases_path).parent.name
    if folder == "globem":
        from .globem.verify_test_cases import OBJECTIVE_GROUND_TRUTH
    else:
        from .gloss.verify_test_cases import OBJECTIVE_GROUND_TRUTH
    return OBJECTIVE_GROUND_TRUTH
