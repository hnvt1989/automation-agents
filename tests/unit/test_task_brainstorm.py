"""Unit tests for task brainstorming functionality."""
import os
import tempfile
import yaml
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pytest
import asyncio

from src.agents.task_brainstorm import (
    TaskBrainstorm,
    BrainstormManager,
    parse_brainstorm_query,
    generate_brainstorm_content,
    save_brainstorm_to_file,
    load_existing_brainstorm,
    find_task_by_query
)


class TestTaskBrainstorm:
    """Test TaskBrainstorm dataclass."""
    
    def test_task_brainstorm_creation(self):
        """Test creating TaskBrainstorm instance."""
        brainstorm = TaskBrainstorm(
            task_id='TEST-1',
            task_title='Test Task',
            brainstorm_type='initial',
            generated_at=datetime.now(),
            content={
                'overview': 'Test overview',
                'considerations': ['Point 1', 'Point 2'],
                'approaches': ['Approach 1', 'Approach 2'],
                'risks': ['Risk 1'],
                'recommendations': ['Rec 1']
            },
            rag_context=['Context 1', 'Context 2'],
            sources=['source1.md', 'source2.md']
        )
        
        assert brainstorm.task_id == 'TEST-1'
        assert brainstorm.task_title == 'Test Task'
        assert brainstorm.brainstorm_type == 'initial'
        assert len(brainstorm.content['considerations']) == 2
        assert len(brainstorm.rag_context) == 2
        assert len(brainstorm.sources) == 2
    
    def test_to_dict(self):
        """Test converting TaskBrainstorm to dictionary."""
        timestamp = datetime.now()
        brainstorm = TaskBrainstorm(
            task_id='TEST-1',
            task_title='Test Task',
            brainstorm_type='initial',
            generated_at=timestamp,
            content={'overview': 'Test'},
            rag_context=['Context'],
            sources=['source.md']
        )
        
        data = brainstorm.to_dict()
        
        assert data['task_id'] == 'TEST-1'
        assert data['task_title'] == 'Test Task'
        assert data['brainstorm_type'] == 'initial'
        assert data['generated_at'] == timestamp.isoformat()
        assert data['content'] == {'overview': 'Test'}
        assert data['rag_context'] == ['Context']
        assert data['sources'] == ['source.md']
    
    def test_from_dict(self):
        """Test creating TaskBrainstorm from dictionary."""
        timestamp = datetime.now()
        data = {
            'task_id': 'TEST-1',
            'task_title': 'Test Task',
            'brainstorm_type': 'initial',
            'generated_at': timestamp.isoformat(),
            'content': {'overview': 'Test'},
            'rag_context': ['Context'],
            'sources': ['source.md']
        }
        
        brainstorm = TaskBrainstorm.from_dict(data)
        
        assert brainstorm.task_id == 'TEST-1'
        assert brainstorm.task_title == 'Test Task'
        assert brainstorm.brainstorm_type == 'initial'
        assert brainstorm.generated_at == timestamp
        assert brainstorm.content == {'overview': 'Test'}
        assert brainstorm.rag_context == ['Context']
        assert brainstorm.sources == ['source.md']
    
    def test_to_markdown(self):
        """Test converting TaskBrainstorm to markdown."""
        brainstorm = TaskBrainstorm(
            task_id='TEST-1',
            task_title='Test Task',
            brainstorm_type='initial',
            generated_at=datetime(2025, 6, 2, 10, 30),
            content={
                'overview': 'This is a test overview',
                'considerations': ['Point 1', 'Point 2'],
                'approaches': ['Approach 1', 'Approach 2'],
                'risks': ['Risk 1'],
                'recommendations': ['Rec 1']
            },
            rag_context=['Relevant context from RAG'],
            sources=['source1.md']
        )
        
        markdown = brainstorm.to_markdown()
        
        # Check basic structure
        assert '# Brainstorm: Test Task (TEST-1)' in markdown
        assert '**Generated:** 2025-06-02 10:30:00' in markdown
        assert '**Type:** initial' in markdown
        assert '## Overview' in markdown
        assert 'This is a test overview' in markdown
        assert '## Key Considerations' in markdown
        assert '- Point 1' in markdown
        assert '- Point 2' in markdown
        assert '## Potential Approaches' in markdown
        assert '- Approach 1' in markdown
        assert '## Risks and Challenges' in markdown
        assert '## Recommendations' in markdown
        assert '## RAG Context Used' in markdown
        assert 'Relevant context from RAG' in markdown
        assert '## Sources' in markdown
        assert '- source1.md' in markdown


