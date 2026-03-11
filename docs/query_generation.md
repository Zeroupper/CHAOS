# Test Case Query Generation

Prompts for generating evaluation test cases at different difficulty levels. Use these with an LLM to produce new queries for your dataset.

## Prerequisites

Before generating queries, provide the LLM with:
1. The dataset schema (`datasets/<your_dataset>/data_schema.yaml`)
2. A few sample rows from each dataset
3. The existing test cases (`eval/test_cases/test_cases.yaml`) to avoid duplicates

## Objective Queries

Objective queries have a single correct numeric answer. Each must be verifiable by running code against the data.

### Simple

Single dataset, one aggregation, no filtering or data cleaning.

**Prompt:**
```
Given the following dataset schema, generate objective test case queries at the SIMPLE difficulty level.

Rules:
- Each query targets exactly ONE dataset
- Uses a single aggregation (max, min, sum, count, mean, nunique)
- No filtering, no data cleaning, no invalid value handling
- The answer is a single number

Schema:
<paste schema>

Generate N queries in this YAML format:
- id: "obj_XXX"
  category: "objective"
  difficulty: "simple"
  query: "..."
```

**Example queries:**
- "What was the highest heart rate recorded in the dataset?"
- "How many total steps were taken according to the Garmin watch?"
- "How many times was the phone unlocked?"

### Medium

Single dataset, requires filtering, data cleaning, or domain knowledge about column semantics.

**Prompt:**
```
Given the following dataset schema, generate objective test case queries at the MEDIUM difficulty level.

Rules:
- Each query targets ONE dataset
- Requires filtering (e.g., by status, validity) or handling invalid data (e.g., ignoring -1 or 0 values)
- May require understanding column semantics (e.g., "VALID" status, lock_state values)
- The answer is a single number

Schema:
<paste schema>

Generate N queries in this YAML format:
- id: "obj_XXX"
  category: "objective"
  difficulty: "medium"
  query: "..."
```

**Example queries:**
- "What was the lowest resting heart rate for user test004, ignoring any invalid readings?"
- "What was the average heart rate measured by the stress sensor during 'VALID' readings for user test004?"
- "How many different WiFi networks did user test004's phone connect to?"

### Complex

Cross-dataset joins, temporal alignment, or statistical computation.

**Prompt:**
```
Given the following dataset schema, generate objective test case queries at the COMPLEX difficulty level.

Rules:
- Requires joining TWO or more datasets by timestamp proximity or shared keys
- May involve statistical methods (correlation, regression, time-series alignment)
- Temporal alignment must specify a tolerance window (e.g., "within 30 seconds")
- The answer is a single number

Schema:
<paste schema>

Cross-dataset relationships:
<paste relationships section from schema>

Generate N queries in this YAML format:
- id: "obj_XXX"
  category: "objective"
  difficulty: "complex"
  query: "..."
```

**Example queries:**
- "What was the average heart rate for user test004 during walking periods? Match heart rate readings within 30 seconds of each walking activity event."
- "What is the Pearson correlation between heart rate readings from the dedicated heart rate sensor and the stress sensor for user test004? Align readings by closest timestamp within 1 second."
- "What is the Pearson correlation between hourly step counts from the Garmin watch and the iPhone for user test004?"

## Subjective Queries

Subjective queries are open-ended analytical questions. Each requires a rubric with weighted criteria for LLM-as-judge evaluation.

### Difficulty Levels

| Level | Datasets | Reasoning | What the answer looks like |
|-------|----------|-----------|---------------------------|
| **Simple** | 1 dataset | Summarize or describe what the data shows | Direct summary of values — no inference beyond the numbers |
| **Medium** | 1-2 related datasets | Interpret patterns, draw a conclusion | A conclusion supported by evidence from the data |
| **Complex** | 2+ datasets | Synthesize across sources, apply domain knowledge, acknowledge limitations | Multi-source analysis with uncertainty awareness |

### Simple

Summarize or describe data from a single dataset. The answer follows directly from the data without requiring interpretation or domain expertise.

**Prompt:**
```
Given the following dataset schema, generate subjective test case queries at the SIMPLE difficulty level.

Rules:
- Each query targets exactly ONE dataset
- Asks to summarize, describe, or list what the data shows
- No cross-dataset reasoning or domain expertise needed
- The answer should follow directly from the data values
- Include a rubric with 3-4 criteria, weights summing to 1.0
- Rubric criteria should check: correct data usage, completeness, quantitative evidence, clarity

Schema:
<paste schema>

Generate N queries in this YAML format:
- id: "sub_XXX"
  category: "subjective"
  difficulty: "simple"
  query: "..."
  rubric:
    - criterion: "..."
      weight: 0.X
      description: "..."
```

