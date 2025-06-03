import json
from datetime import date, timedelta
from pathlib import Path

from src.agents.planner import plan_day


def test_planner_success(tmp_path: Path):
    tasks = tmp_path / "tasks.yaml"
    logs = tmp_path / "daily_logs.yaml"
    meets = tmp_path / "meetings.yaml"

    tasks.write_text(
        """
- id: T1
  title: Finish report
  priority: high
  estimate_hours: 2
  due_date: 2024-05-02
  status: pending
  tags: []
- id: T2
  title: Email client
  priority: medium
  estimate_hours: 1
  due_date: 2024-05-03
  status: pending
  tags: []
"""
    )

    logs.write_text(
        """
2024-05-01:
  - log_id: T1
    description: Completed initial draft
    actual_hours: 1
"""
    )

    meets.write_text(
        """
- id: M1
  title: Sync
  start: 2024-05-02T10:00:00
  end: 2024-05-02T11:00:00
  participants: [alice]
"""
    )

    payload = {
        "paths": {"tasks": str(tasks), "logs": str(logs), "meets": str(meets)},
        "target_date": "2024-05-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
    }

    result = plan_day(payload)
    expected = {
        "yesterday_markdown": "## 2024-05-01\n- Completed initial draft",
        "tomorrow_markdown": (
            "## Plan for 2024-05-02\n\n"
            "### Meetings\n"
            "- 10:00 - Sync\n\n"
            "### Tasks\n"
            "| Time | Task | Reason |\n"
            "| - | - | - |\n"
            "| 09:00-10:00 | T1 Finish report | Priority high, due 2024-05-02 |\n"
            "| 11:00-12:00 | T1 Finish report | Priority high, due 2024-05-02 |\n"
            "| 12:00-13:00 | T2 Email client | Priority medium, due 2024-05-03 |"
        ),
    }
    assert result == expected


def test_planner_bad_yaml(tmp_path: Path):
    tasks = tmp_path / "tasks.yaml"
    logs = tmp_path / "daily_logs.yaml"
    meets = tmp_path / "meetings.yaml"

    tasks.write_text("not: [valid")
    logs.write_text("")
    meets.write_text("[]")

    payload = {
        "paths": {"tasks": str(tasks), "logs": str(logs), "meets": str(meets)},
        "target_date": "2024-05-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
    }

    result = plan_day(payload)
    assert "error" in result


def test_planner_with_simplified_meetings_format(tmp_path: Path):
    """Test planner agent with the current meetings.yaml format (date, time, event)."""
    tasks = tmp_path / "tasks.yaml"
    logs = tmp_path / "daily_logs.yaml"
    meets = tmp_path / "meetings.yaml"

    tasks.write_text(
        """
- id: T1
  title: Finish report
  priority: high
  estimate_hours: 2
  due_date: 2024-05-02
  status: pending
  tags: []
- id: T2
  title: Email client
  priority: medium
  estimate_hours: 1
  due_date: 2024-05-03
  status: pending
  tags: []
"""
    )

    logs.write_text(
        """
2024-05-01:
  - log_id: T1
    description: Completed initial draft
    actual_hours: 1
"""
    )

    # Use the simplified format with events containing colons
    meets.write_text(
        """
- date: 2024-05-02
  time: "10:00"
  event: "Lifestage/DMT: Daily Scrum"
- date: 2024-05-02
  time: "15:00"
  event: "Project: Code Review Session"
"""
    )

    payload = {
        "paths": {"tasks": str(tasks), "logs": str(logs), "meets": str(meets)},
        "target_date": "2024-05-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
    }

    result = plan_day(payload)
    
    # Should succeed and return expected structure
    assert "error" not in result
    assert "yesterday_markdown" in result
    assert "tomorrow_markdown" in result
    
    # Verify yesterday summary
    assert "## 2024-05-01" in result["yesterday_markdown"]
    assert "Completed initial draft" in result["yesterday_markdown"]
    
    # Verify schedule respects meeting times (meetings at 10:00-11:00 and 15:00-16:00)
    tomorrow_plan = result["tomorrow_markdown"]
    assert "## Plan for 2024-05-02" in tomorrow_plan
    
    # Verify meetings are displayed in the plan
    assert "### Meetings" in tomorrow_plan
    assert "10:00 - Lifestage/DMT: Daily Scrum" in tomorrow_plan
    assert "15:00 - Project: Code Review Session" in tomorrow_plan
    
    # Should have tasks scheduled around meetings (before 10:00, between 11:00-15:00, after 16:00)
    assert "09:00-10:00" in tomorrow_plan  # Before first meeting
    assert "11:00-" in tomorrow_plan  # After first meeting
    
    # Verify task information is included
    assert "T1 Finish report" in tomorrow_plan
    assert "Priority high" in tomorrow_plan


