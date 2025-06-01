import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.calendar_parser import parse_calendar_from_text, save_events_yaml


def test_parse_calendar_and_save(tmp_path: Path):
    text = (
        "2024-06-10 09:00 Standup - 30m - Alice,Bob - Daily sync\n"
        "2024-06-08 14:00 Demo - 1h - Carol - Product demo\n"
    )
    events = parse_calendar_from_text(text)
    assert len(events) == 2
    assert events[0].title == "Standup"
    yaml_path = tmp_path / "meetings.yaml"
    save_events_yaml(events, yaml_path)
    data = yaml.safe_load(yaml_path.read_text())
    assert len(data) == 2
    assert data[0]["start"] > data[1]["start"]

