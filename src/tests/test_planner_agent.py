import json
from datetime import date
from pathlib import Path

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.planner_agent import plan_day


def test_planner_success(tmp_path: Path):
    tasks = tmp_path / "tasks.yaml"
    logs = tmp_path / "daily_logs.yaml"
    meets = tmp_path / "meetings.yaml"

    tasks.write_text(
        """
- id: T1
  title: Finish report
  priority: high
  estimate_hours: 2
  due_date: 2024-05-02
  status: pending
  tags: []
- id: T2
  title: Email client
  priority: medium
  estimate_hours: 1
  due_date: 2024-05-03
  status: pending
  tags: []
"""
    )

    logs.write_text(
        """
2024-05-01:
  - task_id: T1
    description: Completed initial draft
    actual_hours: 1
"""
    )

    meets.write_text(
        """
- id: M1
  title: Sync
  start: 2024-05-02T10:00+00:00
  end: 2024-05-02T11:00+00:00
  participants: [alice]
"""
    )

    payload = {
        "paths": {"tasks": str(tasks), "logs": str(logs), "meets": str(meets)},
        "target_date": "2024-05-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
    }

    result = plan_day(payload)
    expected = {
        "yesterday_markdown": "## 2024-05-01\n- Completed initial draft",
        "tomorrow_markdown": (
            "## Plan for 2024-05-02\n| Time | Task | Reason |\n| - | - | - |\n"
            "| 09:00-10:00 | T1 Finish report | Priority high, due 2024-05-02 |\n"
            "| 11:00-12:00 | T1 Finish report | Priority high, due 2024-05-02 |\n"
            "| 12:00-13:00 | T2 Email client | Priority medium, due 2024-05-03 |"
        ),
    }
    assert result == expected


def test_planner_bad_yaml(tmp_path: Path):
    tasks = tmp_path / "tasks.yaml"
    logs = tmp_path / "daily_logs.yaml"
    meets = tmp_path / "meetings.yaml"

    tasks.write_text("not: [valid")
    logs.write_text("")
    meets.write_text("[]")

    payload = {
        "paths": {"tasks": str(tasks), "logs": str(logs), "meets": str(meets)},
        "target_date": "2024-05-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
    }

    result = plan_day(payload)
    assert "error" in result