class TestParseBrainstormQuery:
    """Test parsing brainstorm queries."""
    
    def test_parse_by_task_id(self):
        """Test parsing query with task ID."""
        queries = [
            'brainstorm a task with id 111025',
            'brainstorm task with id 111025',
            'brainstorm task id 111025',
            'brainstorm 111025'
        ]
        
        for query in queries:
            result = parse_brainstorm_query(query)
            assert result['type'] == 'id'
            assert result['value'] == '111025'
            assert result['action'] == 'brainstorm'
    
    def test_parse_by_title(self):
        """Test parsing query with task title."""
        queries = [
            'brainstorm a task with title TestRail integration',
            'brainstorm task with title TestRail integration',
            'brainstorm task title "TestRail integration"',
            "brainstorm task title 'TestRail integration'"
        ]
        
        for query in queries:
            result = parse_brainstorm_query(query)
            assert result['type'] == 'title'
            assert result['value'] == 'TestRail integration'
            assert result['action'] == 'brainstorm'
    
    def test_parse_replace_brainstorm(self):
        """Test parsing replace/improve brainstorm queries."""
        queries = [
            'replace brainstorm for task 111025',
            'improve brainstorm for task 111025',
            'update brainstorm for task 111025',
            'redo brainstorm for task 111025'
        ]
        
        for query in queries:
            result = parse_brainstorm_query(query)
            assert result['type'] == 'id'
            assert result['value'] == '111025'
            assert result['action'] in ['replace', 'improve', 'update', 'redo']
    
    def test_parse_invalid_query(self):
        """Test parsing invalid queries."""
        invalid_queries = [
            'just some text',
            'task without the b-word keyword'  # Can't use brainstorm in invalid test
        ]
        
        for query in invalid_queries:
            result = parse_brainstorm_query(query)
            assert result is None


class TestFindTaskByQuery:
    """Test finding tasks by query."""
    
    def setup_method(self):
        """Set up test data."""
        self.sample_tasks = [
            {
                'id': '111025',
                'title': 'Explore weekly Automated Test coverage Sync to TestRail',
                'status': 'pending',
                'priority': 'high'
            },
            {
                'id': 'TASK-1',
                'title': 'job search',
                'status': 'in_progress',
                'priority': 'high'
            }
        ]
        
        self.sample_task_details = [
            {
                'id': '111025',
                'title': 'Weekly Automated Test Coverage Integration with TestRail',
                'objective': 'Explore TestRail integration for test coverage',
                'tasks': ['Review coverage', 'Evaluate API'],
                'acceptance_criteria': ['API endpoints identified']
            }
        ]
    
    @patch('src.agents.task_brainstorm._load_yaml')
    def test_find_task_by_id(self, mock_load_yaml):
        """Test finding task by ID."""
        mock_load_yaml.side_effect = [self.sample_tasks, self.sample_task_details]
        
        result = find_task_by_query('id', '111025')
        
        assert result is not None
        assert result['basic_task']['id'] == '111025'
        assert result['task_detail'] is not None
        assert result['task_detail']['id'] == '111025'
    
    @patch('src.agents.task_brainstorm._load_yaml')
    def test_find_task_by_title_exact_match(self, mock_load_yaml):
        """Test finding task by exact title match."""
        mock_load_yaml.side_effect = [self.sample_tasks, self.sample_task_details]
        
        result = find_task_by_query('title', 'job search')
        
        assert result is not None
        assert result['basic_task']['id'] == 'TASK-1'
        assert result['basic_task']['title'] == 'job search'
    
    @patch('src.agents.task_brainstorm._load_yaml')
    def test_find_task_by_title_partial_match(self, mock_load_yaml):
        """Test finding task by partial title match."""
        mock_load_yaml.side_effect = [self.sample_tasks, self.sample_task_details]
        
        result = find_task_by_query('title', 'TestRail')
        
        assert result is not None
        assert result['basic_task']['id'] == '111025'
        assert 'TestRail' in result['basic_task']['title']
    
    @patch('src.agents.task_brainstorm._load_yaml')
    def test_find_task_not_found(self, mock_load_yaml):
        """Test finding non-existent task."""
        mock_load_yaml.side_effect = [self.sample_tasks, self.sample_task_details]
        
        result = find_task_by_query('id', 'NON-EXISTENT')
        
        assert result is None


class TestGenerateBrainstormContent:
    """Test brainstorm content generation - async tests moved to test_task_brainstorm_async.py."""
    pass  # Async tests are in test_task_brainstorm_async.py


