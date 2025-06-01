# Planner Agent Date Handling

The Planner Agent has been enhanced to intelligently understand and handle date context from user queries. When users ask about planning with temporal references like "tomorrow", the system automatically extracts the correct date context and plans accordingly.

## How It Works

### 1. Date Context Extraction

The system uses an intelligent date extraction function that analyzes user queries to identify temporal references:

```python
def extract_date_from_query(query: str) -> str:
    """Extract date context from user queries."""
```

### 2. Date Resolution

The planner agent's `use_planner_agent` tool resolves date references into actual dates:

- **Relative dates**: "tomorrow", "today", "yesterday", "next week", etc.
- **Absolute dates**: "2024-01-15", "12/25/2024", etc.
- **Default fallback**: If no date context is found, defaults to "today"

## Supported Date References

### Relative Date Terms

| User Input | Resolved To |
|-----------|-------------|
| "tomorrow" | Today + 1 day |
| "today" | Current date |
| "yesterday" | Today - 1 day |
| "next week" | Next Monday |
| "next monday" | Next Monday |
| "this week" | This Monday |
| "this monday" | This Monday |

### Date Formats

| Format | Example | Notes |
|--------|---------|-------|
| ISO 8601 | "2024-01-15" | Preferred format |
| US Format | "12/25/2024", "01/15/2024" | Converted to ISO format |
| With separators | "12-25-2024" | Also supported |

## Example User Interactions

### Basic Planning Queries

**User**: "Tell me what I should plan to do tomorrow?"

**System Response**:
1. Extracts "tomorrow" from the query
2. Calls `use_planner_agent(target_date="tomorrow")`
3. Resolves "tomorrow" to actual date (e.g., "2024-01-16")
4. Returns plan for January 16, 2024

### Specific Date Planning

**User**: "What should I work on for 2024-01-15?"

**System Response**:
1. Extracts "2024-01-15" from the query
2. Calls `use_planner_agent(target_date="2024-01-15")`
3. Returns plan for January 15, 2024

### Complex Queries

**User**: "Can you help me plan what I should do tomorrow morning?"

**System Response**:
1. Extracts "tomorrow" from the complex query
2. Generates plan for tomorrow
3. Focuses on morning time slots in the response

## Technical Implementation

### Date Extraction Function

```python
def extract_date_from_query(query: str) -> str:
    """Extract date context from user queries."""
    query_lower = query.lower().strip()
    
    # Check for relative date terms
    if "tomorrow" in query_lower:
        return "tomorrow"
    elif "today" in query_lower:
        return "today"
    # ... additional logic for other date references
    
    # Check for ISO date patterns
    iso_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', query)
    if iso_match:
        return iso_match.group(1)
    
    # Default to today
    return "today"
```

### Date Resolution Logic

```python
def resolve_date_reference(target_date: str) -> date:
    """Convert date references to actual dates."""
    if target_date == "tomorrow":
        return date.today() + timedelta(days=1)
    elif target_date == "today":
        return date.today()
    # ... additional resolution logic
```

## Primary Agent Integration

The primary orchestration agent has been enhanced with specific guidance for date context extraction:

### System Prompt Guidelines

The agent is instructed to:

1. **Analyze queries** for temporal references
2. **Extract date context** using priority order:
   - Explicit dates (YYYY-MM-DD format)
   - Relative terms ("tomorrow", "today", etc.)
   - Default to "today" for planning requests
3. **Pass extracted context** to the planner agent

### Example Agent Reasoning

For query: "Tell me what I should plan to do tomorrow"

1. **Identifies**: This is a planning request
2. **Extracts**: "tomorrow" from the query
3. **Calls**: `use_planner_agent(target_date="tomorrow")`
4. **Receives**: Plan for tomorrow's date

## Error Handling

### Invalid Date References

- **Malformed dates**: Fall back to "today"
- **Ambiguous references**: Use best-match logic
- **Missing context**: Default to "today"

### Logging

The system logs date resolution for debugging:

```
INFO: Resolved target date: 2024-01-16
```

## Testing

Comprehensive tests verify the date handling functionality:

### Unit Tests

- `test_date_parsing_logic()`: Tests date resolution
- `test_date_extraction_from_queries()`: Tests query parsing

### Test Coverage

- Relative date terms
- Absolute date formats
- Case insensitive matching
- Complex query parsing
- Error handling scenarios

## Benefits

### User Experience

1. **Natural language**: Users can ask about "tomorrow" naturally
2. **Flexible input**: Multiple date formats supported
3. **Intelligent defaults**: No need to specify dates for "today"

### System Intelligence

1. **Context awareness**: Understands temporal references
2. **Consistent behavior**: Reliable date interpretation
3. **Extensible**: Easy to add new date patterns

## Future Enhancements

### Potential Improvements

1. **Natural language dates**: "next Friday", "in two weeks"
2. **Time zone handling**: Support for different time zones
3. **Calendar integration**: Smart date suggestions based on calendar
4. **Recurring patterns**: "every Monday", "weekly"

### Internationalization

- Support for different date formats (DD/MM/YYYY)
- Localized date terms in other languages
- Cultural calendar considerations

## Configuration

The date handling system requires no additional configuration. It works out of the box with the existing planner agent infrastructure.

### Dependencies

- Python `datetime` module for date calculations
- `re` module for pattern matching
- Existing planner agent YAML data files

## Troubleshooting

### Common Issues

1. **Date not recognized**: Check for typos in date format
2. **Wrong date interpreted**: Verify the query contains clear temporal reference
3. **Planning for wrong day**: Confirm the system's current date/time

### Debug Information

Enable logging to see date resolution:

```python
log_info(f"Resolved target date: {target_date_str}")
```

This enhancement makes the planner agent much more intuitive to use, allowing users to naturally ask about their plans for "tomorrow" without needing to specify exact dates. 