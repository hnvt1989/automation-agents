import yaml
from datetime import datetime, timedelta
from typing import Any, List, Dict


class PlannerAgent:
    """Generate daily summaries and time-block plans from YAML files."""

    def _load_yaml(self, path: str) -> Any:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _yesterday_summary(self, logs: Dict[str, List[dict]], target_date: datetime) -> str:
        yesterday = (target_date - timedelta(days=1)).strftime("%Y-%m-%d")
        entries = logs.get(yesterday, [])
        bullets = []
        for entry in entries:
            desc = entry.get("description", "")
            words = desc.split()
            bullet = " ".join(words[:20])
            bullets.append(f"- {bullet}")
            if len(bullets) == 5:
                break
        return f"## {yesterday}\n" + "\n".join(bullets)

    def _available_intervals(self, start: datetime, end: datetime, meetings: List[dict]) -> List[List[datetime]]:
        day_meetings = []
        for m in meetings:
            try:
                s = datetime.fromisoformat(m["start"]).replace(tzinfo=None)
                e = datetime.fromisoformat(m["end"]).replace(tzinfo=None)
            except Exception:
                continue
            if s.date() == start.date():
                day_meetings.append((s, e))
        day_meetings.sort()
        intervals = []
        current = start
        for s, e in day_meetings:
            if e <= current:
                continue
            if s > current:
                intervals.append([current, min(s, end)])
            current = max(current, e)
            if current >= end:
                break
        if current < end:
            intervals.append([current, end])
        return [i for i in intervals if i[1] > i[0]]

    def _score_task(self, task: dict, target_date: datetime) -> int:
        priority_score = {"high": 3, "medium": 2, "low": 1}.get(task.get("priority"), 1)
        due = datetime.fromisoformat(task["due_date"])
        due_in = (due - target_date).days
        due_score = max(0, 10 - due_in)
        return priority_score * 10 + due_score

    def _plan_tasks(self, tasks: List[dict], intervals: List[List[datetime]], target_date: datetime) -> str:
        pending = [t for t in tasks if t.get("status") != "done"]
        ordered = sorted(pending, key=lambda t: self._score_task(t, target_date), reverse=True)
        lines = [f"## Plan for {target_date.strftime('%Y-%m-%d')}", "| Time | Task | Reason |", "|------|------|--------|"]
        for task in ordered:
            hours = task.get("estimate_hours", 1)
            reason_parts = []
            if task.get("priority") == "high":
                reason_parts.append("high priority")
            if datetime.fromisoformat(task["due_date"]) <= target_date:
                reason_parts.append("due soon")
            reason = " ".join(reason_parts) or "scheduled"
            while hours > 0 and intervals:
                s, e = intervals[0]
                avail = (e - s).seconds / 3600
                if avail <= 0:
                    intervals.pop(0)
                    continue
                block = min(hours, avail)
                block_end = s + timedelta(hours=block)
                lines.append(
                    f"| {s.strftime('%H:%M')}-{block_end.strftime('%H:%M')} | {task['id']} {task['title']} | {reason} |"
                )
                if block == avail:
                    intervals.pop(0)
                else:
                    intervals[0][0] = block_end
                hours -= block
                if not intervals:
                    break
            if not intervals:
                break
        return "\n".join(lines)

    def run(self, payload: dict) -> Dict[str, str]:
        try:
            tasks = self._load_yaml(payload["paths"]["tasks"])
            logs = self._load_yaml(payload["paths"]["logs"])
            meetings = self._load_yaml(payload["paths"]["meets"])
        except Exception as e:
            return {"error": f"Failed to load YAML: {e}"}
        try:
            target_date = datetime.fromisoformat(payload["target_date"])
            work_start = datetime.combine(target_date, datetime.strptime(payload["work_hours"]["start"], "%H:%M").time())
            work_end = datetime.combine(target_date, datetime.strptime(payload["work_hours"]["end"], "%H:%M").time())
        except Exception as e:
            return {"error": f"Invalid date format: {e}"}

        summary = self._yesterday_summary(logs, target_date)
        intervals = self._available_intervals(work_start, work_end, meetings)
        plan = self._plan_tasks(tasks, intervals, target_date)
        return {"yesterday_markdown": summary, "tomorrow_markdown": plan}
