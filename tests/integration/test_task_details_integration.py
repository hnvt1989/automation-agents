"""Integration tests for task details with planner system."""
import os
import tempfile
import yaml
from datetime import datetime, timedelta
import pytest

from src.agents.planner import (
    get_task_details,
    get_task_details_markdown,
    list_all_tasks_with_details,
    plan_day
)
from src.agents.planner_task_details import (
    create_task_detail,
    get_task_progress_summary
)


class TestTaskDetailsIntegration:
    """Integration tests for task details with planner system."""
    
    def setup_test_data(self):
        """Set up test data files."""
        # Create temporary files
        self.tasks_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        self.details_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        self.logs_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        self.meetings_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        
        # Sample tasks data
        tasks_data = [
            {
                'id': '111025',
                'title': 'Explore weekly Automated Test coverage Sync to TestRail',
                'priority': 'high',
                'status': 'pending',
                'due_date': '2025-06-09',
                'tags': ['spike', 'work'],
                'estimate_hours': 8
            },
            {
                'id': 'TASK-1',
                'title': 'job search',
                'priority': 'high',
                'status': 'in_progress',
                'due_date': '2025-06-09',
                'tags': ['personal'],
                'estimate_hours': 2
            },
            {
                'id': 'SIMPLE-1',
                'title': 'Simple task without details',
                'priority': 'medium',
                'status': 'pending',
                'due_date': '2025-06-10',
                'estimate_hours': 1
            },
            {
                'id': 'TASK-2',
                'title': 'Complete project documentation',
                'priority': 'medium',
                'status': 'pending',
                'due_date': '2025-06-12',
                'estimate_hours': 3
            }
        ]
        
        # Sample task details data (matching the actual data structure)
        details_data = [
            {
                'id': '111025',
                'title': 'Weekly Automated Test Coverage Integration with TestRail',
                'objective': 'Explore the integration of weekly automated test coverage analysis with TestRail using its API. The goal is to support a mix of frontend and backend automated tests and improve visibility into existing test coverage. This will help identify gaps and provide better context for what manual tests still need to be maintained or added.',
                'tasks': [
                    'Review existing automated test coverage',
                    'Evaluate TestRail API capabilities',
                    'Research tools that generate test coverage reports',
                    'Document findings and recommended next steps'
                ],
                'acceptance_criteria': [
                    {
                        'Summary document outlines': [
                            'Current backend and frontend test coverage tools',
                            'Test scope',
                            'Identified gaps'
                        ]
                    },
                    'Technical review confirms usable TestRail API endpoints for posting test coverage summaries',
                    'Identification and documentation of tools that generate automated test coverage reports',
                    'Documented findings and next steps for integration'
                ]
            }
        ]
        
        # Sample logs data
        logs_data = {
            '2025-06-01': [
                {
                    'log_id': 'TASK-1',
                    'description': 'Updated resume and applied to 3 jobs',
                    'actual_hours': 2.5
                }
            ]
        }
        
        # Sample meetings data
        meetings_data = [
            {
                'date': '2025-06-02',
                'time': '10:00',
                'event': 'Daily standup'
            },
            {
                'date': '2025-06-02',
                'time': '14:00',
                'event': 'TestRail integration planning'
            }
        ]
        
        # Write data to files
        yaml.dump(tasks_data, self.tasks_file)
        yaml.dump(details_data, self.details_file)
        yaml.dump(logs_data, self.logs_file)
        yaml.dump(meetings_data, self.meetings_file)
        
        # Close files
        self.tasks_file.close()
        self.details_file.close()
        self.logs_file.close()
        self.meetings_file.close()
        
        # Store paths
        self.paths = {
            'tasks': self.tasks_file.name,
            'task_details': self.details_file.name,
            'logs': self.logs_file.name,
            'meets': self.meetings_file.name,
            'meeting_notes': tempfile.mkdtemp()
        }
    
    def teardown_test_data(self):
        """Clean up test data files."""
        for path in [self.tasks_file.name, self.details_file.name, 
                     self.logs_file.name, self.meetings_file.name]:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
    
    def test_get_task_details_integration(self):
        """Test getting task details through planner interface."""
        self.setup_test_data()
        
        try:
            # Test getting task with details
            result = get_task_details('111025', self.paths)
            
            assert result['success'] is True
            summary = result['summary']
            assert summary['task_id'] == '111025'
            assert summary['title'] == 'Explore weekly Automated Test coverage Sync to TestRail'
            assert summary['status'] == 'pending'
            assert summary['priority'] == 'high'
            assert summary['has_detailed_breakdown'] is True
            assert summary['subtasks_count'] == 4
            assert 'Review existing automated test coverage' in summary['subtasks']
            assert summary['acceptance_criteria_count'] == 4
            
            # Test getting task without details
            result = get_task_details('SIMPLE-1', self.paths)
            
            assert result['success'] is True
            summary = result['summary']
            assert summary['task_id'] == 'SIMPLE-1'
            assert summary['has_detailed_breakdown'] is False
            assert 'subtasks_count' not in summary
        
        finally:
            self.teardown_test_data()
    
    def test_get_task_details_markdown_integration(self):
        """Test getting task details as markdown through planner interface."""
        self.setup_test_data()
        
        try:
            # Test markdown for task with details
            result = get_task_details_markdown('111025', self.paths)
            
            assert result['success'] is True
            markdown = result['markdown']
            
            # Check markdown structure
            assert '# Task 111025: Explore weekly Automated Test coverage Sync to TestRail' in markdown
            assert '**Status:** pending' in markdown
            assert '**Priority:** high' in markdown
            assert '**Due Date:** 2025-06-09' in markdown
            assert '## Objective' in markdown
            assert 'TestRail using its API' in markdown
            assert '## Tasks' in markdown
            assert '1. Review existing automated test coverage' in markdown
            assert '2. Evaluate TestRail API capabilities' in markdown
            assert '## Acceptance Criteria' in markdown
            
            # Test markdown for task without details
            result = get_task_details_markdown('SIMPLE-1', self.paths)
            
            assert result['success'] is True
            markdown = result['markdown']
            assert '# Task SIMPLE-1: Simple task without details' in markdown
            assert '*No detailed breakdown available for this task.*' in markdown
        
        finally:
            self.teardown_test_data()
    
    def test_list_all_tasks_with_details_integration(self):
        """Test listing all tasks with details status through planner interface."""
        self.setup_test_data()
        
        try:
            result = list_all_tasks_with_details(self.paths)
            
            assert result['success'] is True
            tasks = result['tasks']
            assert len(tasks) == 3
            
            # Find tasks by ID
            task_111025 = next(t for t in tasks if t['id'] == '111025')
            task_simple = next(t for t in tasks if t['id'] == 'SIMPLE-1')
            task_job = next(t for t in tasks if t['id'] == 'TASK-1')
            
            # Check details status
            assert task_111025['has_details'] is True
            assert task_simple['has_details'] is False
            assert task_job['has_details'] is False
            
            # Check basic task information
            assert task_111025['title'] == 'Explore weekly Automated Test coverage Sync to TestRail'
            assert task_111025['priority'] == 'high'
            assert task_111025['status'] == 'pending'
            assert task_111025['due_date'] == '2025-06-09'
        
        finally:
            self.teardown_test_data()
    
    def test_plan_day_with_task_details_integration(self):
        """Test daily planning integration with task details."""
        self.setup_test_data()
        
        try:
            # Plan for June 2, 2025
            payload = {
                'paths': self.paths,
                'target_date': '2025-06-02',
                'work_hours': {
                    'start': '09:00',
                    'end': '17:00'
                },
                'use_llm_for_focus': False  # Disable LLM for testing
            }
            
            result = plan_day(payload)
            
            assert 'error' not in result
            assert 'tomorrow_markdown' in result
            assert 'yesterday_markdown' in result
            
            tomorrow_md = result['tomorrow_markdown']
            
            # Check that tasks are included in the plan
            assert 'Plan for 2025-06-02' in tomorrow_md
            assert '### Meetings' in tomorrow_md
            assert '10:00 - Daily standup' in tomorrow_md
            assert '14:00 - TestRail integration planning' in tomorrow_md
            assert '### Tasks' in tomorrow_md
            
            # The detailed task should be prioritized (high priority, due soon)
            assert '111025' in tomorrow_md or 'TASK-1' in tomorrow_md
        
        finally:
            self.teardown_test_data()
    
    def test_task_details_workflow_integration(self):
        """Test complete workflow: create task detail, get details, format markdown."""
        self.setup_test_data()
        
        try:
            # Create a new task detail for existing simple task
            result = create_task_detail(
                task_id='SIMPLE-1',
                title='Enhanced Simple Task',
                objective='Demonstrate task details workflow integration',
                tasks=[
                    'Define task requirements',
                    'Implement basic functionality',
                    'Write tests',
                    'Document the feature'
                ],
                acceptance_criteria=[
                    'All subtasks are completed',
                    'Tests pass successfully',
                    'Documentation is comprehensive',
                    'Code review is approved'
                ],
                paths=self.paths
            )
            
            assert result['success'] is True
            assert result['task_detail']['id'] == 'SIMPLE-1'
            
            # Now get the enhanced task information
            enhanced_result = get_task_details('SIMPLE-1', self.paths)
            
            assert enhanced_result['success'] is True
            summary = enhanced_result['summary']
            assert summary['has_detailed_breakdown'] is True
            assert summary['subtasks_count'] == 4
            assert summary['acceptance_criteria_count'] == 4
            assert 'Define task requirements' in summary['subtasks']
            
            # Get markdown representation
            markdown_result = get_task_details_markdown('SIMPLE-1', self.paths)
            
            assert markdown_result['success'] is True
            markdown = markdown_result['markdown']
            assert '## Objective' in markdown
            assert 'Demonstrate task details workflow integration' in markdown
            assert '1. Define task requirements' in markdown
            assert '- All subtasks are completed' in markdown
            
            # Verify the task now shows as having details in the list
            list_result = list_all_tasks_with_details(self.paths)
            
            assert list_result['success'] is True
            simple_task = next(t for t in list_result['tasks'] if t['id'] == 'SIMPLE-1')
            assert simple_task['has_details'] is True
        
        finally:
            self.teardown_test_data()
    
    def test_task_progress_summary_integration(self):
        """Test task progress summary with real data structure."""
        self.setup_test_data()
        
        try:
            # Test with task that has complex acceptance criteria
            result = get_task_progress_summary('111025', self.paths)
            
            assert result['success'] is True
            summary = result['summary']
            
            # Check all expected fields
            assert summary['task_id'] == '111025'
            assert summary['title'] == 'Explore weekly Automated Test coverage Sync to TestRail'
            assert summary['status'] == 'pending'
            assert summary['priority'] == 'high'
            assert summary['due_date'] == '2025-06-09'
            assert summary['has_detailed_breakdown'] is True
            
            # Check detailed breakdown
            assert summary['objective'].startswith('Explore the integration of weekly automated test coverage')
            assert summary['subtasks_count'] == 4
            assert len(summary['subtasks']) == 4
            assert summary['acceptance_criteria_count'] == 4
            assert len(summary['acceptance_criteria']) == 4
            
            # Check that subtasks are properly listed
            expected_subtasks = [
                'Review existing automated test coverage',
                'Evaluate TestRail API capabilities',
                'Research tools that generate test coverage reports',
                'Document findings and recommended next steps'
            ]
            
            for expected_task in expected_subtasks:
                assert expected_task in summary['subtasks']
            
            # Check acceptance criteria (should handle both dict and string formats)
            criteria = summary['acceptance_criteria']
            assert any('Summary document outlines' in str(c) for c in criteria)
            assert any('TestRail API endpoints' in str(c) for c in criteria)
        
        finally:
            self.teardown_test_data()
    
    def test_error_handling_integration(self):
        """Test error handling in integration scenarios."""
        self.setup_test_data()
        
        try:
            # Test getting details for non-existent task
            result = get_task_details('NON-EXISTENT', self.paths)
            
            assert 'error' in result
            assert 'not found' in result['error']
            
            # Test markdown for non-existent task
            result = get_task_details_markdown('NON-EXISTENT', self.paths)
            
            assert result['success'] is True  # Should still succeed but show not found
            assert 'not found' in result['markdown']
            
            # Test with corrupted task details file
            with open(self.paths['task_details'], 'w') as f:
                f.write('invalid yaml content: [')
            
            result = get_task_details('111025', self.paths)
            
            assert 'error' in result
        
        finally:
            self.teardown_test_data()
    
    def test_complex_acceptance_criteria_formatting(self):
        """Test handling of complex nested acceptance criteria."""
        self.setup_test_data()
        
        try:
            # Get markdown for task with complex acceptance criteria
            result = get_task_details_markdown('111025', self.paths)
            
            assert result['success'] is True
            markdown = result['markdown']
            
            # Check that nested acceptance criteria are properly formatted
            assert '## Acceptance Criteria' in markdown
            
            # The complex nested structure should be handled
            assert 'Summary document outlines' in markdown
            assert 'Current backend and frontend test coverage tools' in markdown
            assert 'TestRail API endpoints' in markdown
            assert 'automated test coverage reports' in markdown
        
        finally:
            self.teardown_test_data()
    
    def test_task_detail_with_information_attribute(self):
        """Test task detail with information attribute."""
        self.setup_test_data()
        
        try:
            # Create a task detail with information
            result = create_task_detail(
                task_id='TASK-2',
                title='Complete project documentation',
                objective='Create comprehensive documentation for the automation project',
                tasks=[
                    'Write API documentation',
                    'Create user guide',
                    'Add code examples'
                ],
                acceptance_criteria=[
                    'All APIs are documented',
                    'User guide covers all features',
                    'Code examples are tested'
                ],
                information=[
                    'Reference: https://docs.example.com/style-guide',
                    'Meeting notes from 2025-06-04 discussion',
                    'Include diagrams for complex workflows',
                    'Priority: Focus on RAG system documentation first'
                ],
                paths=self.paths
            )
            
            assert result['success'] is True
            assert 'information' in result['task_detail']
            assert len(result['task_detail']['information']) == 4
            
            # Test get_task_details includes information
            details_result = get_task_details('TASK-2', self.paths)
            
            # Debug print to see what's returned
            if 'error' in details_result:
                print(f"Error in get_task_details: {details_result['error']}")
            
            # The function returns get_task_progress_summary which may not have 'success' key
            # but should have 'summary' if successful or 'error' if failed
            assert 'error' not in details_result
            assert 'summary' in details_result
            assert 'information' in details_result['summary']
            assert details_result['summary']['information_count'] == 4
            
            # Test markdown formatting includes information
            markdown_result = get_task_details_markdown('TASK-2', self.paths)
            assert markdown_result['success'] is True
            markdown = markdown_result['markdown']
            
            assert '## Information' in markdown
            assert '- Reference: https://docs.example.com/style-guide' in markdown
            assert '- Meeting notes from 2025-06-04 discussion' in markdown
            assert '- Include diagrams for complex workflows' in markdown
            assert '- Priority: Focus on RAG system documentation first' in markdown
            
        finally:
            self.teardown_test_data()


