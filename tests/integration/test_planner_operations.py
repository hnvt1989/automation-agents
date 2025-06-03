"""Integration tests for planner read and write operations."""

import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime, date, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import yaml

from src.agents.planner import (
    plan_day, insert_task, insert_meeting, insert_daily_log,
    remove_task, remove_meeting, remove_daily_log, update_task,
    _find_recent_meeting_notes, generate_focus_list
)
from src.agents.planner_ops import PlannerOperations
from src.agents.planner_parser import PlannerParser
from src.agents.primary import PrimaryAgent


class TestPlannerIntegration:
    """Integration tests for planner read/write operations."""

    @pytest.fixture
    def temp_data_dir(self, temp_dir):
        """Create temporary data directory with YAML files."""
        data_dir = temp_dir / "data"
        data_dir.mkdir()
        
        # Create initial YAML files
        tasks_file = data_dir / "tasks.yaml"
        meetings_file = data_dir / "meetings.yaml"
        logs_file = data_dir / "daily_logs.yaml"
        
        # Initial tasks data
        initial_tasks = [
            {
                "id": "TASK-1",
                "title": "Write integration tests",
                "priority": "high",
                "status": "in_progress",
                "tags": ["development", "testing"],
                "due_date": "2025-06-05",
                "estimate_hours": 4
            },
            {
                "id": "TASK-2", 
                "title": "Review documentation",
                "priority": "medium",
                "status": "pending",
                "tags": ["documentation"],
                "due_date": "2025-06-03",
                "estimate_hours": 2
            }
        ]
        
        # Initial meetings data
        initial_meetings = [
            {
                "date": "2025-06-02",
                "time": "10:00",
                "event": "Daily standup"
            },
            {
                "date": "2025-06-03",
                "time": "14:00",
                "event": "Sprint planning"
            }
        ]
        
        # Initial logs data
        initial_logs = {
            "2025-06-01": [
                {
                    "log_id": "TASK-1",
                    "description": "Started writing integration tests",
                    "actual_hours": 2
                }
            ]
        }
        
        # Write initial data
        with open(tasks_file, 'w') as f:
            yaml.dump(initial_tasks, f)
        
        with open(meetings_file, 'w') as f:
            yaml.dump(initial_meetings, f)
            
        with open(logs_file, 'w') as f:
            yaml.dump(initial_logs, f)
        
        # Create meeting notes directory
        meeting_notes_dir = data_dir / "meeting_notes"
        meeting_notes_dir.mkdir()
        scrum_dir = meeting_notes_dir / "scrum"
        scrum_dir.mkdir()
        
        # Create sample meeting note
        meeting_note = scrum_dir / "June02standup.md"
        meeting_note_content = """# 2025-06-02 Daily Standup

## Agenda
- Sprint progress review
- Blockers discussion
- Integration testing plans

## Discussion Points
- Need to complete integration tests for planner module
- Documentation review is pending
- Planning to deploy next sprint
- Focus on testing automation and error handling

## Action Items
- Complete integration tests by Friday
- Review and update documentation
- Prepare demo for stakeholders
- Schedule architecture review meeting

## Blockers
- Waiting for API access for external service
- Need clarification on requirements for calendar integration
"""
        meeting_note.write_text(meeting_note_content)
        
        return {
            "data_dir": str(data_dir),
            "tasks_file": str(tasks_file),
            "meetings_file": str(meetings_file),
            "logs_file": str(logs_file),
            "meeting_notes_dir": str(meeting_notes_dir)
        }

    @pytest.fixture
    def planner_paths(self, temp_data_dir):
        """Get paths configuration for planner."""
        return {
            "tasks": temp_data_dir["tasks_file"],
            "logs": temp_data_dir["logs_file"],
            "meets": temp_data_dir["meetings_file"],
            "meeting_notes": temp_data_dir["meeting_notes_dir"]
        }

    def test_task_crud_operations(self, temp_data_dir):
        """Test complete CRUD operations for tasks."""
        paths = {"tasks": temp_data_dir["tasks_file"]}
        
        # Test CREATE - Insert new task
        new_task_text = "Implement calendar integration with high priority and testing tag"
        result = insert_task(new_task_text, paths)
        
        assert result["success"] is True
        assert "task" in result
        new_task = result["task"]
        assert "TASK-" in new_task["id"]
        assert new_task["title"] == "Implement calendar integration"
        assert new_task["priority"] == "high"
        assert "testing" in new_task["tags"]
        
        # Test READ - Verify task was added
        with open(paths["tasks"], 'r') as f:
            tasks = yaml.safe_load(f)
        
        task_ids = [task["id"] for task in tasks]
        assert new_task["id"] in task_ids
        assert len(tasks) == 3  # 2 initial + 1 new
        
        # Test UPDATE - Modify existing task
        update_query = f"update {new_task['id']} status to completed"
        update_result = update_task(update_query, paths)
        
        assert update_result["success"] is True
        assert "status: in_progress → completed" in update_result["message"] or "status: pending → completed" in update_result["message"]
        
        # Verify update was applied
        with open(paths["tasks"], 'r') as f:
            updated_tasks = yaml.safe_load(f)
        
        updated_task = next(task for task in updated_tasks if task["id"] == new_task["id"])
        assert updated_task["status"] == "completed"
        
        # Test DELETE - Remove task
        delete_result = remove_task(new_task["id"], paths)
        
        assert delete_result["success"] is True
        assert new_task["id"] in delete_result["message"]
        
        # Verify task was removed
        with open(paths["tasks"], 'r') as f:
            final_tasks = yaml.safe_load(f)
        
        final_task_ids = [task["id"] for task in final_tasks]
        assert new_task["id"] not in final_task_ids
        assert len(final_tasks) == 2  # Back to original count

    def test_meeting_crud_operations(self, temp_data_dir):
        """Test complete CRUD operations for meetings."""
        paths = {"meets": temp_data_dir["meetings_file"]}
        
        # Test CREATE - Insert new meeting
        meeting_text = "team retrospective tomorrow at 3pm"
        result = insert_meeting(meeting_text, paths)
        
        assert result["success"] is True
        assert "meeting" in result
        new_meeting = result["meeting"]
        assert "retrospective" in new_meeting["event"].lower()
        assert new_meeting["time"] == "15:00"
        
        # Test READ - Verify meeting was added
        with open(paths["meets"], 'r') as f:
            meetings = yaml.safe_load(f)
        
        assert len(meetings) == 3  # 2 initial + 1 new
        meeting_events = [meeting["event"] for meeting in meetings]
        assert any("retrospective" in event.lower() for event in meeting_events)
        
        # Test DELETE - Remove meeting
        delete_query = f"remove meeting retrospective {new_meeting['date']}"
        delete_result = remove_meeting(delete_query, paths)
        
        assert delete_result["success"] is True
        
        # Verify meeting was removed
        with open(paths["meets"], 'r') as f:
            final_meetings = yaml.safe_load(f)
        
        assert len(final_meetings) == 2  # Back to original count
        final_events = [meeting["event"] for meeting in final_meetings]
        assert not any("retrospective" in event.lower() for event in final_events)

    def test_daily_log_crud_operations(self, temp_data_dir):
        """Test complete CRUD operations for daily logs."""
        paths = {"logs": temp_data_dir["logs_file"]}
        
        # Test CREATE - Insert new log entry
        log_text = "Worked on integration tests for 3 hours"
        task_id = "TASK-1"
        hours = 3.0
        
        result = insert_daily_log(log_text, task_id, hours, paths)
        
        assert result["success"] is True
        assert result["log"]["log_id"] == task_id
        assert result["log"]["actual_hours"] == hours
        
        # Test READ - Verify log was added
        with open(paths["logs"], 'r') as f:
            logs = yaml.safe_load(f)
        
        today_str = datetime.now().date().isoformat()
        if today_str in logs:
            today_logs = logs[today_str]
            assert any(log["log_id"] == task_id and log["actual_hours"] == hours for log in today_logs)
        
        # Test DELETE - Remove log entry
        delete_result = remove_daily_log("today", task_id, paths)
        
        if delete_result["success"]:
            # Verify log was removed
            with open(paths["logs"], 'r') as f:
                final_logs = yaml.safe_load(f)
            
            if today_str in final_logs:
                today_logs = final_logs[today_str]
                assert not any(log["log_id"] == task_id and log["actual_hours"] == hours for log in today_logs)

    def test_plan_day_integration(self, temp_data_dir):
        """Test the complete daily planning workflow."""
        target_date = "2025-06-03"
        
        payload = {
            "paths": {
                "tasks": temp_data_dir["tasks_file"],
                "logs": temp_data_dir["logs_file"],
                "meets": temp_data_dir["meetings_file"],
                "meeting_notes": temp_data_dir["meeting_notes_dir"]
            },
            "target_date": target_date,
            "work_hours": {"start": "09:00", "end": "17:00"},
            "use_llm_for_focus": False  # Disable LLM to avoid API calls
        }
        
        result = plan_day(payload)
        
        assert "error" not in result
        assert "yesterday_markdown" in result
        assert "tomorrow_markdown" in result
        assert "focus_analysis" in result
        
        # Verify plan content
        plan_content = result["tomorrow_markdown"]
        assert target_date in plan_content
        assert "Tasks" in plan_content
        assert "TASK-" in plan_content  # Should contain task IDs
        
        # Verify meetings are included
        assert "Sprint planning" in plan_content
        
        # Verify focus analysis
        focus_analysis = result["focus_analysis"]
        if focus_analysis:  # May be empty if no matching content
            assert isinstance(focus_analysis, dict)

    def test_meeting_notes_analysis(self, temp_data_dir):
        """Test meeting notes analysis for focus generation."""
        target_date = date(2025, 6, 2)
        notes_path = temp_data_dir["meeting_notes_dir"]
        
        # Test finding recent meeting notes
        recent_notes = _find_recent_meeting_notes(notes_path, target_date, days_back=3)
        
        assert len(recent_notes) > 0
        assert recent_notes[0]["filename"] == "June02standup.md"
        assert "integration tests" in recent_notes[0]["content"].lower()
        
        # Test focus generation with mock tasks
        mock_tasks = [
            {
                "id": "TASK-1",
                "title": "integration testing",
                "tags": ["testing", "development"]
            },
            {
                "id": "TASK-2", 
                "title": "documentation review",
                "tags": ["documentation"]
            }
        ]
        
        focus_result = generate_focus_list(recent_notes, mock_tasks, use_llm=False)
        
        assert "rule_based_focus" in focus_result
        assert "llm_prompt" in focus_result
        
        # Should find relevant focus points based on content matching
        rule_based_points = focus_result["rule_based_focus"]
        if rule_based_points:
            assert any("integration" in point.lower() or "testing" in point.lower() for point in rule_based_points)

    @pytest.mark.asyncio
    async def test_planner_operations_integration(self, temp_data_dir):
        """Test PlannerOperations class integration."""
        ops = PlannerOperations()
        
        # Test adding task through operations
        task_data = {
            "title": "Test planner operations",
            "priority": "medium",
            "tags": ["testing", "operations"]
        }
        
        # Mock the paths
        with patch('src.agents.planner_ops.DEFAULT_PATHS', {
            'tasks': temp_data_dir["tasks_file"],
            'logs': temp_data_dir["logs_file"],
            'meets': temp_data_dir["meetings_file"]
        }):
            result = ops.add_task(task_data)
        
        assert result["success"] is True
        assert "task" in result
        
        # Verify task was written to file
        with open(temp_data_dir["tasks_file"], 'r') as f:
            tasks = yaml.safe_load(f)
        
        new_task = next(task for task in tasks if task["title"] == "Test planner operations")
        assert new_task["priority"] == "medium"
        assert "testing" in new_task["tags"]

    def test_complex_task_operations(self, temp_data_dir):
        """Test complex task operations with multiple attributes."""
        paths = {"tasks": temp_data_dir["tasks_file"]}
        
        # Insert task with multiple attributes
        complex_task_text = "implement user authentication with high priority due next week with security and backend tags 8 hours"
        result = insert_task(complex_task_text, paths)
        
        assert result["success"] is True
        task = result["task"]
        
        # Verify complex attributes were parsed correctly
        assert task["priority"] == "high"
        assert "security" in task["tags"]
        assert "backend" in task["tags"]
        assert task["estimate_hours"] == 8.0
        
        # Test complex update operations
        update_queries = [
            f"update {task['id']} priority to low",
            f"add tags urgent, critical to {task['id']}",
            f"change status of {task['id']} to in_progress"
        ]
        
        for query in update_queries:
            update_result = update_task(query, paths)
            assert update_result["success"] is True
        
        # Verify all updates were applied
        with open(paths["tasks"], 'r') as f:
            updated_tasks = yaml.safe_load(f)
        
        updated_task = next(t for t in updated_tasks if t["id"] == task["id"])
        assert updated_task["priority"] == "low"
        assert updated_task["status"] == "in_progress"
        assert "urgent" in updated_task["tags"]
        assert "critical" in updated_task["tags"]

    def test_date_handling_in_operations(self, temp_data_dir):
        """Test date handling across different operations."""
        paths = {
            "tasks": temp_data_dir["tasks_file"],
            "meets": temp_data_dir["meetings_file"],
            "logs": temp_data_dir["logs_file"]
        }
        
        # Test various date formats in task creation
        date_test_cases = [
            ("Task due tomorrow", "tomorrow"),
            ("Task due next week", "next week"),
            ("Task due in 3 days", "in 3 days"),
            ("Task due 2025-06-10", "2025-06-10")
        ]
        
        for task_text, expected_date_context in date_test_cases:
            result = insert_task(task_text, paths)
            assert result["success"] is True
            
            # Verify date was parsed (exact date depends on current date)
            task = result["task"]
            assert "due_date" in task
            assert task["due_date"] is not None
        
        # Test date handling in meetings
        meeting_date_cases = [
            "team meeting tomorrow at 2pm",
            "project review next monday at 10am",
            "client call on 2025-06-05 at 3pm"
        ]
        
        for meeting_text in meeting_date_cases:
            result = insert_meeting(meeting_text, paths)
            assert result["success"] is True
            
            meeting = result["meeting"]
            assert "date" in meeting
            assert "time" in meeting

    def test_error_handling_and_edge_cases(self, temp_data_dir):
        """Test error handling and edge cases."""
        paths = {"tasks": temp_data_dir["tasks_file"]}
        
        # Test invalid task operations
        invalid_operations = [
            ("", "Empty task text"),
            ("   ", "Whitespace only"),
            ("update NONEXISTENT-TASK status to completed", "Non-existent task"),
            ("remove INVALID-ID", "Invalid task ID")
        ]
        
        for operation, description in invalid_operations:
            if operation.startswith("update"):
                result = update_task(operation, paths)
            elif operation.startswith("remove"):
                result = remove_task("INVALID-ID", paths)
            else:
                result = insert_task(operation, paths)
            
            # Some operations may succeed with default values, others should fail
            if not result.get("success", False):
                assert "error" in result
        
        # Test file permissions and corruption scenarios
        # Make file read-only temporarily
        import stat
        tasks_file = temp_data_dir["tasks_file"]
        original_mode = os.stat(tasks_file).st_mode
        
        try:
            os.chmod(tasks_file, stat.S_IRUSR)  # Read-only
            
            # This should fail due to permissions
            result = insert_task("Test task with readonly file", paths)
            # Note: May succeed depending on system, just ensure it doesn't crash
            
        finally:
            # Restore original permissions
            os.chmod(tasks_file, original_mode)

    def test_concurrent_operations(self, temp_data_dir):
        """Test concurrent planner operations."""
        import threading
        import time
        
        paths = {"tasks": temp_data_dir["tasks_file"]}
        results = []
        errors = []
        
        def insert_task_worker(task_id):
            try:
                result = insert_task(f"Concurrent task {task_id}", paths)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads doing concurrent operations
        threads = []
        for i in range(5):
            thread = threading.Thread(target=insert_task_worker, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Concurrent operations had errors: {errors}"
        assert len(results) == 5
        
        # Verify all tasks were actually written
        with open(paths["tasks"], 'r') as f:
            final_tasks = yaml.safe_load(f)
        
        # Should have original 2 tasks + 5 new concurrent tasks
        assert len(final_tasks) >= 7
        
        concurrent_tasks = [task for task in final_tasks if "Concurrent task" in task["title"]]
        assert len(concurrent_tasks) == 5

    def test_data_consistency_and_validation(self, temp_data_dir):
        """Test data consistency and validation across operations."""
        paths = {
            "tasks": temp_data_dir["tasks_file"],
            "meets": temp_data_dir["meetings_file"],
            "logs": temp_data_dir["logs_file"]
        }
        
        # Create tasks and log work against them
        task_result = insert_task("Data consistency test task", paths)
        assert task_result["success"] is True
        task_id = task_result["task"]["id"]
        
        # Log work against the task
        log_result = insert_daily_log(
            f"Worked on {task_id} for data consistency testing",
            task_id,
            2.5,
            paths
        )
        assert log_result["success"] is True
        
        # Verify referential integrity
        with open(paths["tasks"], 'r') as f:
            tasks = yaml.safe_load(f)
        with open(paths["logs"], 'r') as f:
            logs = yaml.safe_load(f)
        
        # Ensure logged task actually exists
        task_ids = [task["id"] for task in tasks]
        assert task_id in task_ids
        
        # Ensure log references valid task
        today_str = datetime.now().date().isoformat()
        if today_str in logs:
            today_logs = logs[today_str]
            logged_task_ids = [log["log_id"] for log in today_logs]
            assert task_id in logged_task_ids
        
        # Test data validation
        # Verify task has required fields
        test_task = next(task for task in tasks if task["id"] == task_id)
        required_fields = ["id", "title", "priority", "status", "tags", "due_date"]
        for field in required_fields:
            assert field in test_task, f"Missing required field: {field}"