**Example queries:**
- "Summarize user test004's phone call activity."
- "Describe the battery usage pattern for user test004."
- "What apps does user test004 use most frequently?"

**Example rubric:**
```yaml
rubric:
  - criterion: "Uses correct data source"
    weight: 0.3
    description: "Queries the relevant dataset and references actual values"
  - criterion: "Completeness"
    weight: 0.3
    description: "Covers the key aspects of the data (e.g., all call types, counts, durations)"
  - criterion: "Quantitative evidence"
    weight: 0.2
    description: "Cites specific numbers from the data"
  - criterion: "Clarity"
    weight: 0.2
    description: "Presents findings in a clear, organized manner"
```

### Medium

Interpretation of patterns from one or two related datasets.

**Prompt:**
```
Given the following dataset schema, generate subjective test case queries at the MEDIUM difficulty level.

Rules:
- Asks for interpretation or pattern analysis from ONE or TWO related datasets
- The answer requires citing specific data values as evidence
- Should be answerable without cross-dataset temporal joins
- Include a rubric with 3-4 criteria, weights summing to 1.0
- Rubric criteria should check: data usage, quantitative evidence, sound reasoning, contextualization

Schema:
<paste schema>

Generate N queries in this YAML format:
- id: "sub_XXX"
  category: "subjective"
  difficulty: "medium"
  query: "..."
  rubric:
    - criterion: "..."
      weight: 0.X
      description: "..."
```

**Example queries:**
- "Based on the data, is user test004 physically active or sedentary?"
- "What can you tell about user test004's daily routine from their phone usage?"

**Example rubric:**
```yaml
rubric:
  - criterion: "Uses step data"
    weight: 0.3
    description: "References actual step count values from garmin_steps or ios_steps"
  - criterion: "Provides quantitative evidence"
    weight: 0.3
    description: "Cites specific numeric values (total steps, daily average, etc.)"
  - criterion: "Sound reasoning"
    weight: 0.2
    description: "Logical chain from step data to activity level conclusion"
  - criterion: "Contextualizes findings"
    weight: 0.2
    description: "Compares to standard benchmarks (e.g., 10k steps/day) or provides context"
```

### Complex

Cross-dataset synthesis, domain reasoning, or acknowledging data limitations.

**Prompt:**
```
Given the following dataset schema, generate subjective test case queries at the COMPLEX difficulty level.

Rules:
- Requires synthesizing data from TWO or more datasets
- Answer should involve domain reasoning (health interpretation, behavioral inference)
- Must acknowledge data limitations or uncertainty
- Include a rubric with 3-4 criteria, weights summing to 1.0
- Rubric criteria should check: multi-source data usage, methodology, evidence, limitation awareness

Schema:
<paste schema>

Cross-dataset relationships:
<paste relationships section from schema>

Generate N queries in this YAML format:
- id: "sub_XXX"
  category: "subjective"
  difficulty: "complex"
  query: "..."
  rubric:
    - criterion: "..."
      weight: 0.X
      description: "..."
```

**Example queries:**
- "Does user test004 seem stressed? What does the data tell us?"
- "What can we figure out about user test004's sleep habits?"
- "Is user test004's heart rate variability healthy?"

**Example rubric:**
```yaml
rubric:
  - criterion: "Uses heart rate data"
    weight: 0.25
    description: "References garmin_hr heart rate values and patterns"
  - criterion: "Uses stress data"
    weight: 0.25
    description: "References garmin_stress data (heart rate from stress sensor, status values)"
  - criterion: "Provides evidence"
    weight: 0.25
    description: "Cites specific numeric values from the data"
  - criterion: "Acknowledges limitations"
    weight: 0.25
    description: "Notes data limitations, missing fields, or uncertainty"
```

## Ground Truth

Objective test cases need ground truth expected answers in `eval/test_cases/verify_test_cases.py`. For each new objective query, add a function that computes the expected answer directly from the dataset:

```python
def obj_XXX() -> float:
    """<paste the query text here>"""
    # Use load_all() for simple (no filtering), load() for medium/complex (per-user)
    df = load_all("dataset_name")
    # compute the answer
    return float(result)

# Add to OBJECTIVE_GROUND_TRUTH dict:
OBJECTIVE_GROUND_TRUTH["obj_XXX"] = (obj_XXX, <expected_value>)
```

Subjective test cases do not need ground truth — they are evaluated by rubric scoring only.
