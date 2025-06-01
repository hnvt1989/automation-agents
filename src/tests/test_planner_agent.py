import os
import json
from tempfile import TemporaryDirectory
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from src.planner_agent import plan_day

SAMPLE_TASKS = """
- id: T1
  title: Write code
  priority: high
  estimate_hours: 2
  due_date: 2099-01-02
  status: pending
  tags: []
"""

SAMPLE_LOGS = """
2099-01-01:
  - task_id: T1
    description: Worked on feature
    actual_hours: 1.5
"""

SAMPLE_MEETS = """
- id: M1
  title: Sync
  start: 2099-01-02T10:00+00:00
  end: 2099-01-02T11:00+00:00
  participants: [dev]
"""

def write(path, content):
    with open(path, 'w') as f:
        f.write(content)

def test_plan_success():
    with TemporaryDirectory() as tmp:
        tasks = os.path.join(tmp, 'tasks.yaml')
        logs = os.path.join(tmp, 'logs.yaml')
        meets = os.path.join(tmp, 'meets.yaml')
        write(tasks, SAMPLE_TASKS)
        write(logs, SAMPLE_LOGS)
        write(meets, SAMPLE_MEETS)

        payload = {
            'paths': {'tasks': tasks, 'logs': logs, 'meets': meets},
            'target_date': '2099-01-02',
            'work_hours': {'start': '09:00', 'end': '17:00'}
        }
        result = plan_day(payload)
        assert 'yesterday_markdown' in result
        assert 'tomorrow_markdown' in result
        assert 'Plan for 2099-01-02' in result['tomorrow_markdown']


def test_create_templates_when_missing():
    with TemporaryDirectory() as tmp:
        tasks = os.path.join(tmp, 'tasks.yaml')
        logs = os.path.join(tmp, 'logs.yaml')
        meets = os.path.join(tmp, 'meets.yaml')
        payload = {
            'paths': {'tasks': tasks, 'logs': logs, 'meets': meets},
            'target_date': '2099-01-02',
            'work_hours': {'start': '09:00', 'end': '17:00'}
        }
        result = plan_day(payload)
        assert 'error' in result
        assert os.path.exists(tasks)
        assert os.path.exists(logs)
        assert os.path.exists(meets)
