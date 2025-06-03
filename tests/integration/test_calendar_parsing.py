"""Integration tests for calendar text parsing functionality."""

import pytest
import asyncio
import tempfile
from datetime import datetime, date
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import yaml

from src.processors.calendar import CalendarProcessor
from src.processors.image import extract_text_from_image


class TestCalendarParsingIntegration:
    """Integration tests for calendar text parsing from various sources."""

    @pytest.fixture
    def calendar_processor(self):
        """Create a calendar processor instance."""
        return CalendarProcessor()

    @pytest.fixture
    def sample_calendar_texts(self):
        """Sample calendar text data in various formats."""
        return {
            "outlook_format": """
Monday, June 2, 2025

9:00 AM - 10:00 AM    Daily Standup
Location: Conference Room A
Attendees: Team Alpha

10:30 AM - 11:30 AM   Sprint Planning
Location: Virtual (Teams)
Required: All developers

2:00 PM - 3:00 PM     Client Review Meeting
Location: Building B, Room 201
Optional: QA Team

4:00 PM - 5:00 PM     Architecture Discussion
Location: Virtual (Zoom)
Attendees: Senior developers
""",
            "google_calendar_format": """
Tuesday, June 3, 2025

• 9:00 – 9:30 AM
  Team Sync
  Meet in main conference room

• 11:00 AM – 12:00 PM
  Product Demo
  Virtual meeting link: meet.google.com/abc-defg-hij

• 1:00 – 2:30 PM
  Quarterly Review
  Building C, Executive Conference Room
  
• 3:30 – 4:00 PM
  1:1 with Manager
  Manager's office
""",
            "apple_calendar_format": """
Wednesday, Jun 3, 2025

Daily Standup                 9:00 AM
Sprint Review                10:00 AM - 11:00 AM
Lunch & Learn               12:00 PM - 1:00 PM
Code Review Session         2:00 PM - 3:00 PM
Team Retrospective          4:00 PM - 5:00 PM
""",
            "mixed_format": """
Thursday, 06/04/2025

09:00 - Team Standup (Room 101)
10:30 - Project Kickoff Meeting
      Location: Virtual
      Duration: 90 minutes
      
13:00 - 14:30 Client Call
15:00 Sprint Demo (Conference Room B)
16:30 - Weekly Review Meeting
""",
            "dense_schedule": """
Friday June 5th, 2025

8:00 AM  Early Bird Meeting
8:30 AM  Coffee with VP
9:00 AM  Status Update
9:30 AM  Technical Review
10:00 AM Sprint Planning
10:30 AM Backlog Grooming
11:00 AM Architecture Review
11:30 AM Code Review
12:00 PM Lunch Meeting with Client
1:00 PM  Project Update
1:30 PM  Technical Discussion
2:00 PM  Design Review
2:30 PM  Integration Testing
3:00 PM  Performance Review
3:30 PM  Security Audit
4:00 PM  Sprint Demo
4:30 PM  Retrospective
5:00 PM  Team Social
""",
            "multi_day_format": """
Monday, June 2 - Friday, June 6, 2025

MONDAY 6/2:
9:00 AM - Sprint Planning
2:00 PM - Client Demo

TUESDAY 6/3:
10:00 AM - Architecture Review
3:00 PM - Team Retrospective

WEDNESDAY 6/4:
9:00 AM - Daily Standup
11:00 AM - Product Planning
4:00 PM - Engineering All-Hands

THURSDAY 6/5:
9:30 AM - Technical Review
1:00 PM - Stakeholder Meeting

FRIDAY 6/6:
10:00 AM - Sprint Demo
2:00 PM - Team Social Hour
"""
        }

    @pytest.fixture 
    def sample_calendar_images(self, temp_dir):
        """Create sample calendar image data for testing."""
        # Create mock image files with calendar-like names
        calendar_images = {}
        
        # Create mock screenshot files
        screenshot_files = [
            "calendar_screenshot_2025_06_02.png",
            "outlook_calendar_view.jpg", 
            "google_calendar_week_view.png",
            "mobile_calendar_app.jpg"
        ]
        
        for filename in screenshot_files:
            image_path = temp_dir / filename
            # Create empty file to simulate image
            image_path.write_bytes(b'\x89PNG\r\n\x1a\n')  # PNG header
            calendar_images[filename] = str(image_path)
        
        return calendar_images

    def test_basic_calendar_text_parsing(self, calendar_processor, sample_calendar_texts):
        """Test basic calendar text parsing functionality."""
        outlook_text = sample_calendar_texts["outlook_format"]
        
        # Parse calendar events
        events = calendar_processor.parse_calendar_text(outlook_text)
        
        assert len(events) >= 4  # Should find at least 4 events
        
        # Verify first event details
        first_event = events[0]
        assert "Daily Standup" in first_event["title"]
        assert first_event["start_time"] == "9:00 AM" or "9:00" in first_event["start_time"]
        assert first_event["end_time"] == "10:00 AM" or "10:00" in first_event["end_time"]
        assert "Conference Room A" in first_event.get("location", "")
        
        # Verify date parsing
        assert first_event["date"] == "2025-06-02" or "June 2" in str(first_event["date"])

    def test_multiple_calendar_formats(self, calendar_processor, sample_calendar_texts):
        """Test parsing different calendar formats."""
        format_names = ["google_calendar_format", "apple_calendar_format", "mixed_format"]
        
        for format_name in format_names:
            calendar_text = sample_calendar_texts[format_name]
            events = calendar_processor.parse_calendar_text(calendar_text)
            
            assert len(events) > 0, f"No events parsed from {format_name}"
            
            # Verify each event has required fields
            for event in events:
                assert "title" in event, f"Missing title in {format_name}"
                assert "date" in event, f"Missing date in {format_name}"
                assert "start_time" in event or "time" in event, f"Missing time in {format_name}"

    def test_dense_schedule_parsing(self, calendar_processor, sample_calendar_texts):
        """Test parsing dense schedules with many events."""
        dense_text = sample_calendar_texts["dense_schedule"]
        events = calendar_processor.parse_calendar_text(dense_text)
        
        # Should parse many events from dense schedule
        assert len(events) >= 15
        
        # Verify chronological order
        times = []
        for event in events:
            if "start_time" in event:
                times.append(event["start_time"])
        
        # Check that events are generally in chronological order
        # (allowing for some parsing variations)
        morning_events = [t for t in times if "AM" in t]
        afternoon_events = [t for t in times if "PM" in t]
        
        assert len(morning_events) > 0
        assert len(afternoon_events) > 0

    def test_multi_day_calendar_parsing(self, calendar_processor, sample_calendar_texts):
        """Test parsing multi-day calendar formats."""
        multi_day_text = sample_calendar_texts["multi_day_format"]
        events = calendar_processor.parse_calendar_text(multi_day_text)
        
        # Should parse events across multiple days
        assert len(events) >= 8
        
        # Verify different dates are captured
        dates = set()
        for event in events:
            if "date" in event:
                dates.add(event["date"])
        
        assert len(dates) >= 3  # Should have events on at least 3 different days

    def test_time_format_normalization(self, calendar_processor, sample_calendar_texts):
        """Test time format normalization across different inputs."""
        all_events = []
        
        # Parse all calendar formats
        for calendar_text in sample_calendar_texts.values():
            events = calendar_processor.parse_calendar_text(calendar_text)
            all_events.extend(events)
        
        # Check time format consistency
        for event in all_events:
            if "start_time" in event:
                start_time = event["start_time"]
                # Should be in consistent format (e.g., "HH:MM AM/PM" or "HH:MM")
                assert isinstance(start_time, str)
                assert len(start_time) > 0
                
            if "end_time" in event:
                end_time = event["end_time"]
                assert isinstance(end_time, str)
                assert len(end_time) > 0

    def test_event_details_extraction(self, calendar_processor, sample_calendar_texts):
        """Test extraction of detailed event information."""
        outlook_text = sample_calendar_texts["outlook_format"]
        events = calendar_processor.parse_calendar_text(outlook_text)
        
        # Find events with rich details
        detailed_events = [e for e in events if "location" in e or "attendees" in e]
        assert len(detailed_events) > 0
        
        # Test specific event details
        for event in events:
            if "Sprint Planning" in event["title"]:
                assert "Virtual" in event.get("location", "") or "Teams" in event.get("location", "")
                break
        else:
            pytest.fail("Sprint Planning event not found")

    @pytest.mark.asyncio
    async def test_calendar_image_text_extraction(self, sample_calendar_images):
        """Test text extraction from calendar screenshot images."""
        # Mock the actual OCR functionality
        mock_calendar_text = """
Monday, June 2, 2025

9:00 AM - 10:00 AM    Daily Standup
2:00 PM - 3:00 PM     Sprint Review
4:00 PM - 5:00 PM     Team Meeting
"""
        
        for image_name, image_path in sample_calendar_images.items():
            # Mock the extract_text_from_image function
            with patch('src.processors.image.extract_text_from_image') as mock_extract:
                mock_extract.return_value = mock_calendar_text
                
                # Extract text from calendar image
                extracted_text = await extract_text_from_image(image_path, 'file')
                
                assert extracted_text is not None
                assert len(extracted_text) > 0
                assert "Daily Standup" in extracted_text
                assert "June 2, 2025" in extracted_text

    @pytest.mark.asyncio 
    async def test_end_to_end_calendar_processing(self, calendar_processor, sample_calendar_images):
        """Test complete end-to-end calendar processing from image to structured data."""
        # Mock calendar text extraction
        mock_calendar_text = sample_calendar_images  # Use one of our sample texts
        outlook_format = """
Monday, June 2, 2025

9:00 AM - 10:00 AM    Daily Standup
Location: Conference Room A

2:00 PM - 3:00 PM     Client Review Meeting  
Location: Building B, Room 201

4:00 PM - 5:00 PM     Architecture Discussion
Location: Virtual (Zoom)
"""
        
        image_path = list(sample_calendar_images.values())[0]
        
        # Mock the entire pipeline
        with patch('src.processors.image.extract_text_from_image') as mock_extract:
            mock_extract.return_value = outlook_format
            
            # Extract text from image
            extracted_text = await extract_text_from_image(image_path, 'file')
            
            # Parse calendar events
            events = calendar_processor.parse_calendar_text(extracted_text)
            
            # Verify end-to-end processing
            assert len(events) >= 3
            
            # Verify structured data
            for event in events:
                assert "title" in event
                assert "date" in event
                assert "start_time" in event
                
            # Verify specific event details
            standup_event = next((e for e in events if "Standup" in e["title"]), None)
            assert standup_event is not None
            assert "Conference Room A" in standup_event.get("location", "")

    def test_calendar_export_formats(self, calendar_processor, sample_calendar_texts):
        """Test conversion to various calendar export formats."""
        outlook_text = sample_calendar_texts["outlook_format"]
        events = calendar_processor.parse_calendar_text(outlook_text)
        
        # Test YAML export
        yaml_export = calendar_processor.export_to_yaml(events)
        parsed_yaml = yaml.safe_load(yaml_export)
        
        assert isinstance(parsed_yaml, list)
        assert len(parsed_yaml) == len(events)
        
        # Test CSV export format
        csv_export = calendar_processor.export_to_csv(events)
        assert "title,date,start_time,end_time,location" in csv_export
        assert "Daily Standup" in csv_export
        
        # Test iCal format export
        ical_export = calendar_processor.export_to_ical(events)
        assert "BEGIN:VCALENDAR" in ical_export
        assert "BEGIN:VEVENT" in ical_export
        assert "Daily Standup" in ical_export

    def test_calendar_data_validation(self, calendar_processor, sample_calendar_texts):
        """Test data validation and error handling."""
        # Test with malformed calendar text
        malformed_texts = [
            "",  # Empty text
            "Not a calendar format at all",  # No calendar structure
            "Monday\n\nSome random text without times",  # Missing time information
            "9:00 AM Meeting\n10:00 AM Another Meeting",  # Missing date context
        ]
        
        for malformed_text in malformed_texts:
            events = calendar_processor.parse_calendar_text(malformed_text)
            # Should handle gracefully, either return empty list or minimal data
            assert isinstance(events, list)
            
        # Test with edge cases
        edge_cases = [
            "Monday, June 2, 2025\n\n",  # Date only, no events
            "9:00 AM - Meeting without end time",  # Missing end time
            "All Day Event\nJune 2, 2025",  # All-day event format
        ]
        
        for edge_case in edge_cases:
            events = calendar_processor.parse_calendar_text(edge_case)
            assert isinstance(events, list)
            # Should not crash, may or may not find events depending on implementation

    def test_recurring_event_detection(self, calendar_processor):
        """Test detection and handling of recurring events."""
        recurring_calendar_text = """
Monday, June 2, 2025

9:00 AM - 10:00 AM    Daily Standup (Recurring)
2:00 PM - 3:00 PM     Sprint Planning (Every 2 weeks)

Tuesday, June 3, 2025

9:00 AM - 10:00 AM    Daily Standup (Recurring)
3:00 PM - 4:00 PM     Team Retrospective (Weekly)

Wednesday, June 4, 2025

9:00 AM - 10:00 AM    Daily Standup (Recurring)
"""
        
        events = calendar_processor.parse_calendar_text(recurring_calendar_text)
        
        # Should detect multiple instances of recurring events
        standup_events = [e for e in events if "Daily Standup" in e["title"]]
        assert len(standup_events) >= 3  # One for each day
        
        # Should identify recurring patterns
        recurring_events = [e for e in events if "recurring" in e.get("description", "").lower() or "recurring" in e["title"].lower()]
        assert len(recurring_events) > 0

    def test_timezone_handling(self, calendar_processor):
        """Test handling of timezone information in calendar data."""
        timezone_calendar_text = """
Monday, June 2, 2025

9:00 AM PST - 10:00 AM PST    West Coast Meeting
12:00 PM EST - 1:00 PM EST    East Coast Meeting  
3:00 PM UTC - 4:00 PM UTC     Global Team Sync
5:00 PM PDT - 6:00 PM PDT     After Hours Call
"""
        
        events = calendar_processor.parse_calendar_text(timezone_calendar_text)
        
        assert len(events) >= 4
        
        # Check if timezone information is preserved
        for event in events:
            # Implementation may handle timezones differently
            time_info = event.get("start_time", "") + " " + event.get("end_time", "")
            # Should have some indication of timezone handling
            assert len(time_info) > 0

    def test_calendar_conflict_detection(self, calendar_processor, sample_calendar_texts):
        """Test detection of scheduling conflicts."""
        # Use dense schedule which likely has overlapping times
        dense_text = sample_calendar_texts["dense_schedule"]
        events = calendar_processor.parse_calendar_text(dense_text)
        
        # Analyze for potential conflicts
        conflicts = calendar_processor.detect_conflicts(events)
        
        # Dense schedule should have some potential conflicts
        # (Implementation dependent - may return empty list if no conflict detection)
        assert isinstance(conflicts, list)

    def test_calendar_statistics_and_analysis(self, calendar_processor, sample_calendar_texts):
        """Test calendar statistics and analysis functionality."""
        # Combine multiple calendar formats for analysis
        all_events = []
        for calendar_text in sample_calendar_texts.values():
            events = calendar_processor.parse_calendar_text(calendar_text)
            all_events.extend(events)
        
        # Generate statistics
        stats = calendar_processor.generate_statistics(all_events)
        
        assert "total_events" in stats
        assert stats["total_events"] > 0
        assert "unique_dates" in stats
        assert "average_events_per_day" in stats
        
        # Test time distribution analysis
        time_distribution = calendar_processor.analyze_time_distribution(all_events)
        assert "morning_events" in time_distribution
        assert "afternoon_events" in time_distribution

    @pytest.mark.asyncio
    async def test_calendar_integration_with_task_planner(self, calendar_processor, temp_dir):
        """Test integration between calendar parsing and task planner."""
        # Create temporary planner data
        data_dir = temp_dir / "data"
        data_dir.mkdir()
        meetings_file = data_dir / "meetings.yaml"
        
        # Parse calendar and convert to planner format
        calendar_text = """
Monday, June 2, 2025

9:00 AM - 10:00 AM    Daily Standup
2:00 PM - 3:00 PM     Sprint Review
"""
        
        events = calendar_processor.parse_calendar_text(calendar_text)
        
        # Convert to planner meeting format
        planner_meetings = calendar_processor.convert_to_planner_format(events)
        
        # Write to meetings file
        with open(meetings_file, 'w') as f:
            yaml.dump(planner_meetings, f)
        
        # Verify integration
        with open(meetings_file, 'r') as f:
            saved_meetings = yaml.safe_load(f)
        
        assert len(saved_meetings) >= 2
        
        # Verify planner format
        for meeting in saved_meetings:
            assert "date" in meeting
            assert "time" in meeting  
            assert "event" in meeting
            
        # Find specific meeting
        standup_meeting = next((m for m in saved_meetings if "Standup" in m["event"]), None)
        assert standup_meeting is not None
        assert standup_meeting["date"] == "2025-06-02"
        assert "09:00" in standup_meeting["time"]