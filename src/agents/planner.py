from __future__ import annotations

import os
import re
import glob
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

import yaml
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai import Agent


@dataclass
class PlannerInput:
    paths: Dict[str, str]
    target_date: str
    work_hours: Dict[str, str]
    feedback: str | None = None


def _load_yaml(path: str) -> Any:
    if not os.path.exists(path):
        raise FileNotFoundError(f"YAML file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _save_yaml(path: str, data: Any) -> None:
    """Save data to a YAML file."""
    # Convert datetime.date keys to strings for consistency
    if isinstance(data, dict):
        data = {str(k): v for k, v in data.items()}
    
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _find_recent_meeting_notes(notes_path: str, target_date: datetime.date, days_back: int = 3) -> List[Dict[str, Any]]:
    """Find meeting notes within the last N days before the target date."""
    if not os.path.exists(notes_path):
        return []
    
    recent_notes = []
    start_date = target_date - timedelta(days=days_back)
    end_date = target_date
    
    # Search for markdown files in the meeting notes directory
    pattern = os.path.join(notes_path, "**", "*.md")
    note_files = glob.glob(pattern, recursive=True)
    
    for file_path in note_files:
        try:
            # Try to extract date from filename or content
            file_date = _extract_date_from_meeting_note(file_path)
            if file_date and start_date <= file_date <= end_date:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                recent_notes.append({
                    'date': file_date,
                    'file_path': file_path,
                    'content': content,
                    'filename': os.path.basename(file_path)
                })
        except Exception:
            # Skip files that can't be read or parsed
            continue
    
    return sorted(recent_notes, key=lambda x: x['date'], reverse=True)


def _extract_date_from_meeting_note(file_path: str) -> Optional[datetime.date]:
    """Extract date from meeting note filename or content."""
    filename = os.path.basename(file_path)
    
    # Try various date patterns in filename
    date_patterns = [
        r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
        r'(\d{4})(\d{2})(\d{2})',    # YYYYMMDD
        r'(\d{2})-(\d{2})-(\d{4})',  # MM-DD-YYYY
        r'(\d{1,2})/(\d{1,2})/(\d{4})',  # M/D/YYYY
        r'June(\d{2})',  # JuneDD
        r'(\d{1,2})-(\d{1,2})',  # MM-DD (assume current year)
    ]
    
    current_year = datetime.now().year
    
    for pattern in date_patterns:
        match = re.search(pattern, filename)
        if match:
            try:
                if pattern == r'June(\d{2})':
                    # Special case for JuneDD format
                    day = int(match.group(1))
                    return datetime(current_year, 6, day).date()
                elif len(match.groups()) == 3:
                    if pattern == r'(\d{4})-(\d{2})-(\d{2})' or pattern == r'(\d{4})(\d{2})(\d{2})':
                        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    else:  # MM-DD-YYYY or M/D/YYYY
                        month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    return datetime(year, month, day).date()
                elif len(match.groups()) == 2:
                    # MM-DD format, assume current year
                    month, day = int(match.group(1)), int(match.group(2))
                    return datetime(current_year, month, day).date()
            except ValueError:
                continue
    
    # Try to find date in file content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_lines = f.read(500)  # Read first 500 chars
            
        for pattern in date_patterns[:4]:  # Only standard date patterns
            match = re.search(pattern, first_lines)
            if match:
                try:
                    if pattern == r'(\d{4})-(\d{2})-(\d{2})':
                        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                        return datetime(year, month, day).date()
                except ValueError:
                    continue
    except Exception:
        pass
    
    return None


def _analyze_meeting_notes_for_focus(meeting_notes: List[Dict[str, Any]], tasks: List[Dict[str, Any]]) -> List[str]:
    """Analyze meeting notes to generate focus points relevant to current tasks."""
    if not meeting_notes or not tasks:
        return []
    
    # Extract task keywords and topics
    task_keywords = set()
    for task in tasks:
        title = task.get('title', '').lower()
        tags = task.get('tags', [])
        
        # Add title words
        task_keywords.update(title.split())
        # Add tags
        task_keywords.update(tag.lower() for tag in tags)
    
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 
                  'task', 'work', 'project', 'will', 'be', 'is', 'are', 'was', 'were', 'have', 'has', 'had'}
    task_keywords = {kw for kw in task_keywords if kw not in stop_words and len(kw) > 2}
    
    focus_points = []
    
    for note in meeting_notes:
        content = note['content'].lower()
        date_str = note['date'].strftime('%Y-%m-%d')
        
        # Find relevant sections in the meeting notes
        relevant_points = []
        
        # Split content into sections
        sections = re.split(r'\n#+\s+', content)
        
        for section in sections:
            lines = section.split('\n')
            section_title = lines[0] if lines else ""
            
            # Check if section contains task-related keywords
            relevance_score = 0
            for keyword in task_keywords:
                if keyword in section.lower():
                    relevance_score += 1
            
            if relevance_score > 0:
                # Extract key points from this section
                for line in lines[1:]:
                    line = line.strip()
                    if line.startswith('- ') or line.startswith('* '):
                        # This is a bullet point
                        bullet_content = line[2:].strip()
                        # Check if bullet point is relevant
                        bullet_relevance = sum(1 for kw in task_keywords if kw in bullet_content.lower())
                        if bullet_relevance > 0:
                            relevant_points.append({
                                'point': bullet_content,
                                'section': section_title,
                                'relevance': bullet_relevance
                            })
        
        # Add the most relevant points from this meeting
        if relevant_points:
            relevant_points.sort(key=lambda x: x['relevance'], reverse=True)
            for point in relevant_points[:3]:  # Top 3 most relevant points
                focus_points.append(f"[{date_str}] {point['point']}")
    
    return focus_points[:5]  # Return top 5 focus points


