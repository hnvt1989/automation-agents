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


def _get_yesterday_summary(logs: Dict[str, Any], target_date: datetime.date) -> str:
    yesterday = target_date - timedelta(days=1)
    entries = logs.get(yesterday.isoformat(), []) or []
    bullets: List[str] = []
    for entry in entries[:5]:
        desc = str(entry.get("description", "")).strip()
        if not desc:
            continue
        words = desc.split()
        bullet = " ".join(words[:20])
        bullets.append(f"- {bullet}")
    if not bullets:
        bullets.append("- No log entries")
    return f"## {yesterday.isoformat()}\n" + "\n".join(bullets)


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
        remaining = int(task.get("estimate_hours", 1))
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


def _format_plan(plan: List[Tuple[datetime, datetime, Dict[str, Any]]], target_date: datetime.date) -> str:
    header = f"## Plan for {target_date.isoformat()}\n| Time | Task | Reason |\n| - | - | - |"
    rows: List[str] = []
    for st, et, task in plan:
        block = f"{st.strftime('%H:%M')}-{et.strftime('%H:%M')}"
        reason = f"Priority {task.get('priority')}, due {task.get('due_date')}"
        rows.append(f"| {block} | {task.get('id')} {task.get('title')} | {reason} |")
    if not rows:
        rows.append("No tasks scheduled.")
    return header + "\n" + "\n".join(rows)


def plan_day(payload: Dict[str, Any]) -> Dict[str, str]:
    try:
        paths = payload["paths"]
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

    yesterday_md = _get_yesterday_summary(logs, target_date)
    pending = [t for t in tasks if t.get("status") != "done"]
    pending.sort(key=lambda t: _score_task(t, target_date), reverse=True)
    free = _compute_free_intervals(meetings, target_date, work_hours["start"], work_hours["end"])
    plan = _pack_tasks(pending, free)
    tomorrow_md = _format_plan(plan, target_date)

    return {"yesterday_markdown": yesterday_md, "tomorrow_markdown": tomorrow_md}
