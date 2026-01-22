"""Sensemaker agent - updates memory and synthesizes information."""

import json
from typing import Any

from ..core.config import Config
from ..llm import LLMClient
from ..memory import Memory
from .base import BaseAgent


class SensemakerAgent(BaseAgent):
    """
    Updates its memory based on information from the InformationSeekingAgent.

    Responsibilities:
    - Process incoming information
    - Update working memory
    - Synthesize understanding
    - Decide when task is COMPLETE
    """

    def __init__(self, config: Config, llm_client: LLMClient, memory: Memory) -> None:
        super().__init__(config, llm_client)
        self.memory = memory
        self._system_prompt = """You are a sensemaking agent. Your task is to synthesize information and determine when you have enough to answer a query.

Given a query, plan, and gathered information, you must:
1. Analyze what information you have
2. Determine if you can answer the query
3. If yes, provide the answer
4. If no, specify what additional information is needed

Always respond with a JSON object in one of these formats:

If you have enough information to answer:
{
    "status": "complete",
    "answer": "Your complete answer to the query",
    "confidence": 0.9,
    "supporting_evidence": ["List of key data points that support your answer"]
}

If you need more information:
{
    "status": "needs_info",
    "request": "Specific description of what information is needed",
    "reasoning": "Why this information is needed"
}

Be thorough but efficient. Don't request unnecessary information."""

    def execute(
        self,
        query: str,
        plan: dict[str, Any],
        new_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process information and update understanding.

        Args:
            query: Original user query.
            plan: Execution plan from planner.
            new_info: New information from information seeker.

        Returns:
            Status dict with 'status' and either 'answer' or 'request'.
        """
        return self.process(query, plan, new_info)

    def process(
        self,
        query: str,
        plan: dict[str, Any],
        new_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process new information and update memory."""
        # Store new information in memory
        if new_info and new_info.get("success"):
            self.memory.update({"content": new_info})

        # Build context for LLM
        memory_context = self.memory.get_context_for_llm()
        plan_summary = self._summarize_plan(plan)

        # Format new info if available
        new_info_str = ""
        if new_info:
            new_info_str = f"\nNew information just received:\n{json.dumps(new_info, indent=2, default=str)}"

        prompt = f"""Query: {query}

Plan Summary:
{plan_summary}

{memory_context}
{new_info_str}

Based on all the information gathered, can you answer the query?
Respond with JSON indicating either 'complete' with an answer, or 'needs_info' with what you need."""

        messages = [{"role": "user", "content": prompt}]
        response = self._call_llm(messages)
        result = self._parse_response(response)

        # Ensure required fields
        result.setdefault("status", "needs_info")

        if result["status"] == "complete":
            result.setdefault("answer", "")
            result.setdefault("confidence", 0.5)
            result.setdefault("supporting_evidence", [])
        else:
            result.setdefault("request", "Need more information")
            result.setdefault("reasoning", "")

        return result

    def _summarize_plan(self, plan: dict[str, Any]) -> str:
        """Create a brief summary of the plan."""
        lines = []
        if plan.get("query_understanding"):
            lines.append(f"Understanding: {plan['query_understanding']}")
        if plan.get("required_info"):
            lines.append(f"Required info: {', '.join(plan['required_info'][:5])}")
        if plan.get("data_sources"):
            lines.append(f"Data sources: {', '.join(plan['data_sources'])}")
        return "\n".join(lines) if lines else "No plan details available"

    def get_answer(self) -> dict[str, Any]:
        """Generate final answer from accumulated knowledge."""
        prompt = f"""Based on all the information gathered:

{self.memory.get_context_for_llm()}

Provide a final comprehensive answer.
Respond with JSON containing 'answer', 'confidence', and 'supporting_evidence'."""

        messages = [{"role": "user", "content": prompt}]
        response = self._call_llm(messages)
        result = self._parse_response(response)

        result.setdefault("answer", "")
        result.setdefault("confidence", 0.0)
        result.setdefault("supporting_evidence", [])

        return result
