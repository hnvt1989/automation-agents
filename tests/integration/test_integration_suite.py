"""Comprehensive integration test suite for automation-agents."""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch


class TestIntegrationSuite:
    """High-level integration tests that combine multiple components."""

    @pytest.fixture
    def test_workspace(self, temp_dir):
        """Create a complete test workspace with all necessary directories and files."""
        workspace = {
            "data_dir": temp_dir / "data",
            "images_dir": temp_dir / "images", 
            "docs_dir": temp_dir / "docs",
            "chroma_dir": temp_dir / "chroma_db"
        }
        
        # Create directories
        for dir_path in workspace.values():
            dir_path.mkdir(parents=True)
        
        # Create sample documents
        docs_dir = workspace["docs_dir"]
        (docs_dir / "api_documentation.md").write_text("""
# API Documentation

## Calendar Integration
The calendar API allows parsing of calendar screenshots and text.

### Endpoints
- POST /calendar/parse - Parse calendar from image
- GET /calendar/events - List parsed events

## Meeting Notes
Meeting notes are automatically analyzed for focus areas.
""")
        
        (docs_dir / "team_processes.py").write_text("""
def schedule_meeting(title, date, time, attendees):
    \"\"\"Schedule a team meeting.\"\"\"
    return {
        "event": title,
        "date": date,
        "time": time,
        "attendees": attendees
    }

def generate_focus_areas(meeting_notes, tasks):
    \"\"\"Generate focus areas from meeting notes.\"\"\"
    return ["Focus on API integration", "Review documentation"]
""")
        
        # Create sample images directory with mock files
        images_dir = workspace["images_dir"]
        for filename in ["calendar_screenshot.png", "slack_conversation.png", "meeting_notes.jpg"]:
            (images_dir / filename).write_bytes(b'\x89PNG\r\n\x1a\n')  # Mock PNG header
        
        # Create planner data files
        data_dir = workspace["data_dir"]
        
        # Sample tasks
        import yaml
        tasks = [
            {
                "id": "INTEGRATION-1",
                "title": "Complete API documentation review",
                "priority": "high",
                "status": "in_progress", 
                "tags": ["documentation", "api"],
                "due_date": "2025-06-05",
                "estimate_hours": 3
            },
            {
                "id": "INTEGRATION-2",
                "title": "Implement calendar parsing integration",
                "priority": "medium",
                "status": "pending",
                "tags": ["calendar", "integration"],
                "due_date": "2025-06-07",
                "estimate_hours": 5
            }
        ]
        
        with open(data_dir / "tasks.yaml", 'w') as f:
            yaml.dump(tasks, f)
        
        # Sample meetings
        meetings = [
            {"date": "2025-06-03", "time": "09:00", "event": "Daily standup"},
            {"date": "2025-06-03", "time": "14:00", "event": "Integration review"}
        ]
        
        with open(data_dir / "meetings.yaml", 'w') as f:
            yaml.dump(meetings, f)
        
        # Sample logs
        logs = {
            "2025-06-02": [
                {
                    "log_id": "INTEGRATION-1", 
                    "description": "Reviewed API documentation structure",
                    "actual_hours": 2
                }
            ]
        }
        
        with open(data_dir / "daily_logs.yaml", 'w') as f:
            yaml.dump(logs, f)
        
        # Create meeting notes
        meeting_notes_dir = data_dir / "meeting_notes"
        meeting_notes_dir.mkdir()
        (meeting_notes_dir / "integration_meeting.md").write_text("""
# Integration Team Meeting - June 2, 2025

## Attendees
- Alice (Tech Lead)
- Bob (Backend Developer)  
- Charlie (Frontend Developer)

## Discussion Points
- API documentation needs review and updates
- Calendar parsing integration is priority for next sprint
- Focus on improving test coverage for integration scenarios

## Action Items
- Complete API documentation review by Friday
- Implement calendar parsing integration
- Add comprehensive integration tests

## Decisions
- Use OCR for calendar screenshot parsing
- Implement conversation parsing for team communications
- Focus on file indexing performance improvements
""")
        
        return workspace

    @pytest.mark.asyncio
    async def test_complete_workflow_file_indexing_to_search(self, test_workspace):
        """Test complete workflow from file indexing to search and retrieval."""
        from src.storage.chromadb_client import ChromaDBClient
        
        # Initialize ChromaDB client
        chroma_client = ChromaDBClient(persist_directory=str(test_workspace["chroma_dir"]))
        
        # Mock the LLM context generation to avoid API calls
        with patch.object(chroma_client, '_generate_chunk_context', return_value="Integration test content"):
            # Index documentation files
            docs_dir = test_workspace["docs_dir"]
            result = await chroma_client.add_directory(str(docs_dir), recursive=True)
            
            assert result["success"] is True
            assert result["files_processed"] >= 2
            assert result["total_chunks_added"] > 0
        
        # Search for indexed content
        search_results = await chroma_client.search("API documentation", n_results=5)
        
        assert len(search_results["documents"]) > 0
        assert any("API" in doc for doc in search_results["documents"])
        
        # Test semantic search
        focus_results = await chroma_client.search("team meeting focus areas", n_results=3)
        assert len(focus_results["documents"]) > 0

    @pytest.mark.asyncio
    async def test_complete_planner_workflow(self, test_workspace):
        """Test complete planner workflow with focus analysis."""
        from src.agents.planner import plan_day, _find_recent_meeting_notes, generate_focus_list
        
        data_dir = test_workspace["data_dir"]
        
        # Test planning workflow
        payload = {
            "paths": {
                "tasks": str(data_dir / "tasks.yaml"),
                "logs": str(data_dir / "daily_logs.yaml"),
                "meets": str(data_dir / "meetings.yaml"),
                "meeting_notes": str(data_dir / "meeting_notes")
            },
            "target_date": "2025-06-03",
            "work_hours": {"start": "09:00", "end": "17:00"},
            "use_llm_for_focus": False  # Disable LLM to avoid API calls
        }
        
        result = plan_day(payload)
        
        # Verify planning output
        assert "error" not in result
        assert "yesterday_markdown" in result
        assert "tomorrow_markdown" in result
        assert "focus_analysis" in result
        
        # Verify content includes tasks and meetings
        plan_content = result["tomorrow_markdown"]
        assert "INTEGRATION-1" in plan_content or "API documentation" in plan_content
        assert "Daily standup" in plan_content
        
        # Verify focus analysis includes meeting-based insights
        focus_analysis = result["focus_analysis"]
        if focus_analysis.get("rule_based_focus"):
            # Should have found relevant focus areas
            assert isinstance(focus_analysis["rule_based_focus"], list)

    @pytest.mark.asyncio 
    async def test_calendar_parsing_integration_workflow(self, test_workspace):
        """Test calendar parsing integrated with planner."""
        from src.processors.calendar import CalendarProcessor
        from src.processors.image import extract_text_from_image
        
        # Mock calendar screenshot text
        mock_calendar_text = """
Monday, June 3, 2025

9:00 AM - 10:00 AM    Daily Standup
Location: Conference Room A

2:00 PM - 3:00 PM     Integration Review Meeting
Location: Virtual (Teams)
Attendees: Development Team

4:00 PM - 5:00 PM     Planning Session
Location: Conference Room B
"""
        
        calendar_image = test_workspace["images_dir"] / "calendar_screenshot.png"
        
        # Mock OCR extraction
        with patch('src.processors.image.extract_text_from_image') as mock_extract:
            mock_extract.return_value = mock_calendar_text
            
            # Extract calendar text
            extracted_text = await extract_text_from_image(str(calendar_image), 'file')
            
            # Parse calendar events
            calendar_processor = CalendarProcessor()
            events = calendar_processor.parse_calendar_text(extracted_text)
            
            assert len(events) >= 3
            
            # Convert to planner format and integrate
            planner_meetings = calendar_processor.convert_to_planner_format(events)
            
            # Write to meetings file
            import yaml
            meetings_file = test_workspace["data_dir"] / "meetings_from_calendar.yaml"
            with open(meetings_file, 'w') as f:
                yaml.dump(planner_meetings, f)
            
            # Verify integration
            with open(meetings_file, 'r') as f:
                saved_meetings = yaml.safe_load(f)
            
            assert len(saved_meetings) >= 3
            standup_meeting = next((m for m in saved_meetings if "Standup" in m["event"]), None)
            assert standup_meeting is not None

    @pytest.mark.asyncio
    async def test_conversation_parsing_to_indexing_workflow(self, test_workspace):
        """Test complete conversation parsing and indexing workflow."""
        from src.processors.image import extract_text_from_image, parse_conversation_from_text, process_conversation_and_index
        from src.storage.chromadb_client import ChromaDBClient
        
        # Mock conversation screenshot text
        mock_conversation = """
Alice Johnson  2:15 PM
The integration tests are looking good. Should we deploy to staging?

Bob Smith  2:16 PM
I think we should run the full test suite first

Charlie Brown  2:17 PM
Agreed. Also want to make sure the calendar parsing is working correctly

Alice Johnson  2:18 PM
Good point. Let's focus on the API documentation integration too
👍 2

Bob Smith  2:19 PM
I'll handle the deployment checklist
✅ 1
"""
        
        conversation_image = test_workspace["images_dir"] / "slack_conversation.png"
        
        # Initialize ChromaDB for indexing
        chroma_client = ChromaDBClient(persist_directory=str(test_workspace["chroma_dir"]))
        
        # Mock OCR and process conversation
        with patch('src.processors.image.extract_text_from_image') as mock_extract:
            mock_extract.return_value = mock_conversation
            
            # Extract conversation text
            extracted_text = await extract_text_from_image(str(conversation_image), 'file')
            
            # Parse conversation
            conversation = await parse_conversation_from_text(extracted_text, str(conversation_image))
            
            assert conversation is not None
            assert conversation.platform == "slack"
            assert len(conversation.messages) >= 4
            assert "Alice Johnson" in conversation.participants
            
            # Index conversation
            await process_conversation_and_index(conversation, chroma_client.collection)
            
            # Search indexed conversation
            search_results = await chroma_client.search("integration tests deployment", n_results=3)
            assert len(search_results["documents"]) > 0

    @pytest.mark.asyncio
    async def test_multi_component_integration_scenario(self, test_workspace):
        """Test integration scenario involving multiple components."""
        from src.agents.planner import plan_day, insert_task
        from src.storage.chromadb_client import ChromaDBClient
        from src.processors.calendar import CalendarProcessor
        
        data_dir = test_workspace["data_dir"]
        
        # 1. Index project documentation
        chroma_client = ChromaDBClient(persist_directory=str(test_workspace["chroma_dir"]))
        
        with patch.object(chroma_client, '_generate_chunk_context', return_value="Project documentation"):
            docs_result = await chroma_client.add_directory(str(test_workspace["docs_dir"]))
            assert docs_result["success"] is True
        
        # 2. Add new task based on "discovered" requirements
        new_task_result = insert_task(
            "Implement real-time calendar sync with high priority due next week",
            {"tasks": str(data_dir / "tasks.yaml")}
        )
        assert new_task_result["success"] is True
        
        # 3. Parse calendar for additional meetings
        mock_calendar = """
Tuesday, June 4, 2025
10:00 AM - 11:00 AM    Architecture Review
3:00 PM - 4:00 PM      Code Review Session
"""
        
        calendar_processor = CalendarProcessor()
        calendar_events = calendar_processor.parse_calendar_text(mock_calendar)
        
        # Convert and add to meetings
        import yaml
        with open(data_dir / "meetings.yaml", 'r') as f:
            existing_meetings = yaml.safe_load(f)
        
        new_meetings = calendar_processor.convert_to_planner_format(calendar_events)
        all_meetings = existing_meetings + new_meetings
        
        with open(data_dir / "meetings.yaml", 'w') as f:
            yaml.dump(all_meetings, f)
        
        # 4. Generate updated plan with all components
        payload = {
            "paths": {
                "tasks": str(data_dir / "tasks.yaml"),
                "logs": str(data_dir / "daily_logs.yaml"), 
                "meets": str(data_dir / "meetings.yaml"),
                "meeting_notes": str(data_dir / "meeting_notes")
            },
            "target_date": "2025-06-04",
            "work_hours": {"start": "09:00", "end": "17:00"},
            "use_llm_for_focus": False
        }
        
        final_plan = plan_day(payload)
        
        # Verify integrated planning
        assert "error" not in final_plan
        plan_content = final_plan["tomorrow_markdown"]
        
        # Should include new task
        assert "calendar sync" in plan_content.lower() or "real-time" in plan_content.lower()
        
        # Should include parsed calendar meetings
        assert "Architecture Review" in plan_content
        
        # 5. Search knowledge base for related information
        kb_results = await chroma_client.search("calendar integration architecture", n_results=3)
        assert len(kb_results["documents"]) > 0

    def test_error_resilience_across_components(self, test_workspace):
        """Test error resilience when components fail."""
        from src.agents.planner import plan_day, insert_task
        
        data_dir = test_workspace["data_dir"]
        
        # Test with corrupted data files
        corrupted_tasks_file = data_dir / "corrupted_tasks.yaml"
        corrupted_tasks_file.write_text("invalid: yaml: content: [unclosed bracket")
        
        # Should handle corrupted files gracefully
        result = insert_task("Test task", {"tasks": str(corrupted_tasks_file)})
        # May fail, but should not crash the system
        assert "error" in result or result.get("success") is False
        
        # Test planning with missing files
        payload = {
            "paths": {
                "tasks": str(data_dir / "nonexistent_tasks.yaml"),
                "logs": str(data_dir / "daily_logs.yaml"),
                "meets": str(data_dir / "meetings.yaml")
            },
            "target_date": "2025-06-04",
            "work_hours": {"start": "09:00", "end": "17:00"}
        }
        
        plan_result = plan_day(payload)
        # Should handle missing files gracefully
        assert "error" in plan_result or "tomorrow_markdown" in plan_result

    @pytest.mark.asyncio
    async def test_performance_integration_scenario(self, test_workspace):
        """Test performance across integrated components."""
        import time
        from src.storage.chromadb_client import ChromaDBClient
        
        # Test indexing performance
        start_time = time.time()
        
        chroma_client = ChromaDBClient(persist_directory=str(test_workspace["chroma_dir"]))
        
        with patch.object(chroma_client, '_generate_chunk_context', return_value="Performance test content"):
            # Index multiple files
            docs_dir = test_workspace["docs_dir"]
            
            # Create additional test files for performance testing
            for i in range(5):
                test_file = docs_dir / f"performance_test_{i}.md"
                test_file.write_text(f"# Performance Test Document {i}\n" + "Content line.\n" * 100)
            
            result = await chroma_client.add_directory(str(docs_dir))
            
        indexing_time = time.time() - start_time
        
        assert result["success"] is True
        assert indexing_time < 30  # Should complete within 30 seconds
        
        # Test search performance
        start_time = time.time()
        
        search_results = await chroma_client.search("performance test", n_results=10)
        
        search_time = time.time() - start_time
        
        assert len(search_results["documents"]) > 0
        assert search_time < 5  # Search should be fast

    @pytest.mark.asyncio
    async def test_data_consistency_across_components(self, test_workspace):
        """Test data consistency when multiple components modify the same data."""
        from src.agents.planner import insert_task, insert_meeting, plan_day
        
        data_dir = test_workspace["data_dir"]
        paths = {
            "tasks": str(data_dir / "tasks.yaml"),
            "logs": str(data_dir / "daily_logs.yaml"),
            "meets": str(data_dir / "meetings.yaml")
        }
        
        # Add multiple tasks and meetings
        task_results = []
        for i in range(3):
            result = insert_task(f"Consistency test task {i} with medium priority", paths)
            task_results.append(result)
            assert result["success"] is True
        
        meeting_results = []
        for i in range(2):
            result = insert_meeting(f"Consistency test meeting {i} tomorrow at {10+i}am", paths)
            meeting_results.append(result)
            assert result["success"] is True
        
        # Generate plan and verify all data is consistent
        payload = {
            "paths": paths,
            "target_date": "2025-06-03",
            "work_hours": {"start": "09:00", "end": "17:00"}
        }
        
        plan_result = plan_day(payload)
        
        assert "error" not in plan_result
        plan_content = plan_result["tomorrow_markdown"]
        
        # Verify tasks and meetings are included in plan
        for task_result in task_results:
            task_id = task_result["task"]["id"]
            assert task_id in plan_content
        
        # Verify meetings are included
        assert "Consistency test meeting" in plan_content