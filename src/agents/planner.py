from __future__ import annotations

import os
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import yaml


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


def _format_plan(plan: List[Tuple[datetime, datetime, Dict[str, Any]]], target_date: datetime.date, meetings: List[Dict[str, Any]] = None) -> str:
    # Get meetings for the target date
    target_meetings = _get_target_date_meetings(meetings or [], target_date)
    
    # Start with the header
    content = [f"## Plan for {target_date.isoformat()}"]
    
    # Add meetings section if there are any
    if target_meetings:
        content.append("\n### Meetings")
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


def plan_day(payload: Dict[str, Any]) -> Dict[str, str]:
    try:
        # Use default paths if not provided
        default_paths = {
            'tasks': 'data/tasks.yaml',
            'logs': 'data/daily_logs.yaml',
            'meets': 'data/meetings.yaml'
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
    tomorrow_md = _format_plan(plan, target_date, meetings)

    return {"yesterday_markdown": yesterday_md, "tomorrow_markdown": tomorrow_md}
