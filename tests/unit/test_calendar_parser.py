from pathlib import Path
import yaml
import pytest

from src.processors.calendar import parse_calendar_from_text, save_events_yaml, save_events_simplified_yaml, parse_calendar_from_image, save_parsed_events_yaml


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


def test_save_events_simplified_yaml_with_colons(tmp_path: Path):
    """Test that simplified YAML format properly handles event titles with colons."""
    text = (
        "2024-06-10 13:00 Lifestage/DMT: Daily Scrum - 30m - Alice,Bob - Team sync\n"
        "2024-06-08 14:00 Project: Code Review - 1h - Carol - Review session\n"
    )
    events = parse_calendar_from_text(text)
    assert len(events) == 2
    assert events[0].title == "Lifestage/DMT: Daily Scrum"
    assert events[1].title == "Project: Code Review"
    
    yaml_path = tmp_path / "meetings_simplified.yaml"
    save_events_simplified_yaml(events, yaml_path)
    
    # Verify the YAML can be loaded back properly
    data = yaml.safe_load(yaml_path.read_text())
    assert len(data) == 2
    
    # Check structure matches expected format
    assert "date" in data[0]
    assert "time" in data[0]  
    assert "event" in data[0]
    
    # Verify events with colons are properly handled
    event_titles = [item["event"] for item in data]
    assert "Lifestage/DMT: Daily Scrum" in event_titles
    assert "Project: Code Review" in event_titles
    
    # Verify dates and times are in expected format
    assert data[0]["date"] == "2024-06-10"
    assert data[0]["time"] == "13:00"


def test_save_parsed_events_yaml(tmp_path: Path):
    """Test saving events that are already in the simplified format."""
    events = [
        {"date": "2025-06-01", "time": "13:00", "event": "Lifestage/DMT: Daily Scrum"},
        {"date": "2025-06-02", "time": "10:35", "event": "Huy / Joe 1x1"},
        {"date": "2025-06-03", "time": "16:00", "event": "Project: Meeting"}
    ]
    
    yaml_path = tmp_path / "parsed_meetings.yaml"
    save_parsed_events_yaml(events, yaml_path)
    
    # Verify the YAML can be loaded back properly
    data = yaml.safe_load(yaml_path.read_text())
    assert len(data) == 3
    
    # Check all events are preserved correctly
    assert data[0]["date"] == "2025-06-01"
    assert data[0]["time"] == "13:00"
    assert data[0]["event"] == "Lifestage/DMT: Daily Scrum"
    
    assert data[1]["date"] == "2025-06-02"
    assert data[1]["time"] == "10:35"
    assert data[1]["event"] == "Huy / Joe 1x1"
    
    # Verify colons in event titles are properly handled
    assert data[2]["event"] == "Project: Meeting"


@pytest.mark.asyncio
async def test_parse_calendar_from_image_format():
    """Test that parse_calendar_from_image returns the expected format (if API key is available)."""
    import os
    
    # Skip test if no API key is available
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("No OpenAI API key available for vision testing")
    
    # This test would require a real image file, so we'll just test the function structure
    try:
        # The function should exist and be callable
        from src.calendar_parser import parse_calendar_from_image
        assert callable(parse_calendar_from_image)
        
        # Test with a non-existent file to check error handling
        try:
            await parse_calendar_from_image("non_existent_file.png")
            assert False, "Should have raised an exception for non-existent file"
        except Exception as e:
            assert "Error reading image file" in str(e)
            
    except ImportError:
        pytest.fail("parse_calendar_from_image function should be importable")

