import os
import sys
import yaml

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.planner_agent import PlannerAgent


def test_generate_plan(tmp_path):
    tasks = [
        {
            "id": "T1",
            "title": "Task One",
            "priority": "high",
            "estimate_hours": 2,
            "due_date": "2025-06-02",
            "status": "pending",
            "tags": [],
        },
        {
            "id": "T2",
            "title": "Task Two",
            "priority": "low",
            "estimate_hours": 1,
            "due_date": "2025-06-05",
            "status": "in_progress",
            "tags": [],
        },
    ]
    logs = {
        "2025-05-31": [
            {"task_id": "T1", "description": "Worked on T1", "actual_hours": 2.0}
        ]
    }
    meetings = [
        {
            "id": "M1",
            "title": "Sync",
            "start": "2025-06-01T13:00+00:00",
            "end": "2025-06-01T14:00+00:00",
            "participants": [],
        }
    ]

    tasks_p = tmp_path / "tasks.yaml"
    logs_p = tmp_path / "logs.yaml"
    meets_p = tmp_path / "meets.yaml"
    tasks_p.write_text(yaml.safe_dump(tasks))
    logs_p.write_text(yaml.safe_dump(logs))
    meets_p.write_text(yaml.safe_dump(meetings))

    payload = {
        "paths": {
            "tasks": str(tasks_p),
            "logs": str(logs_p),
            "meets": str(meets_p),
        },
        "target_date": "2025-06-01",
        "work_hours": {"start": "09:00", "end": "17:00"},
        "feedback": "",
    }

    agent = PlannerAgent()
    result = agent.run(payload)

    assert "yesterday_markdown" in result
    assert "tomorrow_markdown" in result


def test_yaml_error(tmp_path):
    bad = tmp_path / "tasks.yaml"
    bad.write_text("this is: [broken")
    logs = tmp_path / "logs.yaml"
    logs.write_text("{}")
    meets = tmp_path / "meets.yaml"
    meets.write_text("[]")

    payload = {
        "paths": {"tasks": str(bad), "logs": str(logs), "meets": str(meets)},
        "target_date": "2025-06-01",
        "work_hours": {"start": "09:00", "end": "17:00"},
        "feedback": "",
    }

    agent = PlannerAgent()
    result = agent.run(payload)
    assert "error" in result