def _generate_llm_focus_analysis(meeting_notes: List[Dict[str, Any]], tasks: List[Dict[str, Any]]) -> str:
    """Generate an LLM prompt for analyzing meeting notes and generating focus points."""
    if not meeting_notes or not tasks:
        return ""
    
    # Prepare meeting notes summary
    notes_summary = []
    for note in meeting_notes:
        date_str = note['date'].strftime('%Y-%m-%d')
        # Extract key sections (first 1000 chars to keep it manageable)
        content_preview = note['content'][:1000] + "..." if len(note['content']) > 1000 else note['content']
        notes_summary.append(f"**{date_str}** ({note['filename']}):\n{content_preview}")
    
    # Prepare tasks summary
    tasks_summary = []
    for task in tasks[:10]:  # Limit to top 10 tasks
        priority = task.get('priority', 'medium')
        due_date = task.get('due_date', 'no due date')
        title = task.get('title', '')
        tags = task.get('tags', [])
        tags_str = f" [tags: {', '.join(tags)}]" if tags else ""
        tasks_summary.append(f"- {title} (priority: {priority}, due: {due_date}){tags_str}")
    
    prompt = f"""# Meeting Notes Analysis for Focus Generation

## Recent Meeting Notes (Last 3 Days):
{chr(10).join(notes_summary)}

## Current Tasks:
{chr(10).join(tasks_summary)}

## Task:
Based on the meeting notes above and the current tasks, generate a focused list of 3-5 key things that should be prioritized or given special attention today. Look for:

1. Items mentioned in meetings that relate to current tasks
2. Blockers or dependencies mentioned in meetings
3. Deadlines or urgent items discussed
4. Team decisions that affect current work
5. Follow-up actions from meetings

Format your response as a simple bulleted list of focus areas, each with a brief explanation of why it's important based on the meeting context.

## Focus Areas:"""
    
    return prompt


async def _generate_llm_focus_list(meeting_notes: List[Dict[str, Any]], tasks: List[Dict[str, Any]], model: Optional[OpenAIModel] = None) -> str:
    """Use LLM to generate a focus list based on meeting notes and tasks."""
    if not meeting_notes or not tasks:
        return ""
    
    if model is None:
        model = OpenAIModel('gpt-4')
    
    prompt = _generate_llm_focus_analysis(meeting_notes, tasks)
    
    try:
        # Create a simple agent for focus analysis
        focus_agent = Agent(
            model=model,
            system_prompt="You are a productivity assistant that analyzes meeting notes and tasks to generate actionable focus areas. Provide clear, concise, and actionable focus points based on the context provided."
        )
        
        result = await focus_agent.run(prompt)
        return str(result.data) if hasattr(result, 'data') else str(result)
    except Exception as e:
        return f"Error generating LLM focus list: {str(e)}"


def generate_focus_list(meeting_notes: List[Dict[str, Any]], tasks: List[Dict[str, Any]], use_llm: bool = True, model: Optional[OpenAIModel] = None) -> Dict[str, Any]:
    """Generate focus list using both rule-based and optionally LLM approaches."""
    result = {
        "rule_based_focus": [],
        "llm_focus": "",
        "llm_prompt": ""
    }
    
    # Rule-based analysis
    result["rule_based_focus"] = _analyze_meeting_notes_for_focus(meeting_notes, tasks)
    result["llm_prompt"] = _generate_llm_focus_analysis(meeting_notes, tasks)
    
    # LLM analysis (if requested and available)
    if use_llm:
        try:
            import asyncio
            result["llm_focus"] = asyncio.run(_generate_llm_focus_list(meeting_notes, tasks, model))
        except Exception as e:
            result["llm_focus"] = f"LLM analysis unavailable: {str(e)}"
    
    return result


def _get_yesterday_summary(logs: Dict[str, Any], target_date: datetime.date, meetings: List[Dict[str, Any]] = None) -> str:
    # Find the latest entry in logs (most recent working day)
    latest_date = None
    latest_entries = []
    
    # Sort dates in descending order to find the most recent
    available_dates = []
    for date_str in logs.keys():
        try:
            date_obj = datetime.fromisoformat(str(date_str)).date()
            # Only consider dates before the target date
            if date_obj < target_date:
                available_dates.append(date_obj)
        except (ValueError, TypeError):
            continue
    
    if available_dates:
        # Get the most recent date before target_date
        latest_date = max(available_dates)
        latest_entries = logs.get(latest_date.isoformat(), []) or []
    
    # If no entries found, fall back to "yesterday" for the header
    if not latest_date:
        latest_date = target_date - timedelta(days=1)
        latest_entries = []
    
    # Process work log entries
    bullets: List[str] = []
    for entry in latest_entries[:5]:
        desc = str(entry.get("description", "")).strip()
        if not desc:
            continue
        words = desc.split()
        bullet = " ".join(words[:20])
        bullets.append(f"- {bullet}")
    
    # Process meetings for the same date
    if meetings:
        meeting_bullets = []
        for meeting in meetings:
            try:
                meeting_date = None
                meeting_title = ""
                
                # Handle new format with date, time, event
                if "date" in meeting and "event" in meeting:
                    meeting_date_str = str(meeting["date"])
                    try:
                        meeting_date = datetime.fromisoformat(meeting_date_str).date()
                        meeting_title = str(meeting.get("event", "")).strip()
                        if meeting.get("time"):
                            time_str = str(meeting["time"]).strip('"')
                            meeting_title = f"{time_str} - {meeting_title}"
                    except ValueError:
                        continue
                
                # Handle legacy format with start/end ISO strings
                elif "start" in meeting and "title" in meeting:
                    start_val = meeting["start"]
                    if isinstance(start_val, str):
                        meeting_datetime = datetime.fromisoformat(start_val)
                    else:
                        meeting_datetime = start_val
                    
                    # Convert to local time if timezone info present
                    if meeting_datetime.tzinfo:
                        meeting_datetime = meeting_datetime.astimezone(None).replace(tzinfo=None)
                    
                    meeting_date = meeting_datetime.date()
                    meeting_title = str(meeting.get("title", "")).strip()
                    # Add time info
                    meeting_title = f"{meeting_datetime.strftime('%H:%M')} - {meeting_title}"
                
                # Only include meetings from the latest date
                if meeting_date == latest_date and meeting_title:
                    # Truncate long meeting titles
                    words = meeting_title.split()
                    meeting_bullet = " ".join(words[:15])
                    meeting_bullets.append(f"- {meeting_bullet}")
                    
            except Exception:
                # Skip malformed meeting entries
                continue
        
        # Add meeting bullets to the summary (limit to 3 meetings)
        if meeting_bullets:
            bullets.extend(meeting_bullets[:3])
    
    if not bullets:
        bullets.append("- No log entries")
    return f"## {latest_date.isoformat()}\n" + "\n".join(bullets)


