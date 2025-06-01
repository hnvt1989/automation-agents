import sys
from pathlib import Path

import yaml

sys.path.append(str(Path(__file__).resolve().parents[1]))
from planner_agent import PlannerAgent


def make_payload(tmp_path, target_date="2025-06-02"):
    paths = {
        "tasks": str(tmp_path / "tasks.yaml"),
        "logs": str(tmp_path / "daily_logs.yaml"),
        "meets": str(tmp_path / "meetings.yaml"),
    }
    return {
        "paths": paths,
        "target_date": target_date,
        "work_hours": {"start": "09:00", "end": "17:00"},
        "feedback": "",
    }


def test_templates_created(tmp_path):
    agent = PlannerAgent()
    payload = make_payload(tmp_path)
    result = agent.generate_plan(payload)
    assert "yesterday_markdown" in result
    assert Path(payload["paths"]["tasks"]).exists()
    assert Path(payload["paths"]["logs"]).exists()
    assert Path(payload["paths"]["meets"]).exists()


def test_malformed_yaml_returns_error(tmp_path):
    tasks = tmp_path / "tasks.yaml"
    tasks.write_text(":- invalid")
    (tmp_path / "daily_logs.yaml").write_text("{}")
    (tmp_path / "meetings.yaml").write_text("[]")
    agent = PlannerAgent()
    payload = make_payload(tmp_path)
    result = agent.generate_plan(payload)
    assert "error" in result


def test_plan_generation(tmp_path):
    tasks = [
        {
            "id": "T1",
            "title": "Important",
            "priority": "high",
            "estimate_hours": 2,
            "due_date": "2025-06-05",
            "status": "pending",
            "tags": [],
        }
    ]
    logs = {
        "2025-06-01": [
            {"task_id": "T0", "description": "Worked on something", "actual_hours": 1.0}
        ]
    }
    meets = [
        {
            "id": "M1",
            "title": "Sync",
            "start": "2025-06-02T11:00+00:00",
            "end": "2025-06-02T12:00+00:00",
            "participants": ["a"],
        }
    ]
    payload = make_payload(tmp_path)
    Path(payload["paths"]["tasks"]).write_text(yaml.safe_dump(tasks))
    Path(payload["paths"]["logs"]).write_text(yaml.safe_dump(logs))
    Path(payload["paths"]["meets"]).write_text(yaml.safe_dump(meets))
    agent = PlannerAgent()
    result = agent.generate_plan(payload)
    assert "Plan for 2025-06-02" in result["tomorrow_markdown"]