class TestRealDataCompatibility:
    """Test compatibility with actual data files."""
    
    def test_with_actual_data_structure(self):
        """Test that the system works with the actual data structure from the repository."""
        # Use the actual data from the repository if available
        actual_paths = {
            'tasks': 'data/tasks.yaml',
            'task_details': 'data/task_details.yaml'
        }
        
        # Only run this test if the actual files exist
        if not all(os.path.exists(path) for path in actual_paths.values()):
            pytest.skip("Actual data files not available")
        
        # Test getting details for the actual task ID from the data
        result = get_task_details('111025', actual_paths)
        
        if result.get('success'):
            summary = result['summary']
            assert summary['task_id'] == '111025'
            assert 'TestRail' in summary['title']
            
            if summary['has_detailed_breakdown']:
                assert summary['subtasks_count'] > 0
                assert summary['acceptance_criteria_count'] > 0
                assert 'automated test coverage' in summary['objective'].lower()
        
        # Test markdown formatting with actual data
        markdown_result = get_task_details_markdown('111025', actual_paths)
        
        if markdown_result.get('success'):
            markdown = markdown_result['markdown']
            assert '# Task 111025:' in markdown
            assert 'TestRail' in markdown
    
    def test_list_actual_tasks(self):
        """Test listing actual tasks with details status."""
        actual_paths = {
            'tasks': 'data/tasks.yaml',
            'task_details': 'data/task_details.yaml'
        }
        
        # Only run this test if the actual files exist
        if not all(os.path.exists(path) for path in actual_paths.values()):
            pytest.skip("Actual data files not available")
        
        result = list_all_tasks_with_details(actual_paths)
        
        if result.get('success'):
            tasks = result['tasks']
            assert len(tasks) > 0
            
            # Should have the TestRail task
            testrail_task = next((t for t in tasks if '111025' in t['id']), None)
            if testrail_task:
                assert 'TestRail' in testrail_task['title']
                # This task should have details based on the data structure
                assert testrail_task['has_details'] is True