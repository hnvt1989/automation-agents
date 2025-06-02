# Planner LLM Refactor

## Overview

The planner has been refactored to use an LLM-based parser instead of complex regex patterns. This provides more reliable natural language processing and cleaner code separation.

## Architecture

The refactored planner consists of three main components:

### 1. PlannerParser (`src/agents/planner_parser.py`)
- Uses OpenAI to parse natural language commands into structured JSON
- Handles date/time parsing and normalization
- Returns consistent action/data format for operations

### 2. PlannerOperations (`src/agents/planner_ops.py`)
- Provides simple CRUD operations for tasks, meetings, and logs
- No natural language processing - works with structured data only
- Handles all YAML file operations

### 3. Primary Agent Integration (`src/agents/primary.py`)
- Updated `handle_planner_task` to use the new parser and operations
- Cleaner code with clear separation of concerns

## Benefits

1. **More Reliable Parsing**: LLM handles complex natural language patterns better than regex
2. **Maintainable Code**: Clear separation between NLP and file operations
3. **Extensible**: Easy to add new commands by updating the parser prompt
4. **Testable**: Operations can be tested independently of parsing

## Usage Examples

The planner now supports the same natural language commands as before:

```
# Tasks
"add task 'job search' with tag 'personal' and high priority"
"add task with id 106264 description 'Document test scenarios' priority high"
"update job search task status to in progress"
"mark task TASK-1 as completed"
"remove task TASK-1"

# Meetings
"schedule meeting team sync tomorrow at 10am"
"add meeting 'client call' on Monday at 2pm"
"cancel meeting tomorrow"

# Work Logs
"add a daily log 'research automated test analysis' took 2 hours"
"log 3 hours on TASK-1 implementing the API"
"spent 4 hours on TASK-2"

Note: Daily logs now use `log_id` instead of `task_id` in the YAML files.

# Planning
"plan for tomorrow"
"what's on my agenda today"

# Task Search and Listing
"list all tasks"
"find task with title including 'test scenarios'"
"search for tasks containing 'documentation'"
```

## Implementation Details

### Parser Prompt
The parser uses a detailed system prompt that includes:
- Available actions and their formats
- Date/time parsing rules
- Example input/output pairs
- JSON response structure

### Error Handling
- Invalid commands return an "error" action
- File operation errors are caught and returned with details
- Missing task IDs or ambiguous references are handled gracefully

### Testing
- Unit tests for operations (CRUD functionality)
- Parser tests with mocked LLM responses
- Integration tests for end-to-end flow

## Migration Notes

The original `planner.py` file still contains the regex-based functions for backward compatibility. These can be removed once the new implementation is fully validated.

## Custom Task IDs

The planner now supports custom task IDs when creating tasks. This is useful for tracking tasks from external systems like TestRail, Jira, etc.

```
"add task with id 106264 description 'Document test scenarios' priority high"
```

- If a custom ID is provided, it will be used instead of auto-generating one
- Duplicate IDs are rejected with an error message
- Both `id` and `identifier` fields are supported in the parsed data

## Improved Task Matching

The system now includes enhanced task matching capabilities:

- **Exact matching**: Direct ID or title matches
- **Partial matching**: Substring matching in titles
- **Fuzzy matching**: Handles small typos (e.g., "tests scenarios" matches "test scenarios")
- **Word-based matching**: Matches when 80% of words are found

This makes it easier to update tasks even with slight variations in how you refer to them.

## Future Enhancements

1. Add support for batch operations
2. Implement natural language queries ("what tasks are due this week?")
3. Add more sophisticated date parsing ("every Monday", "in 3 business days")
4. Support for task dependencies and subtasks