"""Async unit tests for task brainstorming functionality."""
import os
import tempfile
import yaml
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import pytest
import asyncio

from src.agents.task_brainstorm import (
    TaskBrainstorm,
    BrainstormManager,
    generate_brainstorm_content
)


class TestGenerateBrainstormContentAsync:
    """Test async brainstorm content generation."""
    
    @pytest.mark.asyncio
    @patch('src.agents.task_brainstorm.RAGAgent')
    @patch('src.agents.task_brainstorm.OpenAIModel')
    async def test_generate_brainstorm_content(self, mock_model, mock_rag_agent):
        """Test generating brainstorm content with RAG and LLM."""
        # Mock RAG agent
        mock_rag_instance = AsyncMock()
        mock_rag_instance.run.return_value = Mock(data="Relevant context from RAG search")
        mock_rag_agent.return_value = mock_rag_instance
        
        # Mock LLM model
        mock_llm_result = Mock()
        mock_llm_result.data = {
            'overview': 'Test overview from LLM',
            'considerations': ['Consideration 1', 'Consideration 2'],
            'approaches': ['Approach 1'],
            'risks': ['Risk 1'],
            'recommendations': ['Recommendation 1']
        }
        
        with patch('src.agents.task_brainstorm.Agent') as mock_agent:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.run.return_value = mock_llm_result
            mock_agent.return_value = mock_agent_instance
            
            task_info = {
                'basic_task': {
                    'id': '111025',
                    'title': 'Test Task',
                    'status': 'pending'
                },
                'task_detail': {
                    'objective': 'Test objective',
                    'tasks': ['Task 1'],
                    'acceptance_criteria': ['Criteria 1']
                }
            }
            
            result = await generate_brainstorm_content(task_info, 'initial')
            
            assert result is not None
            assert result.task_id == '111025'
            assert result.task_title == 'Test Task'
            assert result.brainstorm_type == 'initial'
            assert 'overview' in result.content
            assert len(result.rag_context) > 0
    
    @pytest.mark.asyncio
    @patch('src.agents.task_brainstorm.RAGAgent')
    @patch('src.agents.task_brainstorm.OpenAIModel')
    async def test_generate_brainstorm_content_json_string(self, mock_model, mock_rag_agent):
        """Test generating brainstorm content when LLM returns JSON string."""
        # Mock RAG agent
        mock_rag_instance = AsyncMock()
        mock_rag_instance.run.return_value = Mock(data="Relevant context from RAG search")
        mock_rag_agent.return_value = mock_rag_instance
        
        # Mock LLM model returning JSON string (the case that was causing the error)
        mock_llm_result = Mock()
        mock_llm_result.data = '''{"overview": "Test overview from LLM", "considerations": ["Consideration 1", "Consideration 2"], "approaches": ["Approach 1"], "risks": ["Risk 1"], "recommendations": ["Recommendation 1"]}'''
        
        with patch('src.agents.task_brainstorm.Agent') as mock_agent:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.run.return_value = mock_llm_result
            mock_agent.return_value = mock_agent_instance
            
            task_info = {
                'basic_task': {
                    'id': '111025',
                    'title': 'Test Task',
                    'status': 'pending'
                },
                'task_detail': {
                    'objective': 'Test objective',
                    'tasks': ['Task 1'],
                    'acceptance_criteria': ['Criteria 1']
                }
            }
            
            result = await generate_brainstorm_content(task_info, 'initial')
            
            assert result is not None
            assert result.task_id == '111025'
            assert result.task_title == 'Test Task'
            assert result.brainstorm_type == 'initial'
            assert 'overview' in result.content
            assert result.content['overview'] == 'Test overview from LLM'
            assert len(result.content['considerations']) == 2
            assert len(result.rag_context) > 0
    
    @pytest.mark.asyncio
    @patch('src.agents.task_brainstorm.RAGAgent')
    @patch('src.agents.task_brainstorm.OpenAIModel')
    async def test_generate_brainstorm_content_invalid_json(self, mock_model, mock_rag_agent):
        """Test handling invalid JSON from LLM."""
        # Mock RAG agent
        mock_rag_instance = AsyncMock()
        mock_rag_instance.run.return_value = Mock(data="Relevant context from RAG search")
        mock_rag_agent.return_value = mock_rag_instance
        
        # Mock LLM model returning invalid JSON string
        mock_llm_result = Mock()
        mock_llm_result.data = 'Invalid JSON {not valid json'
        
        with patch('src.agents.task_brainstorm.Agent') as mock_agent:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.run.return_value = mock_llm_result
            mock_agent.return_value = mock_agent_instance
            
            task_info = {
                'basic_task': {
                    'id': '111025',
                    'title': 'Test Task',  
                    'status': 'pending'
                },
                'task_detail': {
                    'objective': 'Test objective',
                    'tasks': ['Task 1'],
                    'acceptance_criteria': ['Criteria 1']
                }
            }
            
            result = await generate_brainstorm_content(task_info, 'initial')
            
            # Should return None on JSON parse error
            assert result is None


