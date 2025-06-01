from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List
import re
import yaml

from .image_processor import extract_text_from_image

@dataclass
class CalendarEvent:
    """Single calendar event."""
    title: str
    description: str
    start: datetime
    duration: str
    participants: List[str]


def parse_calendar_from_text(text: str) -> List[CalendarEvent]:
    """Parse calendar events from OCR text."""
    events: List[CalendarEvent] = []
    pattern = re.compile(
        r"(?P<date>\d{4}-\d{2}-\d{2})\s+"  # date
        r"(?P<time>\d{1,2}:\d{2})\s+"       # time
        r"(?P<title>[^-\n]+)\s+-\s+"        # title
        r"(?P<duration>\d+[hm])\s+-\s+"     # duration
        r"(?P<participants>[^-\n]+)"         # participants
        r"(?:\s+-\s*(?P<description>.*))?",  # optional description
        re.IGNORECASE
    )
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if not m:
            continue
        start = datetime.fromisoformat(f"{m.group('date')} {m.group('time')}")
        participants = [p.strip() for p in m.group('participants').split(',') if p.strip()]
        event = CalendarEvent(
            title=m.group('title').strip(),
            description=(m.group('description') or '').strip(),
            start=start,
            duration=m.group('duration').strip(),
            participants=participants,
        )
        events.append(event)
    return events


def save_events_yaml(events: List[CalendarEvent], path: str = "meetings.yaml") -> None:
    """Save events to a YAML file sorted in descending order by start time."""
    events_sorted = sorted(events, key=lambda e: e.start, reverse=True)
    data = []
    for ev in events_sorted:
        item = asdict(ev)
        item["start"] = ev.start.isoformat()
        data.append(item)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False)


async def process_calendar_image(image_path: str, output_path: str = "meetings.yaml") -> str:
    """Extract calendar events from an image and save them as YAML."""
    text = await extract_text_from_image(image_path, "file")
    events = parse_calendar_from_text(text)
    save_events_yaml(events, output_path)
    return output_path