def _compute_free_intervals(
    meetings: List[Dict[str, Any]],
    target_date: datetime.date,
    start_str: str,
    end_str: str,
) -> List[Tuple[datetime, datetime]]:
    start_dt = datetime.combine(target_date, datetime.strptime(start_str, "%H:%M").time())
    end_dt = datetime.combine(target_date, datetime.strptime(end_str, "%H:%M").time())
    day_meetings: List[Tuple[datetime, datetime]] = []
    
    for m in meetings:
        try:
            # Handle new format with date, time, event
            if "date" in m and "time" in m:
                meeting_date_str = str(m["date"])
                meeting_time_str = str(m["time"]).strip('"')  # Remove quotes if present
                
                # Parse the date
                try:
                    meeting_date = datetime.fromisoformat(meeting_date_str).date()
                except ValueError:
                    # Try alternative date format if needed
                    continue
                
                # Only process meetings for the target date
                if meeting_date != target_date:
                    continue
                
                # Parse the time and create start datetime
                try:
                    meeting_time = datetime.strptime(meeting_time_str, "%H:%M").time()
                    meeting_start = datetime.combine(meeting_date, meeting_time)
                    # Assume 1 hour duration if not specified
                    meeting_end = meeting_start + timedelta(hours=1)
                    day_meetings.append((meeting_start, meeting_end))
                except ValueError:
                    # Skip meetings with invalid time format
                    continue
            
            # Handle legacy format with start/end ISO strings
            elif "start" in m and "end" in m:
                # Handle both string and datetime object formats
                start_val = m["start"]
                end_val = m["end"]
                
                if isinstance(start_val, str):
                    st = datetime.fromisoformat(start_val)
                else:
                    st = start_val  # Already a datetime object
                    
                if isinstance(end_val, str):
                    et = datetime.fromisoformat(end_val)
                else:
                    et = end_val  # Already a datetime object
                
                # Convert to local time if timezone info present
                if st.tzinfo:
                    st = st.astimezone(None).replace(tzinfo=None)
                if et.tzinfo:
                    et = et.astimezone(None).replace(tzinfo=None)
                
                # Only process meetings for the target date (check after timezone conversion)
                if st.date() == target_date:
                    day_meetings.append((st, et))
            
        except Exception:
            # Skip malformed meeting entries
            continue
    
    day_meetings.sort()
    free: List[Tuple[datetime, datetime]] = []
    current = start_dt
    for st, et in day_meetings:
        if st > current:
            free.append((current, min(st, end_dt)))
        current = max(current, et)
        if current >= end_dt:
            break
    if current < end_dt:
        free.append((current, end_dt))
    return free


def _score_task(task: Dict[str, Any], target_date: datetime.date) -> int:
    priority_map = {"high": 3, "medium": 2, "low": 1}
    priority_score = priority_map.get(task.get("priority", "low"), 1)
    try:
        due_date = datetime.fromisoformat(task.get("due_date")).date()
        days_until_due = (due_date - target_date).days
    except Exception:
        days_until_due = 999
    due_score = max(0, 7 - days_until_due)
    return priority_score * 10 + due_score


def _pack_tasks(
    tasks: List[Dict[str, Any]],
    free: List[Tuple[datetime, datetime]],
) -> List[Tuple[datetime, datetime, Dict[str, Any]]]:
    plan: List[Tuple[datetime, datetime, Dict[str, Any]]] = []
    i = 0
    for task in tasks:
        # Handle None or missing estimate_hours values
        estimate_hours = task.get("estimate_hours")
        if estimate_hours is None or estimate_hours == "":
            remaining = 1  # Default to 1 hour
        else:
            try:
                remaining = int(estimate_hours)
                if remaining <= 0:
                    remaining = 1  # Ensure positive value
            except (ValueError, TypeError):
                remaining = 1  # Default to 1 hour if conversion fails
        
        while remaining > 0 and i < len(free):
            st, et = free[i]
            span = (et - st).total_seconds() / 3600
            if span <= 0:
                i += 1
                continue
            used = min(remaining, span)
            slot_end = st + timedelta(hours=used)
            plan.append((st, slot_end, task))
            remaining -= used
            if used < span:
                free[i] = (slot_end, et)
            else:
                i += 1
        if i >= len(free):
            break
    return plan


def _get_target_date_meetings(meetings: List[Dict[str, Any]], target_date: datetime.date) -> List[str]:
    """Get formatted meetings for the target date."""
    meeting_list = []
    
    for meeting in meetings:
        try:
            meeting_date = None
            meeting_title = ""
            
            # Handle new format with date, time, event
            if "date" in meeting and "event" in meeting:
                meeting_date_str = str(meeting["date"])
                try:
                    meeting_date = datetime.fromisoformat(meeting_date_str).date()
                    meeting_title = str(meeting.get("event", "")).strip()
                    if meeting.get("time"):
                        time_str = str(meeting["time"]).strip('"')
                        meeting_title = f"{time_str} - {meeting_title}"
                except ValueError:
                    continue
            
            # Handle legacy format with start/end ISO strings
            elif "start" in meeting and "title" in meeting:
                start_val = meeting["start"]
                if isinstance(start_val, str):
                    meeting_datetime = datetime.fromisoformat(start_val)
                else:
                    meeting_datetime = start_val
                
                # Convert to local time if timezone info present
                if meeting_datetime.tzinfo:
                    meeting_datetime = meeting_datetime.astimezone(None).replace(tzinfo=None)
                
                meeting_date = meeting_datetime.date()
                meeting_title = str(meeting.get("title", "")).strip()
                # Add time info
                meeting_title = f"{meeting_datetime.strftime('%H:%M')} - {meeting_title}"
            
            # Only include meetings from the target date
            if meeting_date == target_date and meeting_title:
                meeting_list.append(meeting_title)
                
        except Exception:
            # Skip malformed meeting entries
            continue
    
    return sorted(meeting_list)  # Sort by time