class TestBrainstormManagerAsync:
    """Test async BrainstormManager methods."""
    
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
    
    @pytest.mark.asyncio
    @patch('src.agents.task_brainstorm.find_task_by_query')
    @patch('src.agents.task_brainstorm.load_existing_brainstorm')
    async def test_get_existing_brainstorm(self, mock_load_existing, mock_find_task):
        """Test getting existing brainstorm."""
        mock_find_task.return_value = {
            'basic_task': {'id': 'TEST-1', 'title': 'Test Task'}
        }
        mock_load_existing.return_value = "Existing brainstorm content"
        
        result = await self.manager.get_brainstorm('id', 'TEST-1', force_regenerate=False)
        
        assert result['success'] is True
        assert result['content'] == "Existing brainstorm content"
        assert result['source'] == 'existing_collective'
        assert not result['newly_generated']
    
    @pytest.mark.asyncio
    @patch('src.agents.task_brainstorm.find_task_by_query')
    @patch('src.agents.task_brainstorm.load_existing_brainstorm')
    @patch('src.agents.task_brainstorm.generate_brainstorm_content')
    @patch('src.agents.task_brainstorm.save_brainstorm_to_file')
    async def test_generate_new_brainstorm(self, mock_save, mock_generate, mock_load_existing, mock_find_task):
        """Test generating new brainstorm when none exists."""
        mock_find_task.return_value = {
            'basic_task': {'id': 'TEST-1', 'title': 'Test Task'},
            'task_detail': {'objective': 'Test objective'}
        }
        mock_load_existing.return_value = None  # No existing brainstorm
        
        mock_brainstorm = Mock()
        mock_brainstorm.to_markdown.return_value = "New brainstorm content"
        mock_generate.return_value = mock_brainstorm
        
        mock_save.return_value = {'success': True}
        
        result = await self.manager.get_brainstorm('id', 'TEST-1', force_regenerate=False)
        
        assert result['success'] is True
        assert result['content'] == "New brainstorm content"
        assert result['source'] == 'generated'
        assert result['newly_generated'] is True
        
        # Verify generate was called
        mock_generate.assert_called_once()
        mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.agents.task_brainstorm.find_task_by_query')
    async def test_task_not_found(self, mock_find_task):
        """Test handling when task is not found."""
        mock_find_task.return_value = None
        
        result = await self.manager.get_brainstorm('id', 'NON-EXISTENT', force_regenerate=False)
        
        assert result['success'] is False
        assert 'not found' in result['error'].lower()
    
    @pytest.mark.asyncio
    async def test_process_brainstorm_query_initial(self):
        """Test processing initial brainstorm query."""
        with patch.object(self.manager, 'get_brainstorm') as mock_get:
            mock_get.return_value = {
                'success': True,
                'content': 'Brainstorm content',
                'newly_generated': True
            }
            
            result = await self.manager.process_brainstorm_query('brainstorm task id 111025')
            
            assert result['success'] is True
            assert result['content'] == 'Brainstorm content'
            mock_get.assert_called_once_with('id', '111025', False)
    
    @pytest.mark.asyncio
    async def test_process_brainstorm_query_replace(self):
        """Test processing replace brainstorm query."""
        with patch.object(self.manager, 'get_brainstorm') as mock_get:
            mock_get.return_value = {
                'success': True,
                'content': 'New brainstorm content',
                'newly_generated': True
            }
            
            result = await self.manager.process_brainstorm_query('replace brainstorm for task 111025')
            
            assert result['success'] is True
            assert result['content'] == 'New brainstorm content'
            mock_get.assert_called_once_with('id', '111025', True)
    
    @pytest.mark.asyncio
    async def test_process_brainstorm_query_invalid(self):
        """Test processing invalid brainstorm query."""
        result = await self.manager.process_brainstorm_query('invalid query')
        
        assert result['success'] is False
        assert 'could not parse' in result['error'].lower()