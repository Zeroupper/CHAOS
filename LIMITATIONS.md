# Known Limitations

## Limitations with Small Models

- Models under 10B parameters struggle with the orchestration system as a result. The model spends capacity producing valid JSON structure rather than solving the analytical task.

*Potential fix: Reduce prompt context to only task-relevant information. Most failures occur during plan generation, where models hallucinate column names or misidentify datasets. Providing full dataset schemas when only one or two are relevant introduces noise — smaller models appear to hallucinate more as prompt context grows.*

## Orchestration vs. Raw Code Execution

- The step-by-step orchestrated execution (plan → code → review → iterate) may not yield better accuracy scores compared to simply providing a capable model with dataset context and a straightforward instruction to write and execute analysis code directly. A model given raw code execution access with minimal prompting can often arrive at correct answers faster and with fewer failure points.
- The orchestration system's primary advantage is not necessarily improved accuracy but rather **explainability and traceability** — each step is logged, the reasoning chain is visible, and a human in the loop can follow, inspect, and intervene at any stage of the execution. This makes the process more auditable and debuggable, even if the final numeric result is comparable to a single-shot code execution approach.
- A flawed plan that fails during execution tends to get stuck in a retry loop — the sensemaker repeatedly proposes reviews or re-executes the same failing step, but the underlying plan decomposition is wrong and no amount of retrying will fix it. The system lacks the ability to abandon a plan and start over with a different approach, so it burns through max attempts without making progress.

*Potential fix: Removing planner agent, and step-by-step execution, stay with just the sensemaking loop and generate the whole code for the user query. Replanning is still possible based on previous executions (see human-in-the-loop), but I am afraid the learnings usecase is not tested thoroughly which might be need a better approach to work.*

## Sandbox Constraints

- Hard 30-second timeout — may be insufficient for complex data operations

## CSV-Only Data Sources

- Only `CSVDataSource` is built-in. No native support for JSON, Parquet, SQL, or APIs. Custom sources require extending `BaseDataSource`.

## Silent Data Source Failures

- Failed data sources print a warning but the system continues without that data. No validation that required datasets loaded successfully — downstream agents may operate on incomplete data without knowing.

## Evaluation Metric Fragility

- Numeric answer extraction is regex-based — fragile to phrasing variations
- Falls back to "last number in text" which can extract wrong values
- Hardcoded 0.5% relative tolerance
- LLM-as-judge for subjective questions has no inter-rater reliability checks