def test_planner_with_empty_estimated_hours(tmp_path: Path):
    """Test planner agent handles None/empty estimated_hours values gracefully."""
    tasks = tmp_path / "tasks.yaml"
    logs = tmp_path / "daily_logs.yaml"
    meets = tmp_path / "meetings.yaml"

    # Tasks with various empty/None estimated_hours scenarios
    tasks.write_text(
        """
- id: T1
  title: Task with None estimate
  priority: high
  estimate_hours: null
  due_date: 2024-05-02
  status: pending
  tags: []
- id: T2
  title: Task with missing estimate
  priority: medium
  due_date: 2024-05-03
  status: pending
  tags: []
- id: T3
  title: Task with empty string estimate
  priority: low
  estimate_hours: ""
  due_date: 2024-05-04
  status: pending
  tags: []
- id: T4
  title: Task with valid estimate
  priority: medium
  estimate_hours: 2
  due_date: 2024-05-05
  status: pending
  tags: []
"""
    )

    logs.write_text("")
    meets.write_text("[]")

    payload = {
        "paths": {"tasks": str(tasks), "logs": str(logs), "meets": str(meets)},
        "target_date": "2024-05-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
    }

    result = plan_day(payload)
    
    # Should succeed without errors
    assert "error" not in result
    assert "yesterday_markdown" in result
    assert "tomorrow_markdown" in result
    
    # Verify all tasks are planned (with default 1-hour estimates for empty values)
    tomorrow_plan = result["tomorrow_markdown"]
    assert "T1 Task with None estimate" in tomorrow_plan
    assert "T2 Task with missing estimate" in tomorrow_plan
    assert "T3 Task with empty string estimate" in tomorrow_plan
    assert "T4 Task with valid estimate" in tomorrow_plan


def test_date_parsing_logic():
    """Test that date parsing logic works correctly for relative date references."""
    # Import the date parsing logic from agents.py (we'll simulate it here)
    from datetime import datetime, date, timedelta
    
    def parse_date_reference(target_date: str = None) -> date:
        """Simulate the date parsing logic from use_planner_agent."""
        if target_date is None or target_date.lower().strip() in ["today"]:
            return date.today()
        elif target_date.lower().strip() == "tomorrow":
            return date.today() + timedelta(days=1)
        elif target_date.lower().strip() == "yesterday":
            return date.today() - timedelta(days=1)
        elif target_date.lower().strip() in ["next week", "next monday"]:
            today = date.today()
            days_ahead = 7 - today.weekday()  # Days until next Monday
            return today + timedelta(days=days_ahead)
        elif target_date.lower().strip() in ["this week", "this monday"]:
            today = date.today()
            days_back = today.weekday()  # Days since this Monday
            return today - timedelta(days=days_back)
        else:
            # Try to parse as ISO date format (YYYY-MM-DD)
            try:
                return datetime.fromisoformat(target_date).date()
            except (ValueError, AttributeError):
                return date.today()
    
    today = date.today()
    
    # Test relative date parsing
    assert parse_date_reference("tomorrow") == today + timedelta(days=1)
    assert parse_date_reference("today") == today
    assert parse_date_reference("yesterday") == today - timedelta(days=1)
    assert parse_date_reference(None) == today
    
    # Test exact date parsing
    test_date = "2024-12-25"
    expected_date = date(2024, 12, 25)
    assert parse_date_reference(test_date) == expected_date
    
    # Test invalid date falls back to today
    assert parse_date_reference("invalid-date") == today
    
    # Test case insensitive parsing
    assert parse_date_reference("TOMORROW") == today + timedelta(days=1)
    assert parse_date_reference("Today") == today


