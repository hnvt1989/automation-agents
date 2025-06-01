import yaml
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Tuple


class PlannerAgent:
    """Generate a daily plan from YAML task, log and meeting data."""

    def _load_yaml(self, path: str) -> Any:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            raise ValueError(f"File not found: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Malformed YAML in {path}: {e}")

    def _validate_inputs(self, tasks: Any, logs: Any, meetings: Any) -> None:
        if not isinstance(tasks, list):
            raise ValueError("tasks.yaml should contain a list")
        if not isinstance(logs, dict):
            raise ValueError("daily_logs.yaml should contain a mapping")
        if not isinstance(meetings, list):
            raise ValueError("meetings.yaml should contain a list")

    def _summarize_logs(self, logs: Dict[str, Any], yesterday: date) -> str:
        entries = logs.get(str(yesterday), [])
        bullets: List[str] = []
        if not isinstance(entries, list) or not entries:
            bullets.append(f"- No logs for {yesterday}")
        else:
            for entry in entries[:5]:
                desc = str(entry.get("description", "")).split()
                bullet = " ".join(desc[:20])
                tid = entry.get("task_id")
                if tid:
                    bullet = f"{tid}: {bullet}"
                bullets.append(f"- {bullet}")
        summary = f"## {yesterday}\n" + "\n".join(bullets)
        return summary

    def _parse_time(self, date_str: str, t: str) -> datetime:
        return datetime.fromisoformat(f"{date_str}T{t}")

    def _free_intervals(self, target: date, work_hours: Dict[str, str], meetings: List[Dict[str, Any]]) -> List[Tuple[datetime, datetime]]:
        start = self._parse_time(str(target), work_hours["start"])
        end = self._parse_time(str(target), work_hours["end"])
        start = start.replace(tzinfo=None)
        end = end.replace(tzinfo=None)
        intervals = [(start, end)]
        for mt in meetings:
            try:
                mstart = datetime.fromisoformat(mt["start"]).astimezone(None).replace(tzinfo=None)
                mend = datetime.fromisoformat(mt["end"]).astimezone(None).replace(tzinfo=None)
            except Exception:
                continue
            if mstart.date() != target:
                continue
            new_intervals = []
            for a, b in intervals:
                if mend <= a or mstart >= b:
                    new_intervals.append((a, b))
                    continue
                if mstart > a:
                    new_intervals.append((a, mstart))
                if mend < b:
                    new_intervals.append((mend, b))
            intervals = new_intervals
        intervals.sort()
        return intervals

    def _score_tasks(self, tasks: List[Dict[str, Any]], target: date) -> List[Dict[str, Any]]:
        pri_map = {"high": 3, "medium": 2, "low": 1}
        scored = []
        for t in tasks:
            if t.get("status") == "done":
                continue
            try:
                due = date.fromisoformat(t.get("due_date"))
            except Exception:
                due = target
            days = (due - target).days
            pri = pri_map.get(t.get("priority"), 0)
            score = pri * 10 - days
            t["_score"] = score
            scored.append(t)
        scored.sort(key=lambda x: x["_score"], reverse=True)
        return scored

    def _allocate(self, tasks: List[Dict[str, Any]], intervals: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime, Dict[str, Any]]]:
        schedule = []
        for t in tasks:
            est = t.get("estimate_hours", 1)
            for i, (start, end) in enumerate(list(intervals)):
                free_hours = (end - start).total_seconds() / 3600
                if free_hours >= est:
                    finish = start + timedelta(hours=est)
                    schedule.append((start, finish, t))
                    intervals[i] = (finish, end)
                    break
        schedule.sort(key=lambda x: x[0])
        return schedule

    def _plan_markdown(self, schedule: List[Tuple[datetime, datetime, Dict[str, Any]]], target: date) -> str:
        lines = [f"## Plan for {target}", "| Time | Task | Reason |", "|---|---|---|"]
        for start, end, t in schedule:
            reason = f"{t.get('priority', '').capitalize()} priority"
            try:
                due = date.fromisoformat(t.get("due_date"))
                if due <= target:
                    reason += " due"
                elif (due - target).days <= 2:
                    reason += " due soon"
            except Exception:
                pass
            task_text = f"{t.get('id')} {t.get('title')}"
            time_str = f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"
            lines.append(f"| {time_str} | {task_text} | {reason} |")
        return "\n".join(lines)

    def plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            paths = payload["paths"]
            target = date.fromisoformat(payload["target_date"])
            work_hours = payload["work_hours"]
        except Exception as e:
            return {"error": f"Invalid input: {e}"}

        try:
            tasks = self._load_yaml(paths["tasks"])
            logs = self._load_yaml(paths["logs"])
            meetings = self._load_yaml(paths["meets"])
            self._validate_inputs(tasks, logs, meetings)
        except Exception as e:
            return {"error": str(e)}

        yesterday_md = self._summarize_logs(logs, target - timedelta(days=1))
        intervals = self._free_intervals(target, work_hours, meetings)
        scored_tasks = self._score_tasks(tasks, target)
        schedule = self._allocate(scored_tasks, intervals)
        tomorrow_md = self._plan_markdown(schedule, target)
        return {"yesterday_markdown": yesterday_md, "tomorrow_markdown": tomorrow_md}