def _format_plan(plan: List[Tuple[datetime, datetime, Dict[str, Any]]], target_date: datetime.date, meetings: List[Dict[str, Any]] = None, focus_analysis: Dict[str, Any] = None) -> str:
    # Get meetings for the target date
    target_meetings = _get_target_date_meetings(meetings or [], target_date)
    
    # Start with the header
    content = [f"## Plan for {target_date.isoformat()}"]
    
    # Add focus areas section if available
    if focus_analysis and (focus_analysis.get('rule_based_focus') or focus_analysis.get('llm_focus')):
        content.append("\n### Focus Areas (Based on Recent Meetings)")
        
        # Add rule-based focus points
        rule_based = focus_analysis.get('rule_based_focus', [])
        if rule_based:
            for point in rule_based:
                content.append(f"- {point}")
        
        # Add LLM focus if available
        llm_focus = focus_analysis.get('llm_focus', '').strip()
        if llm_focus and not llm_focus.startswith('Error') and not llm_focus.startswith('LLM analysis unavailable'):
            content.append("\n**AI Analysis:**")
            # Split LLM response into lines and format as bullet points if not already formatted
            llm_lines = llm_focus.split('\n')
            for line in llm_lines:
                line = line.strip()
                if line:
                    if not line.startswith('•') and not line.startswith('-') and not line.startswith('*'):
                        content.append(f"- {line}")
                    else:
                        content.append(f"{line}")
        
        content.append("")  # Empty line before next section
    
    # Add meetings section if there are any
    if target_meetings:
        content.append("### Meetings")
        for meeting in target_meetings:
            content.append(f"- {meeting}")
        content.append("")  # Empty line before tasks
    
    # Add tasks table
    content.append("### Tasks")
    content.append("| Time | Task | Reason |")
    content.append("| - | - | - |")
    
    # Add task rows
    task_rows = []
    for st, et, task in plan:
        block = f"{st.strftime('%H:%M')}-{et.strftime('%H:%M')}"
        reason = f"Priority {task.get('priority')}, due {task.get('due_date')}"
        task_rows.append(f"| {block} | {task.get('id')} {task.get('title')} | {reason} |")
    
    if not task_rows:
        task_rows.append("| - | No tasks scheduled | - |")
    
    content.extend(task_rows)
    return "\n".join(content)


def _parse_natural_language_date(text: str, reference_date: Optional[datetime.date] = None) -> Optional[datetime.date]:
    """Parse natural language date expressions."""
    if reference_date is None:
        reference_date = datetime.now().date()
    
    text_lower = text.lower().strip()
    
    # Direct date patterns
    date_patterns = [
        (r'(\d{4})-(\d{1,2})-(\d{1,2})', lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()),
        (r'(\d{1,2})/(\d{1,2})/(\d{4})', lambda m: datetime(int(m.group(3)), int(m.group(1)), int(m.group(2))).date()),
    ]
    
    for pattern, parser in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return parser(match)
            except ValueError:
                continue
    
    # Relative date patterns
    if "today" in text_lower:
        return reference_date
    elif "tomorrow" in text_lower:
        return reference_date + timedelta(days=1)
    elif "yesterday" in text_lower:
        return reference_date - timedelta(days=1)
    
    # Week-based patterns
    if "next week" in text_lower:
        return reference_date + timedelta(weeks=1)
    elif "this week" in text_lower:
        # Return next Monday
        days_ahead = 0 - reference_date.weekday()
        if days_ahead < 0:
            days_ahead += 7
        return reference_date + timedelta(days=days_ahead)
    
    # Day count patterns
    days_match = re.search(r'in (\d+) days?', text_lower)
    if days_match:
        return reference_date + timedelta(days=int(days_match.group(1)))
    
    # Default to a week from now if no pattern matches
    return reference_date + timedelta(weeks=1)


def _parse_natural_language_time(text: str) -> Optional[str]:
    """Parse natural language time expressions to HH:MM format."""
    text_lower = text.lower().strip()
    
    # Direct time patterns
    time_patterns = [
        (r'(\d{1,2}):(\d{2})\s*(am|pm)?', lambda m: _format_time(m)),
        (r'(\d{1,2})\s*(am|pm)', lambda m: f"{_convert_12_to_24(int(m.group(1)), m.group(2)):02d}:00"),
    ]
    
    for pattern, parser in time_patterns:
        match = re.search(pattern, text_lower)
        if match:
            return parser(match)
    
    # Named time patterns - check for more specific patterns first
    if "afternoon" in text_lower:
        return "14:00"
    elif "morning" in text_lower:
        return "09:00"
    elif "noon" in text_lower:
        return "12:00"
    elif "evening" in text_lower:
        return "18:00"
    elif "night" in text_lower:
        return "20:00"
    
    return None


def _format_time(match) -> str:
    """Format time match to HH:MM."""
    hour = int(match.group(1))
    minute = int(match.group(2))
    ampm = match.group(3)
    
    if ampm:
        hour = _convert_12_to_24(hour, ampm)
    
    return f"{hour:02d}:{minute:02d}"


def _convert_12_to_24(hour: int, ampm: str) -> int:
    """Convert 12-hour format to 24-hour format."""
    if ampm == "pm" and hour != 12:
        return hour + 12
    elif ampm == "am" and hour == 12:
        return 0
    return hour


def _parse_priority(text: str) -> str:
    """Extract priority from natural language."""
    text_lower = text.lower()
    
    # Direct priority mentions
    if "high priority" in text_lower or "priority: high" in text_lower or "priority high" in text_lower:
        return "high"
    elif "medium priority" in text_lower or "priority: medium" in text_lower or "priority medium" in text_lower:
        return "medium"
    elif "low priority" in text_lower or "priority: low" in text_lower or "priority low" in text_lower:
        return "low"
    
    # Check for low priority keywords (before high to catch "not urgent")
    if any(word in text_lower for word in ["whenever", "not urgent"]):
        return "low"
    
    # Check for high priority keywords
    elif any(word in text_lower for word in ["urgent", "critical", "important", "asap"]):
        return "high"
    
    return "medium"