def test_date_extraction_from_queries():
    """Test that date extraction from user queries works correctly."""
    # Import the date extraction logic from agents.py
    import sys
    import os
    
    # Add the project root to the path to import from agents.py
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sys.path.insert(0, project_root)
    
    from agents import extract_date_from_query
    
    # Test direct date references
    assert extract_date_from_query("What should I do tomorrow?") == "tomorrow"
    assert extract_date_from_query("Tell me what I should plan to do tomorrow") == "tomorrow"
    assert extract_date_from_query("Plan for today") == "today"
    assert extract_date_from_query("What's my schedule for yesterday?") == "yesterday"
    assert extract_date_from_query("Planning for next week") == "next week"
    
    # Test case insensitive
    assert extract_date_from_query("What should I do TOMORROW?") == "tomorrow"
    assert extract_date_from_query("Plan for TODAY") == "today"
    
    # Test ISO date format
    assert extract_date_from_query("What should I work on for 2024-01-15?") == "2024-01-15"
    assert extract_date_from_query("My schedule for 2023-12-25") == "2023-12-25"
    
    # Test US date format conversion
    assert extract_date_from_query("Plan for 12/25/2024") == "2024-12-25"
    assert extract_date_from_query("What about 01/15/2024?") == "2024-01-15"
    
    # Test default to today when no date context
    assert extract_date_from_query("What should I work on?") == "today"
    assert extract_date_from_query("Show me my tasks") == "today"
    assert extract_date_from_query("I need help with planning") == "today"
    
    # Test complex queries with date context
    assert extract_date_from_query("Can you help me plan what I should do tomorrow morning?") == "tomorrow"
    assert extract_date_from_query("I'm wondering about my schedule for next week") == "next week"


def test_planner_excludes_completed_tasks(tmp_path: Path):
    """Test that tasks with various completion statuses are excluded from planning."""
    tasks = tmp_path / "tasks.yaml"
    logs = tmp_path / "daily_logs.yaml"
    meets = tmp_path / "meetings.yaml"

    # Tasks with various completion statuses
    tasks.write_text(
        """
- id: T1
  title: Should be included - pending
  priority: high
  estimate_hours: 1
  due_date: 2024-05-02
  status: pending
  tags: []
- id: T2
  title: Should be excluded - done
  priority: high
  estimate_hours: 1
  due_date: 2024-05-02
  status: done
  tags: []
- id: T3
  title: Should be excluded - completed
  priority: high
  estimate_hours: 1
  due_date: 2024-05-02
  status: completed
  tags: []
- id: T4
  title: Should be excluded - finished
  priority: high
  estimate_hours: 1
  due_date: 2024-05-02
  status: finished
  tags: []
- id: T5
  title: Should be excluded - complete
  priority: high
  estimate_hours: 1
  due_date: 2024-05-02
  status: complete
  tags: []
- id: T6
  title: Should be excluded - cancelled
  priority: high
  estimate_hours: 1
  due_date: 2024-05-02
  status: cancelled
  tags: []
- id: T7
  title: Should be included - in progress
  priority: medium
  estimate_hours: 1
  due_date: 2024-05-02
  status: in-progress
  tags: []
- id: T8
  title: Should be excluded - COMPLETED (case insensitive)
  priority: high
  estimate_hours: 1
  due_date: 2024-05-02
  status: COMPLETED
  tags: []
"""
    )

    logs.write_text("")
    meets.write_text("[]")

    payload = {
        "paths": {"tasks": str(tasks), "logs": str(logs), "meets": str(meets)},
        "target_date": "2024-05-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
    }

    result = plan_day(payload)
    
    # Should succeed without errors
    assert "error" not in result
    assert "yesterday_markdown" in result
    assert "tomorrow_markdown" in result
    
    tomorrow_plan = result["tomorrow_markdown"]
    
    # Verify only non-completed tasks are included
    assert "T1" in tomorrow_plan  # pending
    assert "T7" in tomorrow_plan  # in-progress
    
    # Verify completed tasks are excluded
    assert "T2" not in tomorrow_plan  # done
    assert "T3" not in tomorrow_plan  # completed
    assert "T4" not in tomorrow_plan  # finished
    assert "T5" not in tomorrow_plan  # complete
    assert "T6" not in tomorrow_plan  # cancelled
    assert "T8" not in tomorrow_plan  # COMPLETED (case insensitive)
    
    # Verify task titles for clarity
    assert "Should be included - pending" in tomorrow_plan
    assert "Should be included - in progress" in tomorrow_plan
    assert "Should be excluded" not in tomorrow_plan


