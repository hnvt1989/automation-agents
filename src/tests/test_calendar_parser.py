import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.calendar_parser import parse_calendar_from_text, save_events_markdown


def test_parse_calendar_and_save(tmp_path: Path):
    text = (
        "2024-06-10 09:00 Standup - 30m - Alice,Bob - Daily sync\n"
        "2024-06-08 14:00 Demo - 1h - Carol - Product demo\n"
    )
    events = parse_calendar_from_text(text)
    assert len(events) == 2
    assert events[0].title == "Standup"
    md_path = tmp_path / "meetings.md"
    save_events_markdown(events, md_path)
    content = md_path.read_text()
    first_line = content.splitlines()[2]
    assert "2024-06-10" in first_line

