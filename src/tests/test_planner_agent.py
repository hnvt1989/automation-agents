import os
import sys
import pathlib
import yaml

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from planner_agent import PlannerAgent


def write_yaml(path: str, data: object):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)


def sample_files(tmpdir: str):
    tasks = [
        {
            "id": "T1",
            "title": "Task One",
            "priority": "high",
            "estimate_hours": 2,
            "due_date": "2030-01-03",
            "status": "pending",
            "tags": ["dev"],
        },
        {
            "id": "T2",
            "title": "Task Two",
            "priority": "low",
            "estimate_hours": 1,
            "due_date": "2030-01-04",
            "status": "done",
            "tags": [],
        },
    ]
    logs = {
        "2030-01-01": [
            {"task_id": "T1", "description": "Completed part of task one", "actual_hours": 1.5}
        ]
    }
    meetings = [
        {
            "id": "M1",
            "title": "Team sync",
            "start": "2030-01-02T13:00+00:00",
            "end": "2030-01-02T14:00+00:00",
            "participants": ["Alice"],
        }
    ]
    write_yaml(os.path.join(tmpdir, "tasks.yaml"), tasks)
    write_yaml(os.path.join(tmpdir, "daily_logs.yaml"), logs)
    write_yaml(os.path.join(tmpdir, "meetings.yaml"), meetings)


def test_planner_success(tmp_path):
    sample_files(tmp_path)
    payload = {
        "paths": {
            "tasks": str(tmp_path / "tasks.yaml"),
            "logs": str(tmp_path / "daily_logs.yaml"),
            "meets": str(tmp_path / "meetings.yaml"),
        },
        "target_date": "2030-01-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
    }
    agent = PlannerAgent()
    result = agent.plan(payload)
    assert "yesterday_markdown" in result
    assert "tomorrow_markdown" in result
    assert "Task One" in result["tomorrow_markdown"]


def test_planner_invalid_yaml(tmp_path):
    (tmp_path / "tasks.yaml").write_text("- id: T1\n  title")
    (tmp_path / "daily_logs.yaml").write_text("{}")
    (tmp_path / "meetings.yaml").write_text("[]")
    payload = {
        "paths": {
            "tasks": str(tmp_path / "tasks.yaml"),
            "logs": str(tmp_path / "daily_logs.yaml"),
            "meets": str(tmp_path / "meetings.yaml"),
        },
        "target_date": "2030-01-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
    }
    agent = PlannerAgent()
    result = agent.plan(payload)
    assert "error" in result