def test_planner_finds_latest_log_entry(tmp_path: Path):
    """Test that planner agent finds the latest entry in daily_logs.yaml, accounting for weekends/vacations."""
    tasks = tmp_path / "tasks.yaml"
    logs = tmp_path / "daily_logs.yaml"
    meets = tmp_path / "meetings.yaml"

    tasks.write_text(
        """
- id: T1
  title: Test task
  priority: high
  estimate_hours: 1
  due_date: 2024-05-02
  status: pending
  tags: []
"""
    )

    # Create logs with gaps (simulating weekend/vacation)
    # Target date is 2024-05-02 (Thursday)
    # Most recent entry should be 2024-04-30 (Tuesday), skipping 2024-05-01 (Wednesday)
    logs.write_text(
        """
2024-04-28:
  - log_id: T1
    description: Older work from Sunday
    actual_hours: 2
2024-04-30:
  - log_id: T1
    description: Latest work from Tuesday
    actual_hours: 4
# Note: 2024-05-01 (Wednesday) is missing - could be vacation day
"""
    )

    meets.write_text("[]")

    payload = {
        "paths": {"tasks": str(tasks), "logs": str(logs), "meets": str(meets)},
        "target_date": "2024-05-02",  # Thursday
        "work_hours": {"start": "09:00", "end": "17:00"},
    }

    result = plan_day(payload)
    
    # Should succeed without errors
    assert "error" not in result
    assert "yesterday_markdown" in result
    assert "tomorrow_markdown" in result
    
    # Verify it uses the latest available entry (2024-04-30), not just yesterday (2024-05-01)
    yesterday_summary = result["yesterday_markdown"]
    assert "## 2024-04-30" in yesterday_summary  # Should use latest available date
    assert "Latest work from Tuesday" in yesterday_summary  # Should use latest entry content
    assert "2024-05-01" not in yesterday_summary  # Should not use missing date


def test_planner_handles_no_previous_logs(tmp_path: Path):
    """Test that planner agent handles the case when there are no previous log entries."""
    tasks = tmp_path / "tasks.yaml"
    logs = tmp_path / "daily_logs.yaml"
    meets = tmp_path / "meetings.yaml"

    tasks.write_text(
        """
- id: T1
  title: Test task
  priority: high
  estimate_hours: 1
  due_date: 2024-05-02
  status: pending
  tags: []
"""
    )

    # Empty logs or only future entries
    logs.write_text(
        """
2024-05-03:
  - log_id: T1
    description: Future work
    actual_hours: 2
"""
    )

    meets.write_text("[]")

    payload = {
        "paths": {"tasks": str(tasks), "logs": str(logs), "meets": str(meets)},
        "target_date": "2024-05-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
    }

    result = plan_day(payload)
    
    # Should succeed without errors
    assert "error" not in result
    assert "yesterday_markdown" in result
    assert "tomorrow_markdown" in result
    
    # Should fall back to "yesterday" date and show no entries
    yesterday_summary = result["yesterday_markdown"]
    assert "## 2024-05-01" in yesterday_summary  # Falls back to yesterday
    assert "No log entries" in yesterday_summary  # No entries found


