"""Verifier agent - validates answers and creates reports."""

import json
from typing import Any

from ..core.config import Config
from ..llm import LLMClient
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

    def __init__(self, config: Config, llm_client: LLMClient) -> None:
        super().__init__(config, llm_client)
        self._system_prompt = """You are a verification agent. Your task is to evaluate answers and ensure they properly address the original query.

When verifying an answer, check:
1. Does the answer directly address the query?
2. Is the answer complete and comprehensive?
3. Is the answer supported by the provided evidence?
4. Are there any gaps, inconsistencies, or issues?

Respond with a JSON object:
{
    "is_complete": true/false,
    "is_accurate": true/false,
    "confidence_score": 0.0 to 1.0,
    "gaps": ["List of any missing information or gaps"],
    "issues": ["List of any problems or concerns"],
    "summary": "Brief summary of the verification",
    "recommendation": "approve" | "reject" | "needs_review"
}

Be critical but fair. A good answer should directly answer the query with supporting evidence."""

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
        answer = result.get("answer", "")
        evidence = result.get("supporting_evidence", [])
        confidence = result.get("confidence", 0.0)

        prompt = f"""Please verify the following answer to a query:

Original Query: {query}

Answer: {answer}

Supporting Evidence: {json.dumps(evidence, indent=2, default=str)}

Stated Confidence: {confidence}

Evaluate this answer and provide a verification report as JSON."""

        messages = [{"role": "user", "content": prompt}]
        response = self._call_llm(messages)
        verification = self._parse_response(response)

        # Ensure required fields with defaults
        verification.setdefault("query", query)
        verification.setdefault("answer", answer)
        verification.setdefault("is_complete", False)
        verification.setdefault("is_accurate", False)
        verification.setdefault("confidence_score", 0.0)
        verification.setdefault("gaps", [])
        verification.setdefault("issues", [])
        verification.setdefault("summary", "")
        verification.setdefault("recommendation", "needs_review")

        return verification

    def generate_report(self, verification: dict[str, Any]) -> str:
        """Generate human-readable report."""
        gaps = verification.get("gaps", [])
        issues = verification.get("issues", [])

        return f"""
=== Verification Report ===
Query: {verification.get('query', 'N/A')}

Answer: {verification.get('answer', 'N/A')}

Completeness: {'Yes' if verification.get('is_complete') else 'No'}
Accuracy: {'Yes' if verification.get('is_accurate') else 'No'}
Confidence: {verification.get('confidence_score', 0.0):.2f}

Gaps: {', '.join(gaps) if gaps else 'None identified'}
Issues: {', '.join(issues) if issues else 'None identified'}

Summary: {verification.get('summary', 'No summary provided')}
Recommendation: {verification.get('recommendation', 'needs_review').upper()}
"""
