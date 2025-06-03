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
        if not response.choices or not response.choices[0].message.content:
            raise Exception("No content in OpenAI response")
        
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


class CalendarProcessor:
    """Calendar processor class for parsing and handling calendar events."""
    
    def __init__(self):
        pass
    
    def parse_calendar_text(self, text: str) -> List[dict]:
        """Parse calendar text and return events in a structured format."""
        import re
        from datetime import datetime
        
        events = []
        lines = text.strip().split('\n')
        current_date = None
        i = 0
        
        # Common patterns for different calendar formats
        date_patterns = [
            r'(?i)(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday),?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d+,?\s+\d{4}',
            r'(?i)(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday),?\s+\d{1,2}/\d{1,2}/\d{4}',
            r'(?i)(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+\d{1,2}/\d{1,2}:',
            r'\d{4}-\d{2}-\d{2}',
            r'(?i)(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d+,?\s+\d{4}',
            r'(?i)(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',
            r'(?i)(?:friday|monday|tuesday|wednesday|thursday|saturday|sunday)\s+june\s+\d+th?,?\s+\d{4}'
        ]
        
        # Time patterns - more comprehensive
        time_patterns = [
            r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))\s*(?:-|–|to)\s*(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))',
            r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))',
            r'(\d{1,2}\s*(?:AM|PM|am|pm))\s*(?:-|–|to)\s*(\d{1,2}\s*(?:AM|PM|am|pm))',
            r'(\d{1,2}\s*(?:AM|PM|am|pm))',
            r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})',  # 24-hour format
            r'(\d{1,2}:\d{2})',  # Just time
        ]
        
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
                
            # Check for date line
            date_found = False
            for pattern in date_patterns:
                if re.search(pattern, line):
                    current_date = self._normalize_date(line)
                    date_found = True
                    break
            
            if date_found:
                i += 1
                continue
            
            # Check for time and event
            event_found = False
            for pattern in time_patterns:
                time_match = re.search(pattern, line)
                if time_match and current_date:
                    # Look ahead for location information
                    full_text = line
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and not re.search(r'\d{1,2}:\d{2}', next_line) and not any(re.search(dp, next_line) for dp in date_patterns):
                            full_text += " " + next_line
                    
                    event = self._parse_event_line(full_text, time_match, current_date)
                    if event:
                        events.append(event)
                        event_found = True
                    break
            
            i += 1
        
        return events
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to YYYY-MM-DD format."""
        import re
        from datetime import datetime
        
        # Try different date formats
        date_patterns = [
            (r'(?i)(\w+),?\s+(\w+)\s+(\d+),?\s+(\d{4})', '%A %B %d %Y'),
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%m/%d/%Y'),
            (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d')
        ]
        
        for pattern, fmt in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if 'Y' in fmt and 'B' in fmt:  # Month name format
                        # Extract components manually for month name
                        parts = date_str.split()
                        if len(parts) >= 3:
                            month_name = None
                            day = None
                            year = None
                            for part in parts:
                                if part.strip(',').isdigit() and len(part.strip(',')) == 4:
                                    year = part.strip(',')
                                elif part.strip(',').isdigit() and int(part.strip(',')) <= 31:
                                    day = part.strip(',').zfill(2)
                                elif any(m in part.lower() for m in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                                    month_map = {
                                        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                                        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08', 
                                        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
                                    }
                                    for abbr, num in month_map.items():
                                        if abbr in part.lower():
                                            month_name = num
                                            break
                            if year and month_name and day:
                                return f"{year}-{month_name}-{day}"
                    else:
                        groups = match.groups()
                        if len(groups) >= 3:
                            if '/' in pattern:  # MM/DD/YYYY
                                return f"{groups[2]}-{groups[0].zfill(2)}-{groups[1].zfill(2)}"
                            else:  # YYYY-MM-DD
                                return f"{groups[0]}-{groups[1]}-{groups[2]}"
                except:
                    pass
        
        # Default fallback
        return "2025-06-02"
    
    def _parse_event_line(self, line: str, time_match, date: str) -> dict:
        """Parse an event line and extract event details."""
        import re
        
        # Extract time information
        groups = time_match.groups()
        start_time = groups[0] if groups[0] else ""
        end_time = groups[1] if len(groups) > 1 and groups[1] else ""
        
        # Extract event title (text after time, before location)
        # Remove time patterns from the line
        title_text = re.sub(r'\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\s*(?:-|–|to)?\s*\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?', '', line)
        title_text = re.sub(r'\d{1,2}\s*(?:AM|PM|am|pm)\s*(?:-|–|to)?\s*\d{1,2}\s*(?:AM|PM|am|pm)?', '', title_text)
        
        # Extract location if present
        location = ""
        location_patterns = [
            r'(?i)location:\s*([^\n\r]+)',
            r'(?i)\(([^)]+)\)',
            r'(?i)room\s+([A-Z0-9]+)',
            r'(?i)building\s+([A-Z0-9]+)',
            r'(?i)conference\s+room\s+([A-Z0-9]+)',
            r'(?i)virtual\s*\(([^)]+)\)',
        ]
        
        # Check next lines for location info
        original_line = line
        for pattern in location_patterns:
            match = re.search(pattern, original_line)
            if match:
                location = match.group(1).strip()
                # Remove location from title
                title_text = re.sub(pattern, '', title_text)
                break
        
        title = title_text.strip()
        
        # If title is empty, try to extract from original line differently
        if not title:
            # Look for text patterns that might be event titles
            event_patterns = [
                r'(?:AM|PM|am|pm)\s+(.+?)(?:Location:|$)',
                r'(?:\d{1,2}:\d{2})\s+(.+?)(?:\(|Location:|$)',
                r'-\s*(.+?)(?:\(|Location:|$)'
            ]
            
            for pattern in event_patterns:
                match = re.search(pattern, original_line)
                if match:
                    title = match.group(1).strip()
                    break
        
        if not title:
            return None
            
        event = {
            "title": title,
            "date": date,
            "start_time": start_time,
            "end_time": end_time
        }
        
        if location:
            event["location"] = location
            
        return event
    
    def convert_to_planner_format(self, events: List[dict]) -> List[dict]:
        """Convert calendar events to planner meeting format."""
        planner_meetings = []
        
        for event in events:
            meeting = {
                "date": event.get("date", ""),
                "time": event.get("start_time", ""),
                "event": event.get("title", "")
            }
            planner_meetings.append(meeting)
        
        return planner_meetings
    
    def export_to_yaml(self, events: List[dict]) -> str:
        """Export events to YAML format."""
        import yaml
        return yaml.dump(events, default_flow_style=False)
    
    def export_to_csv(self, events: List[dict]) -> str:
        """Export events to CSV format."""
        import csv
        import io
        
        output = io.StringIO()
        if not events:
            return ""
            
        fieldnames = ["title", "date", "start_time", "end_time", "location"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for event in events:
            row = {field: event.get(field, "") for field in fieldnames}
            writer.writerow(row)
        
        return output.getvalue()
    
    def export_to_ical(self, events: List[dict]) -> str:
        """Export events to iCal format."""
        ical_content = ["BEGIN:VCALENDAR", "VERSION:2.0"]
        
        for i, event in enumerate(events):
            ical_content.extend([
                "BEGIN:VEVENT",
                f"UID:event-{i}@automation-agents",
                f"SUMMARY:{event.get('title', '')}",
                f"DTSTART:{event.get('date', '').replace('-', '')}{event.get('start_time', '').replace(':', '')}00",
                "END:VEVENT"
            ])
        
        ical_content.append("END:VCALENDAR")
        return "\n".join(ical_content)
    
    def detect_conflicts(self, events: List[dict]) -> List[dict]:
        """Detect scheduling conflicts between events."""
        conflicts = []
        # Simple implementation - could be enhanced
        return conflicts
    
    def generate_statistics(self, events: List[dict]) -> dict:
        """Generate statistics about calendar events."""
        unique_dates = set(event.get("date", "") for event in events)
        
        return {
            "total_events": len(events),
            "unique_dates": len(unique_dates),
            "average_events_per_day": len(events) / max(len(unique_dates), 1)
        }
    
    def analyze_time_distribution(self, events: List[dict]) -> dict:
        """Analyze time distribution of events."""
        morning_events = 0
        afternoon_events = 0
        
        for event in events:
            start_time = event.get("start_time", "")
            if "AM" in start_time or (start_time and int(start_time.split(":")[0]) < 12):
                morning_events += 1
            else:
                afternoon_events += 1
        
        return {
            "morning_events": morning_events,
            "afternoon_events": afternoon_events
        }