class TestSaveLoadBrainstorm:
    """Test saving and loading brainstorms."""
    
    def test_save_brainstorm_to_file_new_file(self):
        """Test saving brainstorm to new file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            temp_path = f.name
        
        try:
            os.unlink(temp_path)  # Remove the file so we can test creation
            
            brainstorm = TaskBrainstorm(
                task_id='TEST-1',
                task_title='Test Task',
                brainstorm_type='initial',
                generated_at=datetime.now(),
                content={'overview': 'Test overview'},
                rag_context=['Context'],
                sources=['source.md']
            )
            
            result = save_brainstorm_to_file(brainstorm, temp_path)
            
            assert result['success'] is True
            assert os.path.exists(temp_path)
            
            # Check file content
            with open(temp_path, 'r') as f:
                content = f.read()
            
            assert '# Brainstorm: Test Task (TEST-1)' in content
            assert 'Test overview' in content
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_save_brainstorm_to_file_append(self):
        """Test appending brainstorm to existing file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Existing Content\n\nSome existing brainstorms.\n\n")
            temp_path = f.name
        
        try:
            brainstorm = TaskBrainstorm(
                task_id='TEST-1',
                task_title='Test Task',
                brainstorm_type='initial',
                generated_at=datetime.now(),
                content={'overview': 'Test overview'},
                rag_context=['Context'],
                sources=['source.md']
            )
            
            result = save_brainstorm_to_file(brainstorm, temp_path)
            
            assert result['success'] is True
            
            # Check file content
            with open(temp_path, 'r') as f:
                content = f.read()
            
            assert 'Existing Content' in content
            assert '# Brainstorm: Test Task (TEST-1)' in content
        
        finally:
            os.unlink(temp_path)
    
    def test_load_existing_brainstorm_found(self):
        """Test loading existing brainstorm when it exists."""
        content = """# Some content

## Brainstorm: Test Task (TEST-1)

**Generated:** 2025-06-02 10:30:00
**Type:** initial

### Overview
Test overview content

More content here.

## Another Brainstorm: Different Task (TEST-2)

Different content.
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = load_existing_brainstorm('TEST-1', temp_path)
            
            assert result is not None
            assert 'Test Task (TEST-1)' in result
            assert 'Test overview content' in result
        
        finally:
            os.unlink(temp_path)
    
    def test_load_existing_brainstorm_not_found(self):
        """Test loading brainstorm when it doesn't exist."""
        content = """# Some content

## Brainstorm: Different Task (TEST-2)

Some other content.
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = load_existing_brainstorm('TEST-1', temp_path)
            
            assert result is None
        
        finally:
            os.unlink(temp_path)
    
    def test_load_existing_brainstorm_file_not_exists(self):
        """Test loading brainstorm when file doesn't exist."""
        result = load_existing_brainstorm('TEST-1', '/non/existent/path.md')
        
        assert result is None


class TestBrainstormManager:
    """Test BrainstormManager class."""
    
    def setup_method(self):
        """Set up test data."""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
        self.temp_file.close()
        self.brainstorm_file = self.temp_file.name
        
        self.manager = BrainstormManager(
            brainstorm_file=self.brainstorm_file,
            tasks_file='dummy_tasks.yaml',
            task_details_file='dummy_details.yaml'
        )
    
    def teardown_method(self):
        """Clean up test data."""
        if os.path.exists(self.brainstorm_file):
            os.unlink(self.brainstorm_file)
    
    def test_get_existing_brainstorm(self):
        """Test getting existing brainstorm - moved to async test file."""
        pass  # Async test moved to test_task_brainstorm_async.py
    
    def test_generate_new_brainstorm(self):
        """Test generating new brainstorm when none exists - moved to async test file."""
        pass  # Async test moved to test_task_brainstorm_async.py
    
    def test_task_not_found(self):
        """Test handling when task is not found - moved to async test file."""
        pass  # Async test moved to test_task_brainstorm_async.py
    
    def test_process_brainstorm_query_initial(self):
        """Test processing initial brainstorm query - moved to async test file."""
        pass  # Async test moved to test_task_brainstorm_async.py
    
    def test_process_brainstorm_query_replace(self):
        """Test processing replace brainstorm query - moved to async test file."""
        pass  # Async test moved to test_task_brainstorm_async.py
    
    def test_process_brainstorm_query_invalid(self):
        """Test processing invalid brainstorm query - moved to async test file."""
        pass  # Async test moved to test_task_brainstorm_async.py