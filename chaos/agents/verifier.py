"""Verifier agent - validates answers and creates reports."""

from typing import Any

from ..core.config import Config
from .base import BaseAgent


class VerifierAgent(BaseAgent):
    """
    Verifies whether the sensemaker's answer addresses the user query.

    Responsibilities:
    - Evaluate answer completeness
    - Check answer accuracy
    - Identify gaps or issues
    - Generate human-readable report
    """

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._system_prompt = """You are a verification agent. Your task is to:
        1. Evaluate if the answer addresses the original query
        2. Check for completeness and accuracy
        3. Identify any gaps or potential issues
        4. Generate a concise report for human review

        Be critical but fair in your evaluation.
        """

    def execute(self, query: str, result: dict[str, Any]) -> dict[str, Any]:
        """Verify the result."""
        return self.verify(query, result)

    def verify(self, query: str, result: dict[str, Any]) -> dict[str, Any]:
        """
        Verify if the result answers the query.

        Args:
            query: Original user query.
            result: Result from sensemaker.

        Returns:
            Verification report.
        """
        # TODO: Implement verification logic
        return {
            "query": query,
            "answer": result.get("answer"),
            "is_complete": False,
            "is_accurate": False,
            "confidence_score": 0.0,
            "gaps": [],
            "issues": [],
            "summary": "",
            "recommendation": "needs_review",  # approve, reject, needs_review
        }

    def generate_report(self, verification: dict[str, Any]) -> str:
        """Generate human-readable report."""
        # TODO: Implement report generation
        return f"""
        === Verification Report ===
        Query: {verification['query']}
        Answer: {verification['answer']}

        Completeness: {'Yes' if verification['is_complete'] else 'No'}
        Accuracy: {'Yes' if verification['is_accurate'] else 'No'}
        Confidence: {verification['confidence_score']:.2f}

        Gaps: {', '.join(verification['gaps']) or 'None'}
        Issues: {', '.join(verification['issues']) or 'None'}

        Summary: {verification['summary']}
        Recommendation: {verification['recommendation']}
        """
