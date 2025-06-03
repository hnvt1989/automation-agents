"""Unit tests for task details functionality."""
import os
import tempfile
import yaml
from unittest.mock import patch
import pytest

from src.agents.planner_task_details import (
    TaskDetail,
    load_task_details,
    save_task_details,
    get_task_detail_by_id,
    get_enhanced_task_info,
    create_task_detail,
    update_task_detail,
    delete_task_detail,
    list_tasks_with_details,
    get_task_progress_summary,
    format_task_detail_markdown
)


class TestTaskDetail:
    """Test TaskDetail dataclass."""
    
    def test_from_dict(self):
        """Test creating TaskDetail from dictionary."""
        data = {
            'id': 'TEST-1',
            'title': 'Test Task',
            'objective': 'Test objective',
            'tasks': ['Task 1', 'Task 2'],
            'acceptance_criteria': ['Criterion 1', 'Criterion 2']
        }
        
        task_detail = TaskDetail.from_dict(data)
        
        assert task_detail.id == 'TEST-1'
        assert task_detail.title == 'Test Task'
        assert task_detail.objective == 'Test objective'
        assert task_detail.tasks == ['Task 1', 'Task 2']
        assert task_detail.acceptance_criteria == ['Criterion 1', 'Criterion 2']
    
    def test_from_dict_minimal(self):
        """Test creating TaskDetail with minimal data."""
        data = {
            'id': 'TEST-1',
            'title': 'Test Task',
            'objective': 'Test objective'
        }
        
        task_detail = TaskDetail.from_dict(data)
        
        assert task_detail.id == 'TEST-1'
        assert task_detail.title == 'Test Task'
        assert task_detail.objective == 'Test objective'
        assert task_detail.tasks == []
        assert task_detail.acceptance_criteria == []
    
    def test_to_dict(self):
        """Test converting TaskDetail to dictionary."""
        task_detail = TaskDetail(
            id='TEST-1',
            title='Test Task',
            objective='Test objective',
            tasks=['Task 1', 'Task 2'],
            acceptance_criteria=['Criterion 1', 'Criterion 2']
        )
        
        data = task_detail.to_dict()
        
        expected = {
            'id': 'TEST-1',
            'title': 'Test Task',
            'objective': 'Test objective',
            'tasks': ['Task 1', 'Task 2'],
            'acceptance_criteria': ['Criterion 1', 'Criterion 2']
        }
        
        assert data == expected