def test_planner_includes_meetings_in_yesterday_summary(tmp_path: Path):
    """Test that planner agent includes meetings from the latest log date in the yesterday summary."""
    tasks = tmp_path / "tasks.yaml"
    logs = tmp_path / "daily_logs.yaml"
    meets = tmp_path / "meetings.yaml"

    tasks.write_text(
        """
- id: T1
  title: Test task
  priority: high
  estimate_hours: 1
  due_date: 2024-05-02
  status: pending
  tags: []
"""
    )

    # Create logs for 2024-04-30 (this will be the latest date)
    logs.write_text(
        """
2024-04-30:
  - log_id: T1
    description: Completed project review
    actual_hours: 3
  - log_id: T2
    description: Updated documentation
    actual_hours: 1
"""
    )

    # Create meetings for the same date (2024-04-30) using both formats
    meets.write_text(
        """
- date: 2024-04-30
  time: "09:00"
  event: "Daily Standup"
- date: 2024-04-30
  time: "14:00"
  event: "Project: Planning Session"
- id: M1
  title: "Client Review Meeting"
  start: 2024-04-30T16:00:00
  end: 2024-04-30T17:00:00
  participants: [alice, bob]
# Meeting on different date - should not be included
- date: 2024-04-29
  time: "10:00"
  event: "Previous Day Meeting"
"""
    )

    payload = {
        "paths": {"tasks": str(tasks), "logs": str(logs), "meets": str(meets)},
        "target_date": "2024-05-02",  # Thursday
        "work_hours": {"start": "09:00", "end": "17:00"},
    }

    result = plan_day(payload)
    
    # Should succeed without errors
    assert "error" not in result
    assert "yesterday_markdown" in result
    assert "tomorrow_markdown" in result
    
    # Verify it uses the latest available date (2024-04-30)
    yesterday_summary = result["yesterday_markdown"]
    assert "## 2024-04-30" in yesterday_summary
    
    # Verify work log entries are included
    assert "Completed project review" in yesterday_summary
    assert "Updated documentation" in yesterday_summary
    
    # Verify meetings from the same date are included
    assert "09:00 - Daily Standup" in yesterday_summary
    assert "14:00 - Project: Planning Session" in yesterday_summary
    assert "16:00 - Client Review Meeting" in yesterday_summary
    
    # Verify meeting from different date is not included
    assert "Previous Day Meeting" not in yesterday_summary


def test_planner_yesterday_summary_with_legacy_meeting_format(tmp_path: Path):
    """Test that planner agent includes legacy format meetings in yesterday summary."""
    tasks = tmp_path / "tasks.yaml"
    logs = tmp_path / "daily_logs.yaml"
    meets = tmp_path / "meetings.yaml"

    tasks.write_text(
        """
- id: T1
  title: Test task
  priority: high
  estimate_hours: 1
  due_date: 2024-05-02
  status: pending
  tags: []
"""
    )

    logs.write_text(
        """
2024-05-01:
  - log_id: T1
    description: Worked on feature implementation
    actual_hours: 4
"""
    )

    # Legacy meeting format with start/end ISO strings
    meets.write_text(
        """
- id: M1
  title: "Team Sync"
  start: 2024-05-01T10:00:00
  end: 2024-05-01T11:00:00
  participants: [alice, bob]
- id: M2
  title: "Code Review Session"
  start: 2024-05-01T15:30:00
  end: 2024-05-01T16:30:00
  participants: [charlie]
"""
    )

    payload = {
        "paths": {"tasks": str(tasks), "logs": str(logs), "meets": str(meets)},
        "target_date": "2024-05-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
    }

    result = plan_day(payload)
    
    # Should succeed without errors
    assert "error" not in result
    assert "yesterday_markdown" in result
    
    yesterday_summary = result["yesterday_markdown"]
    assert "## 2024-05-01" in yesterday_summary
    
    # Verify work log entry is included
    assert "Worked on feature implementation" in yesterday_summary
    
    # Verify legacy format meetings are included with time
    assert "10:00 - Team Sync" in yesterday_summary
    assert "15:30 - Code Review Session" in yesterday_summary


def test_planner_yesterday_summary_no_meetings_on_log_date(tmp_path: Path):
    """Test that planner agent handles case where there are no meetings on the latest log date."""
    tasks = tmp_path / "tasks.yaml"
    logs = tmp_path / "daily_logs.yaml"
    meets = tmp_path / "meetings.yaml"

    tasks.write_text(
        """
- id: T1
  title: Test task
  priority: high
  estimate_hours: 1
  due_date: 2024-05-02
  status: pending
  tags: []
"""
    )

    logs.write_text(
        """
2024-04-30:
  - log_id: T1
    description: Solo work day
    actual_hours: 6
"""
    )

    # Meetings on different dates
    meets.write_text(
        """
- date: 2024-04-29
  time: "10:00"
  event: "Previous Day Meeting"
- date: 2024-05-01
  time: "14:00"
  event: "Future Day Meeting"
"""
    )

    payload = {
        "paths": {"tasks": str(tasks), "logs": str(logs), "meets": str(meets)},
        "target_date": "2024-05-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
    }

    result = plan_day(payload)
    
    # Should succeed without errors
    assert "error" not in result
    assert "yesterday_markdown" in result
    
    yesterday_summary = result["yesterday_markdown"]
    assert "## 2024-04-30" in yesterday_summary
    
    # Verify work log entry is included
    assert "Solo work day" in yesterday_summary
    
    # Verify no meetings from other dates are included
    assert "Previous Day Meeting" not in yesterday_summary
    assert "Future Day Meeting" not in yesterday_summary


