import yaml
from pathlib import Path
from datetime import datetime, timedelta, time
from typing import Any, Dict, List, Tuple

class PlannerAgent:
    """Generate a daily plan from YAML task, log and meeting files."""

    def _load_yaml(self, path: Path, default: Any, expected_type: type) -> Any:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as fh:
                yaml.safe_dump(default, fh)
            return default
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if data is None:
            return default
        if not isinstance(data, expected_type):
            raise ValueError(f"Unexpected YAML type in {path}")
        return data

    def _summarize_logs(self, logs: Dict[str, List[Dict[str, Any]]], day: str) -> str:
        entries = logs.get(day, [])
        bullets: List[str] = [f"## {day}"]
        if not entries:
            bullets.append("- No log entries.")
        else:
            for entry in entries[:5]:
                desc = entry.get("description", "")
                words = desc.split()
                if len(words) > 20:
                    desc = " ".join(words[:20])
                bullets.append(f"- {desc}")
        return "\n".join(bullets)

    def _compute_free_slots(
        self,
        target_date: datetime,
        work_start: time,
        work_end: time,
        meetings: List[Dict[str, Any]],
    ) -> List[Tuple[datetime, datetime]]:
        start_dt = datetime.combine(target_date, work_start)
        end_dt = datetime.combine(target_date, work_end)
        free: List[Tuple[datetime, datetime]] = [(start_dt, end_dt)]
        for meet in meetings:
            try:
                m_start = datetime.fromisoformat(meet["start"])
                m_end = datetime.fromisoformat(meet["end"])
                if m_start.tzinfo:
                    m_start = m_start.astimezone().replace(tzinfo=None)
                if m_end.tzinfo:
                    m_end = m_end.astimezone().replace(tzinfo=None)
            except Exception:
                continue
            if m_start.date() != target_date.date():
                continue
            new_free: List[Tuple[datetime, datetime]] = []
            for fs, fe in free:
                if fe <= m_start or fs >= m_end:
                    new_free.append((fs, fe))
                    continue
                if fs < m_start:
                    new_free.append((fs, m_start))
                if fe > m_end:
                    new_free.append((m_end, fe))
            free = new_free
        return free

    def _score_tasks(self, tasks: List[Dict[str, Any]], target_date: datetime) -> List[Dict[str, Any]]:
        priority_map = {"high": 3, "medium": 2, "low": 1}
        scored: List[Dict[str, Any]] = []
        for t in tasks:
            if t.get("status") == "done":
                continue
            try:
                due = datetime.strptime(t["due_date"], "%Y-%m-%d")
            except Exception:
                due = target_date
            p_score = priority_map.get(t.get("priority", "low"), 1)
            due_days = (due.date() - target_date.date()).days
            score = p_score * 100 - due_days
            t_copy = dict(t)
            t_copy["_score"] = score
            scored.append(t_copy)
        scored.sort(key=lambda x: x["_score"], reverse=True)
        return scored

    def generate_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            task_path = Path(payload["paths"]["tasks"])
            log_path = Path(payload["paths"]["logs"])
            meet_path = Path(payload["paths"]["meets"])
            tasks = self._load_yaml(task_path, [], list)
            logs = self._load_yaml(log_path, {}, dict)
            meetings = self._load_yaml(meet_path, [], list)
        except yaml.YAMLError as e:
            return {"error": f"Failed to parse YAML: {e}"}
        except Exception as e:
            return {"error": str(e)}

        try:
            target_date = datetime.strptime(payload["target_date"], "%Y-%m-%d")
            wh_start = datetime.strptime(payload["work_hours"]["start"], "%H:%M").time()
            wh_end = datetime.strptime(payload["work_hours"]["end"], "%H:%M").time()
        except Exception as e:
            return {"error": f"Invalid date or time: {e}"}

        yesterday = (target_date - timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_md = self._summarize_logs(logs, yesterday)

        free_slots = self._compute_free_slots(target_date, wh_start, wh_end, meetings)
        tasks_sorted = self._score_tasks(tasks, target_date)

        plan_rows: List[str] = []
        slot_index = 0
        for t in tasks_sorted:
            remaining = timedelta(hours=int(t.get("estimate_hours", 1)))
            while remaining > timedelta() and slot_index < len(free_slots):
                fs, fe = free_slots[slot_index]
                avail = fe - fs
                block_start = fs
                block_end = fs + min(avail, remaining)
                free_slots[slot_index] = (block_end, fe)
                if free_slots[slot_index][0] >= fe:
                    slot_index += 1
                remaining -= (block_end - block_start)
                tb = f"{block_start.strftime('%H:%M')}-{block_end.strftime('%H:%M')}"
                reason = f"priority {t.get('priority')} due {t.get('due_date')}"
                plan_rows.append(f"| {tb} | {t.get('id')} {t.get('title')} | {reason} |")
                if remaining <= timedelta():
                    break
            if slot_index >= len(free_slots):
                break

        tomorrow_md_lines = [f"## Plan for {target_date.strftime('%Y-%m-%d')}", "| Time | Task | Reason |", "|---|---|---|"]
        tomorrow_md_lines.extend(plan_rows)
        tomorrow_md = "\n".join(tomorrow_md_lines)
        return {"yesterday_markdown": yesterday_md, "tomorrow_markdown": tomorrow_md}