class TestLoadSaveTaskDetails:
    """Test loading and saving task details."""
    
    def test_load_task_details_empty_file(self):
        """Test loading from empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump([], f)
            temp_path = f.name
        
        try:
            paths = {'task_details': temp_path}
            result = load_task_details(paths)
            assert result == []
        finally:
            os.unlink(temp_path)
    
    def test_load_task_details_with_data(self):
        """Test loading from file with data."""
        data = [
            {
                'id': 'TEST-1',
                'title': 'Test Task 1',
                'objective': 'Test objective 1',
                'tasks': ['Task 1'],
                'acceptance_criteria': ['Criterion 1']
            },
            {
                'id': 'TEST-2',
                'title': 'Test Task 2',
                'objective': 'Test objective 2',
                'tasks': ['Task 2'],
                'acceptance_criteria': ['Criterion 2']
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(data, f)
            temp_path = f.name
        
        try:
            paths = {'task_details': temp_path}
            result = load_task_details(paths)
            
            assert len(result) == 2
            assert result[0].id == 'TEST-1'
            assert result[1].id == 'TEST-2'
        finally:
            os.unlink(temp_path)
    
    def test_load_task_details_file_not_found(self):
        """Test loading from non-existent file."""
        paths = {'task_details': '/non/existent/path.yaml'}
        
        with pytest.raises(ValueError, match="Error loading task details"):
            load_task_details(paths)
    
    def test_save_task_details(self):
        """Test saving task details."""
        task_details = [
            TaskDetail(
                id='TEST-1',
                title='Test Task',
                objective='Test objective',
                tasks=['Task 1'],
                acceptance_criteria=['Criterion 1']
            )
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            paths = {'task_details': temp_path}
            save_task_details(task_details, paths)
            
            # Load and verify
            with open(temp_path, 'r') as f:
                data = yaml.safe_load(f)
            
            assert len(data) == 1
            assert data[0]['id'] == 'TEST-1'
            assert data[0]['title'] == 'Test Task'
        finally:
            os.unlink(temp_path)


class TestGetTaskDetailById:
    """Test getting task detail by ID."""
    
    def test_get_existing_task_detail(self):
        """Test getting an existing task detail."""
        data = [
            {
                'id': 'TEST-1',
                'title': 'Test Task 1',
                'objective': 'Test objective 1',
                'tasks': [],
                'acceptance_criteria': []
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(data, f)
            temp_path = f.name
        
        try:
            paths = {'task_details': temp_path}
            result = get_task_detail_by_id('TEST-1', paths)
            
            assert result is not None
            assert result.id == 'TEST-1'
            assert result.title == 'Test Task 1'
        finally:
            os.unlink(temp_path)
    
    def test_get_non_existing_task_detail(self):
        """Test getting a non-existing task detail."""
        data = []
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(data, f)
            temp_path = f.name
        
        try:
            paths = {'task_details': temp_path}
            result = get_task_detail_by_id('NON-EXISTENT', paths)
            
            assert result is None
        finally:
            os.unlink(temp_path)


class TestCreateTaskDetail:
    """Test creating task details."""
    
    def test_create_new_task_detail(self):
        """Test creating a new task detail."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump([], f)
            temp_path = f.name
        
        try:
            paths = {'task_details': temp_path}
            result = create_task_detail(
                task_id='NEW-1',
                title='New Task',
                objective='New objective',
                tasks=['Task 1', 'Task 2'],
                acceptance_criteria=['Criterion 1'],
                paths=paths
            )
            
            assert result['success'] is True
            assert result['task_detail']['id'] == 'NEW-1'
            assert result['task_detail']['title'] == 'New Task'
            
            # Verify it was saved
            task_details = load_task_details(paths)
            assert len(task_details) == 1
            assert task_details[0].id == 'NEW-1'
        finally:
            os.unlink(temp_path)
    
    def test_create_duplicate_task_detail(self):
        """Test creating a task detail with existing ID."""
        data = [
            {
                'id': 'EXISTING-1',
                'title': 'Existing Task',
                'objective': 'Existing objective',
                'tasks': [],
                'acceptance_criteria': []
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(data, f)
            temp_path = f.name
        
        try:
            paths = {'task_details': temp_path}
            result = create_task_detail(
                task_id='EXISTING-1',
                title='New Task',
                objective='New objective',
                tasks=[],
                acceptance_criteria=[],
                paths=paths
            )
            
            assert 'error' in result
            assert 'already exists' in result['error']
        finally:
            os.unlink(temp_path)


class TestUpdateTaskDetail:
    """Test updating task details."""
    
    def test_update_existing_task_detail(self):
        """Test updating an existing task detail."""
        data = [
            {
                'id': 'UPDATE-1',
                'title': 'Original Title',
                'objective': 'Original objective',
                'tasks': ['Original task'],
                'acceptance_criteria': ['Original criterion']
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(data, f)
            temp_path = f.name
        
        try:
            paths = {'task_details': temp_path}
            updates = {
                'title': 'Updated Title',
                'objective': 'Updated objective'
            }
            
            result = update_task_detail('UPDATE-1', updates, paths)
            
            assert result['success'] is True
            assert result['updated_fields'] == ['title', 'objective']
            assert result['task_detail']['title'] == 'Updated Title'
            assert result['task_detail']['objective'] == 'Updated objective'
            
            # Verify it was saved
            task_details = load_task_details(paths)
            assert task_details[0].title == 'Updated Title'
            assert task_details[0].objective == 'Updated objective'
        finally:
            os.unlink(temp_path)
    
    def test_update_non_existing_task_detail(self):
        """Test updating a non-existing task detail."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump([], f)
            temp_path = f.name
        
        try:
            paths = {'task_details': temp_path}
            updates = {'title': 'Updated Title'}
            
            result = update_task_detail('NON-EXISTENT', updates, paths)
            
            assert 'error' in result
            assert 'not found' in result['error']
        finally:
            os.unlink(temp_path)


class TestDeleteTaskDetail:
    """Test deleting task details."""
    
    def test_delete_existing_task_detail(self):
        """Test deleting an existing task detail."""
        data = [
            {
                'id': 'DELETE-1',
                'title': 'Task to Delete',
                'objective': 'Will be deleted',
                'tasks': [],
                'acceptance_criteria': []
            },
            {
                'id': 'KEEP-1',
                'title': 'Task to Keep',
                'objective': 'Will remain',
                'tasks': [],
                'acceptance_criteria': []
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(data, f)
            temp_path = f.name
        
        try:
            paths = {'task_details': temp_path}
            result = delete_task_detail('DELETE-1', paths)
            
            assert result['success'] is True
            assert 'deleted successfully' in result['message']
            
            # Verify it was deleted
            task_details = load_task_details(paths)
            assert len(task_details) == 1
            assert task_details[0].id == 'KEEP-1'
        finally:
            os.unlink(temp_path)
    
    def test_delete_non_existing_task_detail(self):
        """Test deleting a non-existing task detail."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump([], f)
            temp_path = f.name
        
        try:
            paths = {'task_details': temp_path}
            result = delete_task_detail('NON-EXISTENT', paths)
            
            assert 'error' in result
            assert 'not found' in result['error']
        finally:
            os.unlink(temp_path)


class TestGetEnhancedTaskInfo:
    """Test getting enhanced task information."""
    
    def test_get_enhanced_task_info_with_details(self):
        """Test getting enhanced info for task with details."""
        # Create tasks file
        tasks_data = [
            {
                'id': 'ENHANCED-1',
                'title': 'Basic Task',
                'status': 'pending',
                'priority': 'high'
            }
        ]
        
        # Create task details file
        details_data = [
            {
                'id': 'ENHANCED-1',
                'title': 'Detailed Task',
                'objective': 'Detailed objective',
                'tasks': ['Subtask 1'],
                'acceptance_criteria': ['Criterion 1']
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tf, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as df:
            
            yaml.dump(tasks_data, tf)
            yaml.dump(details_data, df)
            tasks_path = tf.name
            details_path = df.name
        
        try:
            paths = {
                'tasks': tasks_path,
                'task_details': details_path
            }
            
            result = get_enhanced_task_info('ENHANCED-1', paths)
            
            assert result['error'] is None
            assert result['basic_task'] is not None
            assert result['task_detail'] is not None
            assert result['has_details'] is True
            assert result['basic_task']['id'] == 'ENHANCED-1'
            assert result['task_detail'].id == 'ENHANCED-1'
        finally:
            os.unlink(tasks_path)
            os.unlink(details_path)
    
    def test_get_enhanced_task_info_without_details(self):
        """Test getting enhanced info for task without details."""
        # Create tasks file
        tasks_data = [
            {
                'id': 'NO-DETAILS-1',
                'title': 'Basic Task Only',
                'status': 'pending',
                'priority': 'medium'
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tf, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as df:
            
            yaml.dump(tasks_data, tf)
            yaml.dump([], df)  # Empty details file
            tasks_path = tf.name
            details_path = df.name
        
        try:
            paths = {
                'tasks': tasks_path,
                'task_details': details_path
            }
            
            result = get_enhanced_task_info('NO-DETAILS-1', paths)
            
            assert result['error'] is None
            assert result['basic_task'] is not None
            assert result['task_detail'] is None
            assert result['has_details'] is False
            assert result['basic_task']['id'] == 'NO-DETAILS-1'
        finally:
            os.unlink(tasks_path)
            os.unlink(details_path)


class TestFormatTaskDetailMarkdown:
    """Test markdown formatting of task details."""
    
    def test_format_task_with_details(self):
        """Test formatting task that has detailed breakdown."""
        # Create tasks file
        tasks_data = [
            {
                'id': 'FORMAT-1',
                'title': 'Task for Formatting',
                'status': 'in_progress',
                'priority': 'high',
                'due_date': '2025-06-10'
            }
        ]
        
        # Create task details file
        details_data = [
            {
                'id': 'FORMAT-1',
                'title': 'Detailed Formatting Task',
                'objective': 'Create comprehensive formatting for tasks',
                'tasks': [
                    'Implement markdown generation',
                    'Add proper formatting',
                    'Test output'
                ],
                'acceptance_criteria': [
                    'Markdown is properly formatted',
                    'All sections are included',
                    'Output is readable'
                ]
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tf, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as df:
            
            yaml.dump(tasks_data, tf)
            yaml.dump(details_data, df)
            tasks_path = tf.name
            details_path = df.name
        
        try:
            paths = {
                'tasks': tasks_path,
                'task_details': details_path
            }
            
            markdown = format_task_detail_markdown('FORMAT-1', paths)
            
            # Check that markdown contains expected sections
            assert '# Task FORMAT-1: Task for Formatting' in markdown
            assert '**Status:** in_progress' in markdown
            assert '**Priority:** high' in markdown
            assert '**Due Date:** 2025-06-10' in markdown
            assert '## Objective' in markdown
            assert 'Create comprehensive formatting for tasks' in markdown
            assert '## Tasks' in markdown
            assert '1. Implement markdown generation' in markdown
            assert '2. Add proper formatting' in markdown
            assert '3. Test output' in markdown
            assert '## Acceptance Criteria' in markdown
            assert '- Markdown is properly formatted' in markdown
            assert '- All sections are included' in markdown
            assert '- Output is readable' in markdown
        finally:
            os.unlink(tasks_path)
            os.unlink(details_path)
    
    def test_format_task_without_details(self):
        """Test formatting task without detailed breakdown."""
        # Create tasks file
        tasks_data = [
            {
                'id': 'NO-FORMAT-1',
                'title': 'Simple Task',
                'status': 'pending',
                'priority': 'low'
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tf, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as df:
            
            yaml.dump(tasks_data, tf)
            yaml.dump([], df)  # Empty details file
            tasks_path = tf.name
            details_path = df.name
        
        try:
            paths = {
                'tasks': tasks_path,
                'task_details': details_path
            }
            
            markdown = format_task_detail_markdown('NO-FORMAT-1', paths)
            
            # Check basic task information
            assert '# Task NO-FORMAT-1: Simple Task' in markdown
            assert '**Status:** pending' in markdown
            assert '**Priority:** low' in markdown
            assert '*No detailed breakdown available for this task.*' in markdown
        finally:
            os.unlink(tasks_path)
            os.unlink(details_path)


class TestListTasksWithDetails:
    """Test listing tasks with detail status."""
    
    def test_list_mixed_tasks(self):
        """Test listing tasks where some have details and some don't."""
        # Create tasks file
        tasks_data = [
            {
                'id': 'WITH-DETAILS-1',
                'title': 'Task with Details',
                'status': 'pending',
                'priority': 'high',
                'due_date': '2025-06-10'
            },
            {
                'id': 'NO-DETAILS-1',
                'title': 'Task without Details',
                'status': 'in_progress',
                'priority': 'medium'
            }
        ]
        
        # Create task details file
        details_data = [
            {
                'id': 'WITH-DETAILS-1',
                'title': 'Detailed Task',
                'objective': 'Has detailed breakdown',
                'tasks': [],
                'acceptance_criteria': []
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tf, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as df:
            
            yaml.dump(tasks_data, tf)
            yaml.dump(details_data, df)
            tasks_path = tf.name
            details_path = df.name
        
        try:
            paths = {
                'tasks': tasks_path,
                'task_details': details_path
            }
            
            result = list_tasks_with_details(paths)
            
            assert result['success'] is True
            assert len(result['tasks']) == 2
            
            # Find tasks by ID
            with_details = next(t for t in result['tasks'] if t['id'] == 'WITH-DETAILS-1')
            without_details = next(t for t in result['tasks'] if t['id'] == 'NO-DETAILS-1')
            
            assert with_details['has_details'] is True
            assert without_details['has_details'] is False
            assert with_details['title'] == 'Task with Details'
            assert without_details['title'] == 'Task without Details'
        finally:
            os.unlink(tasks_path)
            os.unlink(details_path)