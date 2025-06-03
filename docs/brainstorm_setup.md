# Task Brainstorming Setup Guide

## Overview
The task brainstorming feature uses RAG (Retrieval-Augmented Generation) to enrich brainstorming with relevant context from your knowledge base, then generates comprehensive brainstorms using OpenAI.

## Features
- **RAG Integration**: Searches knowledge base for relevant context
- **AI-Powered Generation**: Uses OpenAI GPT-4 for structured brainstorming
- **Individual File Storage**: Saves each brainstorm to `data/{task_id}_brainstorm.md`
- **Structured Output**: Includes overview, considerations, approaches, risks, and recommendations

## Setup Requirements

### 1. Environment Variables
Set your LLM API key in your `local.env` file:
```bash
LLM_API_KEY=your-api-key-here
```

The system uses the `LLM_API_KEY` environment variable configured in `local.env` for all AI operations.

### 2. Usage Examples

**Basic brainstorm:**
```
You: brainstorm task 111025
You: lets brainstorm task ONBOARDING-1
```

**Brainstorm by title:**
```
You: brainstorm task with title "job search"
You: brainstorm task title "Explore weekly Automated Test coverage"
```

**Regenerate/improve existing brainstorm:**
```
You: improve brainstorm for task 111025
You: replace brainstorm task ONBOARDING-1
```

## Expected Output Structure

When successful, the brainstorm will include:

```markdown
## Brainstorm: [Task Title] (Task ID)

**Generated:** [Timestamp]
**Type:** initial/improved

### Overview
[Comprehensive task overview]

### Key Considerations
- [Important factors to consider]
- [Technical requirements]
- [Dependencies and constraints]

### Potential Approaches
- [Different ways to accomplish the task]
- [Alternative solutions]

### Risks and Challenges
- [Potential blockers]
- [Technical challenges]

### Recommendations
- [Specific next steps]
- [Best practices to follow]

### RAG Context Used
- [Retrieved context from knowledge base]

### Sources
- [Documentation and resources used]
```

## File Locations
- **Individual files**: `data/{task_id}_brainstorm.md`
- **Collective file**: `task_brainstorms.md`

## Troubleshooting

### "API key not set" Error
Ensure your LLM_API_KEY is properly configured in your `local.env` file.

### "Task not found" Error
Verify the task ID exists in `data/tasks.yaml`.

### RAG Initialization Failed
This warning can be ignored if you don't have documents indexed. The system will still generate brainstorms using task information alone.

## Implementation Details

The brainstorming system:
1. Parses your natural language request
2. Finds the task in your task management system
3. Searches the knowledge base for relevant context (if available)
4. Combines task details with RAG context
5. Sends to OpenAI for structured brainstorming
6. Saves results to both collective and individual markdown files

The implementation is in:
- `src/agents/task_brainstorm.py` - Core brainstorming logic
- `src/agents/primary.py` - Request routing
- `src/agents/planner_parser.py` - Natural language parsing