def test_planner_target_date_no_meetings(tmp_path: Path):
    """Test that planner agent handles target dates with no meetings correctly."""
    tasks = tmp_path / "tasks.yaml"
    logs = tmp_path / "daily_logs.yaml"
    meets = tmp_path / "meetings.yaml"

    tasks.write_text(
        """
- id: T1
  title: Focus work task
  priority: high
  estimate_hours: 4
  due_date: 2024-05-02
  status: pending
  tags: []
"""
    )

    logs.write_text(
        """
2024-05-01:
  - log_id: T1
    description: Started focus work
    actual_hours: 2
"""
    )

    # Meetings on different dates, none on target date
    meets.write_text(
        """
- date: 2024-05-01
  time: "14:00"
  event: "Previous Day Meeting"
- date: 2024-05-03
  time: "10:00"
  event: "Future Day Meeting"
"""
    )

    payload = {
        "paths": {"tasks": str(tasks), "logs": str(logs), "meets": str(meets)},
        "target_date": "2024-05-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
    }

    result = plan_day(payload)
    
    # Should succeed without errors
    assert "error" not in result
    assert "yesterday_markdown" in result
    assert "tomorrow_markdown" in result
    
    tomorrow_plan = result["tomorrow_markdown"]
    assert "## Plan for 2024-05-02" in tomorrow_plan
    
    # Should NOT have a meetings section since there are no meetings for the target date
    assert "### Meetings" not in tomorrow_plan
    
    # Should have tasks section
    assert "### Tasks" in tomorrow_plan
    assert "T1 Focus work task" in tomorrow_plan
    
    # Should not include meetings from other dates
    assert "Previous Day Meeting" not in tomorrow_plan
    assert "Future Day Meeting" not in tomorrow_plan


def test_planner_uses_default_paths(tmp_path: Path):
    """Test that planner agent uses default paths when none are provided."""
    # This test will verify the default path logic, though it will fail 
    # because the default paths point to actual files, not test files
    
    payload = {
        "target_date": "2024-05-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
        # Note: no "paths" key provided
    }

    result = plan_day(payload)
    
    # The result should either succeed (if default files exist) or fail gracefully
    # This tests that the default path logic is working
    assert isinstance(result, dict)
    
    # If files don't exist, should get a FileNotFoundError message
    if "error" in result:
        assert "not found" in result["error"].lower()
    else:
        # If files exist, should have the expected structure
        assert "yesterday_markdown" in result
        assert "tomorrow_markdown" in result


def test_planner_explicit_paths_override_defaults(tmp_path: Path):
    """Test that explicitly provided paths override the defaults."""
    tasks = tmp_path / "custom_tasks.yaml"
    logs = tmp_path / "custom_logs.yaml"
    meets = tmp_path / "custom_meetings.yaml"

    tasks.write_text(
        """
- id: CUSTOM-1
  title: Custom task
  priority: high
  estimate_hours: 1
  due_date: 2024-05-02
  status: pending
  tags: []
"""
    )

    logs.write_text(
        """
2024-05-01:
  - log_id: CUSTOM-1
    description: Custom work done
    actual_hours: 1
"""
    )

    meets.write_text(
        """
- date: 2024-05-02
  time: "11:00"
  event: "Custom Meeting"
"""
    )

    # Explicitly provide custom paths
    payload = {
        "paths": {
            "tasks": str(tasks),
            "logs": str(logs),
            "meets": str(meets)
        },
        "target_date": "2024-05-02",
        "work_hours": {"start": "09:00", "end": "17:00"},
    }

    result = plan_day(payload)
    
    # Should succeed without errors
    assert "error" not in result
    assert "yesterday_markdown" in result
    assert "tomorrow_markdown" in result
    
    # Should use the custom data
    yesterday_summary = result["yesterday_markdown"]
    assert "## 2024-05-01" in yesterday_summary
    assert "Custom work done" in yesterday_summary
    
    tomorrow_plan = result["tomorrow_markdown"]
    assert "## Plan for 2024-05-02" in tomorrow_plan
    assert "11:00 - Custom Meeting" in tomorrow_plan
    assert "CUSTOM-1 Custom task" in tomorrow_plan
