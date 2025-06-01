# Planner Agent Specification

This document outlines a proposed design for a **Planner Agent** that generates a concise daily summary and plan. The agent will be invoked by the primary automation system.

## Inputs

The agent receives a JSON payload with the following structure:

```json
{
  "paths": {
    "tasks": "<abs>/data/tasks.yaml",
    "logs": "<abs>/data/daily_logs.yaml",
    "meets": "<abs>/data/meetings.yaml"
  },
  "target_date": "YYYY-MM-DD",          // tomorrow
  "work_hours": { "start": "09:00", "end": "17:00" },
  "feedback": "<optional free text or structured blob>"
}
```

## YAML Schemas

```yaml
# tasks.yaml
- id: str
  title: str
  priority: high|medium|low
  estimate_hours: int
  due_date: YYYY-MM-DD
  status: pending|in_progress|done
  tags: [str, ...]

# daily_logs.yaml
YYYY-MM-DD:
  - task_id: str | null
    description: str
    actual_hours: float

# meetings.yaml
- id: str
  title: str
  start: YYYY-MM-DDThh:mm±hh:mm
  end:   YYYY-MM-DDThh:mm±hh:mm
  participants: [str, ...]
```

## Expected Output

On success the agent returns:

```json
{
  "yesterday_markdown": "## YYYY-MM-DD\n- bullet ...",
  "tomorrow_markdown":  "## Plan for YYYY-MM-DD\n| Time | Task | Reason | ..."
}
```

If loading or parsing YAML fails the response should be:

```json
{ "error": "human readable message" }
```

## Core Logic

1. **Load YAML files** and validate them against the schemas.
2. **Build Yesterday's Summary**
   - Set `yesterday = target_date - 1`.
   - Gather entries from `daily_logs[yesterday]`.
   - Produce three to five bullet points, each under twenty words.
3. **Build Tomorrow's Plan**
   - Select all tasks where `status != done`.
   - Score tasks by priority (high → low) and how soon the `due_date` is.
   - Exclude times that conflict with meetings on `target_date`.
   - Fit the highest scoring tasks into the available work hours (minus meetings).
   - Output a table with time block, task identifier and title, plus a short reason.
4. **No file system writes** – return strings only.
5. If any YAML file is missing or malformed return the error structure.

## Constraints

- Execution time should be under five seconds for around one thousand tasks or log entries.
- Use only standard Python libraries plus `PyYAML`.
- Do not output any em dash characters.

## Testing Guidelines

Unit tests should mock YAML content and assert the generated JSON matches predefined snapshots. Use `pytest` and keep tests fast.
