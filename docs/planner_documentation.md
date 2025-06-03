# Planner Agent Documentation

## Overview

The Planner Agent is a comprehensive task and schedule management system that generates daily plans, manages tasks, meetings, and work logs. The system has been refactored to use LLM-based natural language processing for improved reliability and user experience.

## Architecture

The planner consists of four main components:

### 1. PlannerParser (`src/agents/planner_parser.py`)
- Uses OpenAI to parse natural language commands into structured JSON
- Handles date/time parsing and normalization
- Returns consistent action/data format for operations

### 2. PlannerOperations (`src/agents/planner_ops.py`)
- Provides simple CRUD operations for tasks, meetings, and logs
- No natural language processing - works with structured data only
- Handles all YAML file operations

### 3. Core Planner (`src/agents/planner.py`)
- Main planning engine that generates daily schedules
- Includes meeting notes analysis for focus generation
- Supports both rule-based and LLM-powered focus analysis

### 4. Primary Agent Integration (`src/agents/primary.py`)
- Integrates planner functionality into the main agent system
- Enhanced task search with multi-field and LLM-powered search

## Input Format

The planner receives a JSON payload with the following structure:

```json
{
  "paths": {
    "tasks": "<abs>/data/tasks.yaml",
    "logs": "<abs>/data/daily_logs.yaml",
    "meets": "<abs>/data/meetings.yaml",
    "meeting_notes": "<abs>/data/meeting_notes"
  },
  "target_date": "YYYY-MM-DD",
  "work_hours": { "start": "09:00", "end": "17:00" },
  "use_llm_for_focus": true,
  "feedback": "<optional free text or structured blob>"
}
```

## Date Handling

The Planner Agent intelligently understands and handles date context from user queries:

### Date Context Extraction

The system analyzes user queries to identify temporal references:

**Supported formats:**
- Direct references: "today", "tomorrow", "yesterday"
- Week references: "next week", "this week", "next Monday"
- Relative: "in 3 days"
- ISO format: "2025-06-02"
- US format: "06/02/2025", "6-2-2025"

### Date Resolution Priority

1. Look for explicit dates (YYYY-MM-DD format)
2. Look for relative terms: "tomorrow", "today", "yesterday", "next week", etc.
3. If no date context found in planning requests, default to "today"

## Meeting Notes Analysis

The planner analyzes meeting notes within the last 3 days of the target date to generate relevant focus areas:

### Features
- **Automatic Discovery**: Finds `.md` files in `data/meeting_notes` recursively
- **Date Extraction**: Supports various filename formats (June02standup.md, 2025-06-02-meeting.md)
- **Rule-based Analysis**: Keyword matching between tasks and meeting content
- **LLM Analysis**: Sophisticated semantic analysis for better focus generation

### Focus Output
Focus areas are integrated directly into the daily plan markdown:

```markdown
## Plan for 2025-06-02

### Focus Areas (Based on Recent Meetings)
- [2025-06-02] Working on veteran information page and pre-fill logic
- [2025-06-02] Writing unit tests for veteran info

**AI Analysis:**
- Focus on veteran info pre-fill logic as backend readiness is critical
- Prioritize unit tests since designs are missing
```

## Enhanced Task Search

The planner includes sophisticated task search capabilities:

### Multi-Field Search
Searches across all task fields:
- Title, Description, Priority, Status, Tags, Task ID

### LLM-Powered Search
Automatically triggers for complex queries like:
- "how many personal tasks do I have?"
- "show me all high priority tasks"
- "find tasks that are overdue"

### Search Output
Results include field match information:
```
Tasks matching 'personal' (keyword search):
- TASK-1: job search (in_progress, high priority) [tags: personal] (matched: tags)
```

## Available Actions

### Task Management
- `add_task`: Add new tasks with natural language
- `update_task`: Modify existing tasks
- `remove_task`: Delete tasks
- `search_tasks`/`find_task`: Search tasks with enhanced capabilities

### Meeting Management
- `add_meeting`: Schedule meetings
- `remove_meeting`: Cancel meetings

### Work Logging
- `add_log`: Log work done on tasks
- `remove_log`: Remove work logs

### Planning
- `plan_day`: Generate comprehensive daily plans with focus areas

## Example Usage

### Planning
```
"What should I do tomorrow?"
"Plan for 2025-06-03"
"Generate my schedule for today"
```

### Task Management
```
"Add task: Review documentation with high priority"
"Search for personal tasks"
"How many high priority tasks do I have?"
"Update TASK-1 status to completed"
```

### Meeting Scheduling
```
"Schedule meeting: team standup tomorrow at 10am"
"Cancel meeting tomorrow at 2pm"
```

### Work Logging
```
"Log 3 hours on TASK-1 implementing the API"
"Remove log for TASK-1 yesterday"
```

## Files Structure

### Data Files
- `data/tasks.yaml` - Individual tasks with metadata
- `data/meetings.yaml` - Scheduled meetings
- `data/daily_logs.yaml` - Work log entries
- `data/meeting_notes/` - Meeting notes for focus analysis

### Code Files
- `src/agents/planner.py` - Core planning engine
- `src/agents/planner_parser.py` - LLM-based command parser
- `src/agents/planner_ops.py` - YAML operations
- `src/agents/primary.py` - Integration with main agent system

## Recent Enhancements

1. **Meeting Notes Integration**: Automatic analysis of recent meeting notes for focus generation
2. **Enhanced Search**: Multi-field keyword search and LLM-powered semantic search
3. **LLM Refactoring**: Moved from regex-based parsing to LLM-based natural language processing
4. **Focus Generation**: Both rule-based and AI-powered focus area suggestions
5. **Comprehensive Date Handling**: Support for various date formats and natural language references