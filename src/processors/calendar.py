from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List
import re
import yaml
import json
import os
import base64
from openai import AsyncOpenAI

from .image import extract_text_from_image

# Initialize OpenAI client for vision processing
openai_client = None
openai_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
if openai_api_key:
    openai_client = AsyncOpenAI(api_key=openai_api_key)

@dataclass
class CalendarEvent:
    """Single calendar event."""
    title: str
    description: str
    start: datetime
    duration: str
    participants: List[str]


async def parse_calendar_from_image(image_path: str) -> List[dict]:
    """
    Parse calendar events directly from an image using OpenAI's vision model.
    Returns events in the simplified format: [{"date": "YYYY-MM-DD", "time": "HH:MM", "event": "title"}]
    """
    if not openai_client:
        raise Exception("OpenAI client not initialized. Please set LLM_API_KEY or OPENAI_API_KEY environment variable.")
    
    # Encode image to base64
    try:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        raise Exception(f"Error reading image file {image_path}: {e}")
    
    # System prompt for calendar parsing
    system_prompt = """You are an expert at parsing calendar events from calendar screenshots. 

Analyze the calendar image and extract all events with their correct dates and times. Pay close attention to:
1. The month/year header to determine the correct year and month
2. The day numbers to determine which date each event belongs to
3. The visual layout showing which events appear under which days
4. Meeting times (convert to 24-hour format)

Return a JSON array of events in this exact format:
[
  {
    "date": "YYYY-MM-DD",
    "time": "HH:MM", 
    "event": "Meeting Title"
  }
]

Guidelines:
- Use the correct date based on the calendar layout (don't put all events on the same day)
- Convert all times to 24-hour format (1pm → 13:00, 10:35am → 10:35)
- For time ranges like "1:30 – 2:30pm", use the start time (13:30)
- Include colons and special characters in event titles as they appear
- If multiple events occur at the same time on the same day, list them separately
- Only include actual scheduled events, not day headers or empty time slots"""

    user_prompt = "Please parse all calendar events from this calendar screenshot and return them in the specified JSON format."

    try:
        vision_model = os.getenv("VISION_LLM_MODEL", "gpt-4o")
        
        response = await openai_client.chat.completions.create(
            model=vision_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=4000
        )
        
        # Parse the JSON response
        result = json.loads(response.choices[0].message.content)
        
        # Handle different possible response formats
        if isinstance(result, list):
            events = result
        elif isinstance(result, dict) and "events" in result:
            events = result["events"]
        elif isinstance(result, dict) and "calendar_events" in result:
            events = result["calendar_events"]
        else:
            # Try to find any array in the response
            for value in result.values():
                if isinstance(value, list):
                    events = value
                    break
            else:
                events = []
        
        # Validate event format
        validated_events = []
        for event in events:
            if isinstance(event, dict) and "date" in event and "time" in event and "event" in event:
                validated_events.append({
                    "date": str(event["date"]),
                    "time": str(event["time"]),
                    "event": str(event["event"])
                })
        
        return validated_events
        
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse JSON response from vision model: {e}")
    except Exception as e:
        raise Exception(f"Error calling OpenAI vision API: {e}")


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


def save_events_simplified_yaml(events: List[CalendarEvent], path: str = "meetings.yaml") -> None:
    """Save events to a YAML file in simplified format with proper escaping for colons."""
    events_sorted = sorted(events, key=lambda e: e.start, reverse=True)
    data = []
    for ev in events_sorted:
        # Create simplified format matching current meetings.yaml structure
        item = {
            "date": ev.start.date().isoformat(),
            "time": ev.start.strftime("%H:%M"),
            "event": ev.title  # Will be properly escaped by yaml.safe_dump
        }
        data.append(item)
    
    with open(path, "w", encoding="utf-8") as fh:
        # Use safe_dump with proper configuration to handle colons in strings
        yaml.safe_dump(
            data, 
            fh, 
            sort_keys=False, 
            default_flow_style=False,
            allow_unicode=True,
            width=None,  # Prevent line wrapping
            indent=2
        )


def save_parsed_events_yaml(events: List[dict], path: str = "meetings.yaml") -> None:
    """Save parsed events (already in simplified format) to a YAML file."""
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(
            events, 
            fh, 
            sort_keys=False, 
            default_flow_style=False,
            allow_unicode=True,
            width=None,
            indent=2
        )


async def process_calendar_image(image_path: str, output_path: str = "meetings.yaml") -> str:
    """Extract calendar events from an image and save them as YAML using vision model."""
    try:
        # First try the new vision-based parsing
        events = await parse_calendar_from_image(image_path)
        if events:
            save_parsed_events_yaml(events, output_path)
            return output_path
    except Exception as e:
        print(f"Vision-based parsing failed: {e}")
        print("Falling back to text extraction method...")
    
    # Fallback to text extraction method
    text = await extract_text_from_image(image_path, "file")
    events = parse_calendar_from_text(text)
    save_events_yaml(events, output_path)
    return output_path

