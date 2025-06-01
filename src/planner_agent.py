import os
import yaml
from datetime import datetime, timedelta
from typing import Any, Dict, List

from src.log_utils import log_info, log_warning, log_error

PRIORITY_SCORE = {"high": 3, "medium": 2, "low": 1}

TASKS_TEMPLATE = """- id: T1
  title: Sample Task
  priority: medium
  estimate_hours: 1
  due_date: 2099-01-01
  status: pending
  tags: []
"""

LOGS_TEMPLATE = """2099-01-01:
  - task_id: T1
    description: Did some work
    actual_hours: 1.0
"""

MEETINGS_TEMPLATE = """- id: M1
  title: Example Meeting
  start: 2099-01-01T10:00+00:00
  end: 2099-01-01T10:30+00:00
  participants: [you]
"""

def _load_yaml(path: str, template: str) -> Any:
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(template)
        log_warning(f"Created template file: {path}")
        return None
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        log_error(f"Failed to load {path}: {e}")
        return None

def _parse_time(date_str: str, time_str: str) -> datetime:
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

def _free_intervals(start: datetime, end: datetime, meetings: List[dict]) -> List[tuple]:
    busy = []
    for m in meetings:
        try:
            m_start = datetime.fromisoformat(m["start"]).replace(tzinfo=None)
            m_end = datetime.fromisoformat(m["end"]).replace(tzinfo=None)
            if m_start.date() == start.date():
                busy.append((m_start, m_end))
        except Exception as e:
            log_warning(f"Bad meeting entry {m}: {e}")
    busy.sort()
    free = []
    cur = start
    for b_start, b_end in busy:
        if b_start > cur:
            free.append((cur, min(b_start, end)))
        cur = max(cur, b_end)
        if cur >= end:
            break
    if cur < end:
        free.append((cur, end))
    return free

def _score(task: dict, target_date: datetime) -> int:
    p = PRIORITY_SCORE.get(task.get("priority", "low"), 1)
    try:
        due = datetime.strptime(task.get("due_date"), "%Y-%m-%d").date()
        delta = (due - target_date.date()).days
        due_score = max(0, 10 - delta)
    except Exception:
        due_score = 0
    return p * 10 + due_score

def plan_day(payload: Dict[str, Any]) -> Dict[str, Any]:
    paths = payload.get("paths", {})
    target_date = payload.get("target_date")
    work_hours = payload.get("work_hours", {})

    if not target_date:
        return {"error": "target_date missing"}

    tasks = _load_yaml(paths.get("tasks", "tasks.yaml"), TASKS_TEMPLATE)
    logs = _load_yaml(paths.get("logs", "daily_logs.yaml"), LOGS_TEMPLATE)
    meets = _load_yaml(paths.get("meets", "meetings.yaml"), MEETINGS_TEMPLATE)

    if tasks is None or logs is None or meets is None:
        return {"error": "Template files created. Please populate them and run again."}

    yesterday = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    log_entries = logs.get(yesterday, []) if isinstance(logs, dict) else []

    bullets = []
    for entry in log_entries[:5]:
        desc = entry.get("description", "")
        words = desc.split()[:20]
        bullet = " ".join(words)
        bullets.append(f"- {bullet}")
    if not bullets:
        bullets.append("- No entries")
    yesterday_md = f"## {yesterday}\n" + "\n".join(bullets)

    start_time = _parse_time(target_date, work_hours.get("start", "09:00"))
    end_time = _parse_time(target_date, work_hours.get("end", "17:00"))
    free_slots = _free_intervals(start_time, end_time, meets or [])
    total_free = sum((b - a).seconds for a, b in free_slots) / 3600

    candidates = [t for t in tasks if t.get("status") != "done"]
    candidates.sort(key=lambda x: _score(x, datetime.strptime(target_date, "%Y-%m-%d")), reverse=True)

    plan_rows = []
    slot_index = 0
    current = free_slots[slot_index][0] if free_slots else None
    remaining_slot_end = free_slots[slot_index][1] if free_slots else None

    for task in candidates:
        est = task.get("estimate_hours", 1)
        if est > total_free:
            continue
        while est > 0 and slot_index < len(free_slots):
            if current >= remaining_slot_end:
                slot_index += 1
                if slot_index >= len(free_slots):
                    break
                current = free_slots[slot_index][0]
                remaining_slot_end = free_slots[slot_index][1]
            available = (remaining_slot_end - current).seconds / 3600
            if available <= 0:
                current = remaining_slot_end
                continue
            use = min(available, est)
            start_block = current
            end_block = current + timedelta(hours=use)
            reason = f"priority {task.get('priority')}".strip()
            plan_rows.append(f"| {start_block.strftime('%H:%M')}-{end_block.strftime('%H:%M')} | {task.get('id')} {task.get('title')} | {reason} |")
            current = end_block
            est -= use
            total_free -= use
        if total_free <= 0:
            break

    if not plan_rows:
        plan_rows.append("| N/A | No tasks scheduled | |")

    plan_md = f"## Plan for {target_date}\n| Time | Task | Reason |\n|---|---|---|\n" + "\n".join(plan_rows)
    return {
        "yesterday_markdown": yesterday_md,
        "tomorrow_markdown": plan_md,
    }