def _generate_task_id(tasks: List[Dict[str, Any]], prefix: str = "TASK") -> str:
    """Generate a unique task ID."""
    existing_ids = [task.get("id", "") for task in tasks]
    counter = 1
    while f"{prefix}-{counter}" in existing_ids:
        counter += 1
    return f"{prefix}-{counter}"


def insert_task(text: str, paths: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Insert a new task from natural language text."""
    if paths is None:
        paths = {'tasks': 'data/tasks.yaml'}
    
    try:
        tasks = _load_yaml(paths["tasks"]) or []
        if not isinstance(tasks, list):
            return {"error": "Invalid tasks file structure"}
        
        # Extract the actual task title by removing metadata
        title_text = text.strip()
        
        # Remove quotes around the entire text if present
        if (title_text.startswith('"') and title_text.endswith('"')) or \
           (title_text.startswith("'") and title_text.endswith("'")):
            title_text = title_text[1:-1]
        
        # Remove "with tag" or "with tags" phrases and everything after
        title_text = re.sub(r'\s+with\s+tags?\s+.*$', '', title_text, flags=re.IGNORECASE)
        
        # Remove priority indicators
        title_text = re.sub(r'\s*(,\s*)?(and\s+)?(high|medium|low)\s+priority\s*$', '', title_text, flags=re.IGNORECASE)
        title_text = re.sub(r'\s*priority:\s*(high|medium|low)\s*$', '', title_text, flags=re.IGNORECASE)
        
        # Remove standalone priority keywords that are likely metadata
        if title_text.endswith(' urgent') or title_text.endswith(' critical') or title_text.endswith(' important'):
            # Only remove if it's at the end and likely metadata
            title_text = re.sub(r'\s+(urgent|critical|important)\s*$', '', title_text, flags=re.IGNORECASE)
        
        # Remove tag indicators
        title_text = re.sub(r'\s+#\w+', '', title_text)  # Remove hashtags
        title_text = re.sub(r'\s+tags?:\s*[\w,\s]+$', '', title_text, flags=re.IGNORECASE)  # Remove "tag: word" at end
        
        # Remove hour estimates
        title_text = re.sub(r'\s+\d+(?:\.\d+)?\s*hours?\s*', ' ', title_text, flags=re.IGNORECASE)
        
        # Remove due date references
        title_text = re.sub(r'\s+by\s+(tomorrow|today|yesterday|next\s+week)\s*$', '', title_text, flags=re.IGNORECASE)
        title_text = re.sub(r'\s+due\s+(tomorrow|today|yesterday|next\s+week)\s*$', '', title_text, flags=re.IGNORECASE)
        title_text = re.sub(r'\s+by\s+\d{4}-\d{1,2}-\d{1,2}\s*$', '', title_text, flags=re.IGNORECASE)
        title_text = re.sub(r'\s+in\s+\d+\s+days?\s*$', '', title_text, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        title_text = re.sub(r'\s+', ' ', title_text).strip()
        
        # Remove trailing punctuation that might be left over
        title_text = title_text.rstrip(',;:')
        
        # Remove quotes if they're around the title
        title_text = title_text.strip('"\'')
        
        # Handle nested quotes (e.g., "'title'" becomes "title")
        if (title_text.startswith('"') and title_text.endswith('"')) or \
           (title_text.startswith("'") and title_text.endswith("'")):
            title_text = title_text[1:-1]
        
        # If title is empty after cleaning, use a default
        if not title_text:
            title_text = "New task"
        
        # Parse the natural language input
        task = {
            "id": _generate_task_id(tasks),
            "title": title_text,
            "priority": _parse_priority(text),
            "status": "pending",
            "tags": []
        }
        
        # Extract due date
        due_date = _parse_natural_language_date(text)
        task["due_date"] = due_date.isoformat()
        
        # Extract estimated hours if mentioned
        hours_match = re.search(r'(\d+(?:\.\d+)?)\s*hours?', text.lower())
        if hours_match:
            task["estimate_hours"] = float(hours_match.group(1))
        
        # Extract tags if mentioned
        tag_matches = []
        
        # Pattern 1: #tag format
        tag_matches.extend(re.findall(r'#(\w+)', text))
        
        # Pattern 2: "tags: word1, word2" or "tag: word"
        tags_colon_match = re.search(r'\btags?:\s*([^,\s]+(?:\s*,\s*[^,\s]+)*)', text, re.IGNORECASE)
        if tags_colon_match:
            tags_str = tags_colon_match.group(1)
            # Split by comma and clean each tag
            tags = [t.strip().strip('"\'') for t in tags_str.split(',')]
            tag_matches.extend(tags)
        
        # Pattern 3: "with tag(s) word1 and word2" or "with tag word"
        with_tags_match = re.search(r'\bwith\s+tags?\s+(.+?)(?:\s+(?:and|,)\s+(.+?))?(?:\s+and\s+|,|$)', text, re.IGNORECASE)
        if with_tags_match:
            # Get all captured groups
            for i in range(1, len(with_tags_match.groups()) + 1):
                tag = with_tags_match.group(i)
                if tag:
                    # Clean the tag
                    tag = tag.strip().strip('"\'')
                    # Remove any trailing priority/hour indicators
                    tag = re.sub(r'\s*(high|medium|low)?\s*priority.*$', '', tag, flags=re.IGNORECASE)
                    tag = re.sub(r'\s*\d+\s*hours?.*$', '', tag, flags=re.IGNORECASE)
                    if tag and tag not in ['and', ',']:
                        tag_matches.append(tag)
        
        # Pattern 4: standalone "tag 'word'"
        single_tag_matches = re.findall(r'\btag\s+[\'"]?(\w+)[\'"]?', text, re.IGNORECASE)
        tag_matches.extend(single_tag_matches)
        
        if tag_matches:
            # Convert to lowercase and remove duplicates
            task["tags"] = list(set(tag.lower() for tag in tag_matches))
        
        # Add the task and save
        tasks.append(task)
        _save_yaml(paths["tasks"], tasks)
        
        return {"success": True, "task": task}
    
    except Exception as e:
        return {"error": str(e)}


def insert_meeting(text: str, paths: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Insert a new meeting from natural language text."""
    if paths is None:
        paths = {'meets': 'data/meetings.yaml'}
    
    try:
        meetings = _load_yaml(paths["meets"])
        if meetings is None:
            meetings = []
        elif not isinstance(meetings, list):
            return {"error": "Invalid meetings file structure"}
        
        # Parse date and time
        meeting_date = _parse_natural_language_date(text)
        meeting_time = _parse_natural_language_time(text)
        
        if not meeting_time:
            # Default to 10:00 if no time specified
            meeting_time = "10:00"
        
        # Extract meeting title/event
        # Remove date/time references from the text to get cleaner event name
        event_text = text
        for pattern in [r'\d{4}-\d{1,2}-\d{1,2}', r'\d{1,2}:\d{2}', r'\b(today|tomorrow|yesterday)\b', 
                       r'\b(at|on|in)\s+\d+', r'\b\d+\s*(am|pm)\b', r'\bin\s+\d+\s+days?\b']:
            event_text = re.sub(pattern, '', event_text, flags=re.IGNORECASE)
        
        event_text = ' '.join(event_text.split()).strip()
        if not event_text:
            event_text = "Meeting"
        
        meeting = {
            "date": meeting_date.isoformat(),
            "time": meeting_time,
            "event": event_text
        }
        
        meetings.append(meeting)
        _save_yaml(paths["meets"], meetings)
        
        return {"success": True, "meeting": meeting}
    
    except Exception as e:
        return {"error": str(e)}


def insert_daily_log(text: str, task_id: str, hours: float, paths: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Insert a new daily log entry."""
    if paths is None:
        paths = {'logs': 'data/daily_logs.yaml'}
    
    try:
        logs = _load_yaml(paths["logs"]) or {}
        if not isinstance(logs, dict):
            return {"error": "Invalid daily logs file structure"}
        
        # Convert any date keys to strings for consistency
        logs = {str(k): v for k, v in logs.items()}
        
        # Use today's date by default
        log_date = datetime.now().date().isoformat()
        
        # Check if date is mentioned in text
        date_in_text = _parse_natural_language_date(text)
        # Only override if it's a different date (yesterday, specific date, etc.)
        if date_in_text and (date_in_text < datetime.now().date() or 
                           "yesterday" in text.lower() or 
                           re.search(r'\d{4}-\d{1,2}-\d{1,2}', text)):
            log_date = date_in_text.isoformat()
        
        # Create log entry
        log_entry = {
            "log_id": task_id,
            "description": text.strip(),
            "actual_hours": hours
        }
        
        # Add to logs
        if log_date not in logs:
            logs[log_date] = []
        logs[log_date].append(log_entry)
        
        _save_yaml(paths["logs"], logs)
        
        return {"success": True, "log": log_entry, "date": log_date}
    
    except Exception as e:
        return {"error": str(e)}


def remove_task(task_id: str, paths: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Remove a task by its ID."""
    if paths is None:
        paths = {'tasks': 'data/tasks.yaml'}
    
    try:
        tasks = _load_yaml(paths["tasks"]) or []
        if not isinstance(tasks, list):
            return {"error": "Invalid tasks file structure"}
        
        # Find and remove the task
        original_count = len(tasks)
        tasks = [task for task in tasks if task.get("id") != task_id]
        
        if len(tasks) == original_count:
            return {"error": f"Task with ID '{task_id}' not found"}
        
        # Save updated tasks
        _save_yaml(paths["tasks"], tasks)
        
        return {"success": True, "message": f"Task '{task_id}' removed successfully"}
    
    except Exception as e:
        return {"error": str(e)}


def remove_meeting(query: str, paths: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Remove a meeting based on natural language query."""
    if paths is None:
        paths = {'meets': 'data/meetings.yaml'}
    
    try:
        meetings = _load_yaml(paths["meets"]) or []
        if not isinstance(meetings, list):
            return {"error": "Invalid meetings file structure"}
        
        if not meetings:
            return {"error": "No meetings found"}
        
        # Parse date from query
        target_date = _parse_natural_language_date(query)
        target_date_str = target_date.isoformat()
        
        # Look for time in query
        target_time = _parse_natural_language_time(query)
        
        # Find matching meetings
        removed_meetings = []
        remaining_meetings = []
        
        for meeting in meetings:
            meeting_date = meeting.get("date", "")
            meeting_time = meeting.get("time", "")
            meeting_event = meeting.get("event", "").lower()
            
            # Check if this meeting matches the criteria
            date_match = meeting_date == target_date_str
            time_match = not target_time or meeting_time == target_time
            
            # Check if any keywords from the query match the event
            query_lower = query.lower()
            event_match = any(word in meeting_event for word in query_lower.split() 
                            if word not in ["remove", "delete", "cancel", "at", "on", "meeting"])
            
            if date_match and time_match and (not event_match or event_match):
                removed_meetings.append(meeting)
            else:
                remaining_meetings.append(meeting)
        
        if not removed_meetings:
            return {"error": f"No meetings found matching the criteria"}
        
        # If multiple meetings match, be more specific
        if len(removed_meetings) > 1 and not target_time:
            meeting_list = []
            for m in removed_meetings:
                meeting_list.append(f"- {m['date']} at {m['time']}: {m['event']}")
            return {
                "error": f"Multiple meetings found. Please be more specific:\n" + "\n".join(meeting_list)
            }
        
        # Save updated meetings
        _save_yaml(paths["meets"], remaining_meetings)
        
        removed = removed_meetings[0]
        return {
            "success": True, 
            "message": f"Removed meeting: {removed['event']} on {removed['date']} at {removed['time']}"
        }
    
    except Exception as e:
        return {"error": str(e)}


def remove_daily_log(query: str, task_id: Optional[str] = None, paths: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Remove a daily log entry based on date and optionally task ID."""
    if paths is None:
        paths = {'logs': 'data/daily_logs.yaml'}
    
    try:
        logs = _load_yaml(paths["logs"]) or {}
        if not isinstance(logs, dict):
            return {"error": "Invalid daily logs file structure"}
        
        # Convert any date keys to strings for consistency
        logs = {str(k): v for k, v in logs.items()}
        
        # Parse date from query
        target_date = _parse_natural_language_date(query)
        target_date_str = target_date.isoformat()
        
        if target_date_str not in logs:
            return {"error": f"No logs found for date {target_date_str}"}
        
        date_logs = logs[target_date_str]
        if not isinstance(date_logs, list):
            return {"error": f"Invalid log structure for date {target_date_str}"}
        
        if task_id:
            # Remove specific task log
            original_count = len(date_logs)
            date_logs = [log for log in date_logs if log.get("log_id") != task_id]
            
            if len(date_logs) == original_count:
                return {"error": f"No log found for task '{task_id}' on {target_date_str}"}
            
            # Update or remove the date entry
            if date_logs:
                logs[target_date_str] = date_logs
            else:
                del logs[target_date_str]
            
            _save_yaml(paths["logs"], logs)
            return {"success": True, "message": f"Removed log for task '{task_id}' on {target_date_str}"}
        else:
            # Remove all logs for the date
            del logs[target_date_str]
            _save_yaml(paths["logs"], logs)
            return {"success": True, "message": f"Removed all logs for {target_date_str}"}
    
    except Exception as e:
        return {"error": str(e)}


def _find_task_by_identifier(tasks: List[Dict[str, Any]], identifier: str) -> Optional[Dict[str, Any]]:
    """Find a task by ID or title (fuzzy match)."""
    identifier_lower = identifier.lower().strip()
    
    # First try exact ID match
    for task in tasks:
        if task.get("id", "").lower() == identifier_lower:
            return task
    
    # Then try exact title match
    for task in tasks:
        if task.get("title", "").lower() == identifier_lower:
            return task
    
    # Then try partial title match
    for task in tasks:
        if identifier_lower in task.get("title", "").lower():
            return task
    
    # Finally try fuzzy matching on title
    from difflib import get_close_matches
    titles = [(task.get("title", ""), task) for task in tasks]
    title_list = [t[0] for t in titles]
    matches = get_close_matches(identifier_lower, [t.lower() for t in title_list], n=1, cutoff=0.6)
    
    if matches:
        # Find the original task
        for title, task in titles:
            if title.lower() == matches[0]:
                return task
    
    return None


def update_task(query: str, paths: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Update a task's attributes based on natural language query."""
    if paths is None:
        paths = {'tasks': 'data/tasks.yaml'}
    
    try:
        tasks = _load_yaml(paths["tasks"]) or []
        if not isinstance(tasks, list):
            return {"error": "Invalid tasks file structure"}
        
        query_lower = query.lower()
        
        # Extract task identifier (ID or title)
        task_identifier = None
        task_to_update = None
        
        # Pattern 1: "update/change TASK-ID ..."
        task_id_match = re.search(r'\b([A-Z]+-\d+)\b', query)
        if task_id_match:
            task_identifier = task_id_match.group(1)
        else:
            # Pattern 2: Extract task name from phrases like "change status of X to Y"
            # Try various patterns
            patterns = [
                r'(?:update|change|modify|set)\s+(?:the\s+)?(\w+)\s+(?:of|for)\s+(.+?)\s+(?:to|as)',
                r'(?:update|change|modify)\s+(.+?)(?:\s+task)?[\'"]?\s+(\w+)\s+to',
                r'(?:mark|set)\s+(.+?)\s+(?:as|to)\s+',
                r'(?:update|change|modify)\s+(.+?)\s+to\s+'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    # The task name is usually in the second group for first pattern
                    if 'of' in pattern and match.group(2):
                        task_identifier = match.group(2).strip().strip('"\'')
                    elif match.group(1):
                        task_identifier = match.group(1).strip().strip('"\'')
                    break
        
        if not task_identifier:
            return {"error": "Could not identify which task to update"}
        
        # Find the task
        task_to_update = _find_task_by_identifier(tasks, task_identifier)
        if not task_to_update:
            return {"error": f"Task '{task_identifier}' not found"}
        
        # Store original values for summary
        original_values = {}
        updated_fields = []
        
        # Update status
        status_patterns = [
            (r'\b(?:to|as)\s+(pending|in[_\s-]?progress|completed|done|finished)\b', lambda m: m.group(1)),
            (r'\bstatus\s+(?:to|as|=)\s*["\']?([^"\'\s]+)["\']?', lambda m: m.group(1)),
            (r'\bmark(?:ed)?\s+(?:as\s+)?(?:task\s+)?(completed|done|finished|in[_\s-]?progress)\b', lambda m: m.group(1))
        ]
        
        for pattern, extractor in status_patterns:
            match = re.search(pattern, query_lower)
            if match:
                new_status = extractor(match).replace(' ', '_').replace('-', '_')
                # Normalize status values
                if new_status in ['done', 'finished']:
                    new_status = 'completed'
                elif new_status == 'in_progress':
                    new_status = 'in_progress'
                
                if new_status in ['pending', 'in_progress', 'completed']:
                    original_values['status'] = task_to_update.get('status')
                    task_to_update['status'] = new_status
                    updated_fields.append('status')
                break
        
        # Update priority
        if 'priority' in query_lower:
            priority_match = re.search(r'priority\s+(?:to|as|=)\s*["\']?(high|medium|low)["\']?', query_lower)
            if priority_match:
                original_values['priority'] = task_to_update.get('priority')
                task_to_update['priority'] = priority_match.group(1)
                updated_fields.append('priority')
        
        # Update due date
        if any(keyword in query_lower for keyword in ['due', 'deadline', 'by']):
            # Extract the new date
            date_match = re.search(r'(?:due|deadline|by)\s+(?:date\s+)?(?:to\s+)?(.+?)(?:\s*$|,)', query_lower)
            if date_match:
                date_text = date_match.group(1).strip()
                new_date = _parse_natural_language_date(date_text)
                if new_date:
                    original_values['due_date'] = task_to_update.get('due_date')
                    task_to_update['due_date'] = new_date.isoformat()
                    updated_fields.append('due_date')
        
        # Update estimated hours
        if 'hours' in query_lower or 'estimate' in query_lower:
            hours_match = re.search(r'(?:to|=)\s*(\d+(?:\.\d+)?)\s*hours?', query_lower)
            if hours_match:
                original_values['estimate_hours'] = task_to_update.get('estimate_hours')
                task_to_update['estimate_hours'] = float(hours_match.group(1))
                updated_fields.append('estimate_hours')
        
        # Update tags
        if any(keyword in query_lower for keyword in ['tag', 'tags', '#']):
            # Check if we're adding or replacing tags
            if 'add' in query_lower or 'append' in query_lower:
                # Add tags to existing
                original_values['tags'] = task_to_update.get('tags', [])[:]
                existing_tags = task_to_update.get('tags', [])
                new_tags = []
                
                # Extract new tags
                tag_matches = re.findall(r'#(\w+)', query)
                new_tags.extend(tag_matches)
                
                # Look for patterns like "tags word1, word2 to TASK-1"
                tags_match = re.search(r'add\s+tags?\s+(.+?)\s+(?:to|for)\s+', query_lower)
                if tags_match:
                    tags_str = tags_match.group(1).strip()
                    # Split by comma and/or "and"
                    # First split by comma
                    parts = [p.strip() for p in tags_str.split(',')]
                    for part in parts:
                        # Then check each part for "and"
                        if ' and ' in part:
                            new_tags.extend([t.strip() for t in part.split(' and ')])
                        else:
                            new_tags.append(part)
                
                # Combine and deduplicate
                task_to_update['tags'] = list(set(existing_tags + [t.lower() for t in new_tags]))
                updated_fields.append('tags')
            else:
                # Replace tags
                original_values['tags'] = task_to_update.get('tags', [])[:]
                new_tags = []
                
                # Extract new tags
                tag_matches = re.findall(r'#(\w+)', query)
                new_tags.extend(tag_matches)
                
                tags_match = re.search(r'tags?\s+(?:to\s+)?["\']?([^"\']+)["\']?', query_lower)
                if tags_match:
                    tags_str = tags_match.group(1)
                    new_tags.extend([t.strip() for t in tags_str.split(',')])
                
                if new_tags:
                    task_to_update['tags'] = list(set(t.lower() for t in new_tags))
                    updated_fields.append('tags')
        
        # Update title
        if 'title' in query_lower or 'rename' in query_lower:
            # Look for patterns like "rename TASK-1 to new title"
            title_match = re.search(r'(?:title|rename)\s+[A-Z]+-\d+\s+to\s+(.+?)$', query, re.IGNORECASE)
            if not title_match:
                # Try simpler pattern
                title_match = re.search(r'(?:title|rename)\s+to\s+(.+?)$', query, re.IGNORECASE)
            
            if title_match:
                original_values['title'] = task_to_update.get('title')
                new_title = title_match.group(1).strip().strip('"\'')
                task_to_update['title'] = new_title
                updated_fields.append('title')
        
        if not updated_fields:
            return {"error": "No valid updates found in the query"}
        
        # Save the updated tasks
        _save_yaml(paths["tasks"], tasks)
        
        # Prepare summary
        summary_parts = []
        for field in updated_fields:
            old_val = original_values.get(field)
            if old_val is None:
                old_val = 'not set'
            new_val = task_to_update.get(field)
            if field == 'tags' and isinstance(old_val, list):
                old_val = ', '.join(old_val) if old_val else 'none'
            if field == 'tags' and isinstance(new_val, list):
                new_val = ', '.join(new_val) if new_val else 'none'
            summary_parts.append(f"{field}: {old_val} → {new_val}")
        
        return {
            "success": True,
            "task_id": task_to_update['id'],
            "task_title": task_to_update['title'],
            "updates": summary_parts,
            "message": f"Updated task '{task_to_update['title']}' ({task_to_update['id']}): " + "; ".join(summary_parts)
        }
    
    except Exception as e:
        return {"error": str(e)}


def plan_day(payload: Dict[str, Any]) -> Dict[str, str]:
    try:
        # Use default paths if not provided
        default_paths = {
            'tasks': 'data/tasks.yaml',
            'logs': 'data/daily_logs.yaml',
            'meets': 'data/meetings.yaml',
            'meeting_notes': 'data/meeting_notes'
        }
        paths = payload.get("paths", default_paths)
        target_date = datetime.fromisoformat(payload["target_date"]).date()
        work_hours = payload["work_hours"]
    except Exception as exc:
        return {"error": str(exc)}

    try:
        tasks = _load_yaml(paths["tasks"])
        logs = _load_yaml(paths["logs"]) or {}
        if isinstance(logs, dict):
            logs = {str(k): v for k, v in logs.items()}
        meetings = _load_yaml(paths["meets"]) or []
    except Exception as exc:
        return {"error": str(exc)}

    if not isinstance(tasks, list) or not isinstance(logs, dict) or not isinstance(meetings, list):
        return {"error": "Invalid YAML structure"}

    yesterday_md = _get_yesterday_summary(logs, target_date, meetings)
    
    # Filter out completed tasks with any completion status
    completion_statuses = {"done", "completed", "finished", "complete", "cancelled", "canceled"}
    pending = [t for t in tasks if t.get("status", "").lower() not in completion_statuses]
    
    pending.sort(key=lambda t: _score_task(t, target_date), reverse=True)
    free = _compute_free_intervals(meetings, target_date, work_hours["start"], work_hours["end"])
    plan = _pack_tasks(pending, free)

    # Generate focus list from recent meeting notes
    focus_analysis = {}
    try:
        notes_path = paths.get("meeting_notes", "data/meeting_notes")
        recent_notes = _find_recent_meeting_notes(notes_path, target_date, days_back=3)
        
        if recent_notes and pending:
            # Generate comprehensive focus analysis
            use_llm = payload.get("use_llm_for_focus", True)
            focus_analysis = generate_focus_list(recent_notes, pending, use_llm=use_llm)
        
    except Exception as e:
        # Don't fail the entire planning if meeting notes analysis fails
        focus_analysis = {"error": str(e)}

    # Format the plan with focus analysis included
    tomorrow_md = _format_plan(plan, target_date, meetings, focus_analysis)

    return {
        "yesterday_markdown": yesterday_md, 
        "tomorrow_markdown": tomorrow_md,
        "focus_analysis": focus_analysis
    }
