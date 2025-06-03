"""Integration tests for task brainstorming with RAG and planner systems."""
import os
import tempfile
import yaml
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.agents.task_brainstorm import BrainstormManager
from src.agents.planner import brainstorm_task, get_task_brainstorm


class TestBrainstormIntegration:
    """Integration tests for brainstorming system."""
    
    def setup_method(self):
        """Set up test data files."""
        # Create temporary files
        self.tasks_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        self.details_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        self.brainstorm_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
        
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
            }
        ]
        
        # Sample task details data
        details_data = [
            {
                'id': '111025',
                'title': 'Weekly Automated Test Coverage Integration with TestRail',
                'objective': 'Explore the integration of weekly automated test coverage analysis with TestRail using its API. The goal is to support a mix of frontend and backend automated tests and improve visibility into existing test coverage.',
                'tasks': [
                    'Review existing automated test coverage',
                    'Evaluate TestRail API capabilities',
                    'Research tools that generate test coverage reports',
                    'Document findings and recommended next steps'
                ],
                'acceptance_criteria': [
                    'Summary document outlines current tools and gaps',
                    'Technical review confirms usable TestRail API endpoints',
                    'Documentation of automated test coverage report tools',
                    'Documented findings and next steps for integration'
                ]
            }
        ]
        
        # Write data to files
        yaml.dump(tasks_data, self.tasks_file)
        yaml.dump(details_data, self.details_file)
        self.brainstorm_file.write("# Task Brainstorms\n\nThis file contains brainstorming sessions for various tasks.\n\n")
        
        # Close files
        self.tasks_file.close()
        self.details_file.close()
        self.brainstorm_file.close()
        
        # Store paths
        self.paths = {
            'tasks': self.tasks_file.name,
            'task_details': self.details_file.name,
            'brainstorms': self.brainstorm_file.name
        }
    
    def teardown_method(self):
        """Clean up test data files."""
        for path in [self.tasks_file.name, self.details_file.name, self.brainstorm_file.name]:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
    
    @patch('src.agents.task_brainstorm.RAGAgent')
    @patch('src.agents.task_brainstorm.OpenAIModel')
    @patch('src.agents.task_brainstorm.Agent')
    @patch('src.agents.task_brainstorm.get_chromadb_client')
    def test_complete_brainstorm_workflow_new_task(self, mock_chroma, mock_agent_class, mock_model, mock_rag_agent):
        """Test complete brainstorming workflow for a new task."""
        # Mock ChromaDB client
        mock_chroma.return_value = Mock()
        
        # Mock RAG agent
        mock_rag_instance = Mock()
        mock_rag_instance.run.return_value = Mock(
            data="TestRail is a test management tool. It provides API endpoints for integration. Coverage reports can be automated using various tools."
        )
        mock_rag_agent.return_value = mock_rag_instance
        
        # Mock LLM agent
        mock_llm_result = Mock()
        mock_llm_result.data = {
            'overview': 'This task involves integrating automated test coverage reporting with TestRail to improve visibility into testing gaps and provide better context for manual testing needs.',
            'considerations': [
                'TestRail API rate limits and authentication requirements',
                'Different coverage report formats from frontend vs backend tools',
                'Data consistency and accuracy of coverage metrics',
                'Integration frequency and performance impact'
            ],
            'approaches': [
                'Direct API integration using TestRail REST API',
                'Scheduled batch processing of coverage reports',
                'Real-time webhook-based integration',
                'Custom dashboard with TestRail data export'
            ],
            'risks': [
                'API authentication and access control issues',
                'Coverage data accuracy and interpretation challenges',
                'Performance impact on CI/CD pipeline',
                'Maintenance overhead for multiple tool integrations'
            ],
            'recommendations': [
                'Start with a pilot integration using one coverage tool',
                'Implement proper error handling and retry mechanisms',
                'Create comprehensive documentation for the integration process',
                'Set up monitoring and alerting for the integration pipeline'
            ]
        }
        
        mock_agent_instance = Mock()
        mock_agent_instance.run.return_value = mock_llm_result
        mock_agent_class.return_value = mock_agent_instance
        
        # Create manager and test workflow
        manager = BrainstormManager(
            brainstorm_file=self.paths['brainstorms'],
            tasks_file=self.paths['tasks'],
            task_details_file=self.paths['task_details']
        )
        
        # Test brainstorming for task 111025
        result = manager.process_brainstorm_query('brainstorm task id 111025')
        
        assert result['success'] is True
        assert result['newly_generated'] is True
        assert result['source'] == 'generated'
        assert 'TestRail' in result['content']
        assert 'Weekly Automated Test Coverage Integration' in result['content']
        
        # Verify brainstorm was saved to file
        with open(self.paths['brainstorms'], 'r') as f:
            file_content = f.read()
        
        assert '# Brainstorm: Explore weekly Automated Test coverage Sync to TestRail (111025)' in file_content
        assert 'TestRail API rate limits' in file_content
        assert 'Direct API integration' in file_content
        
        # Verify RAG was called with relevant query
        mock_rag_instance.run.assert_called()
        rag_call_args = mock_rag_instance.run.call_args[0][0]
        assert 'TestRail' in rag_call_args or 'test coverage' in rag_call_args
        
        # Verify LLM was called with proper context
        mock_agent_instance.run.assert_called()
        llm_call_args = mock_agent_instance.run.call_args[0][0]
        assert 'TestRail' in llm_call_args
        assert 'coverage' in llm_call_args
    
    @patch('src.agents.task_brainstorm.RAGAgent')
    @patch('src.agents.task_brainstorm.OpenAIModel')
    def test_brainstorm_workflow_existing_task(self, mock_model, mock_rag_agent):
        """Test brainstorming workflow when brainstorm already exists."""
        # Pre-populate brainstorm file with existing content
        existing_content = """# Task Brainstorms

## Brainstorm: Explore weekly Automated Test coverage Sync to TestRail (111025)

**Generated:** 2025-06-01 10:00:00
**Type:** initial

### Overview
Existing brainstorm content for TestRail integration.

### Key Considerations
- Existing consideration 1
- Existing consideration 2

### Potential Approaches
- Existing approach 1

### Risks and Challenges
- Existing risk 1

### Recommendations
- Existing recommendation 1

### RAG Context Used
Previous RAG context about TestRail.

### Sources
- previous_source.md

---

"""
        
        with open(self.paths['brainstorms'], 'w') as f:
            f.write(existing_content)
        
        manager = BrainstormManager(
            brainstorm_file=self.paths['brainstorms'],
            tasks_file=self.paths['tasks'],
            task_details_file=self.paths['task_details']
        )
        
        # Test getting existing brainstorm
        result = manager.process_brainstorm_query('brainstorm task id 111025')
        
        assert result['success'] is True
        assert result['newly_generated'] is False
        assert result['source'] == 'existing'
        assert 'Existing brainstorm content' in result['content']
        assert 'Existing consideration 1' in result['content']
        
        # Verify RAG and LLM were not called since content exists
        mock_rag_agent.assert_not_called()
    
    @patch('src.agents.task_brainstorm.RAGAgent')
    @patch('src.agents.task_brainstorm.OpenAIModel')
    @patch('src.agents.task_brainstorm.Agent')
    @patch('src.agents.task_brainstorm.get_chromadb_client')
    def test_replace_existing_brainstorm(self, mock_chroma, mock_agent_class, mock_model, mock_rag_agent):
        """Test replacing an existing brainstorm."""
        # Pre-populate brainstorm file with existing content
        existing_content = """# Task Brainstorms

## Brainstorm: Explore weekly Automated Test coverage Sync to TestRail (111025)

**Generated:** 2025-06-01 10:00:00
**Type:** initial

### Overview
Old brainstorm content that will be replaced.

---

"""
        
        with open(self.paths['brainstorms'], 'w') as f:
            f.write(existing_content)
        
        # Mock RAG and LLM responses
        mock_chroma.return_value = Mock()
        mock_rag_instance = Mock()
        mock_rag_instance.run.return_value = Mock(data="Updated RAG context")
        mock_rag_agent.return_value = mock_rag_instance
        
        mock_llm_result = Mock()
        mock_llm_result.data = {
            'overview': 'Updated brainstorm content with new insights',
            'considerations': ['New consideration'],
            'approaches': ['New approach'],
            'risks': ['New risk'],
            'recommendations': ['New recommendation']
        }
        
        mock_agent_instance = Mock()
        mock_agent_instance.run.return_value = mock_llm_result
        mock_agent_class.return_value = mock_agent_instance
        
        manager = BrainstormManager(
            brainstorm_file=self.paths['brainstorms'],
            tasks_file=self.paths['tasks'],
            task_details_file=self.paths['task_details']
        )
        
        # Test replacing existing brainstorm
        result = manager.process_brainstorm_query('replace brainstorm for task 111025')
        
        assert result['success'] is True
        assert result['newly_generated'] is True
        assert result['source'] == 'generated'
        assert 'Updated brainstorm content' in result['content']
        
        # Verify new content was appended to file
        with open(self.paths['brainstorms'], 'r') as f:
            file_content = f.read()
        
        # Should contain both old and new brainstorms
        assert 'Old brainstorm content that will be replaced' in file_content
        assert 'Updated brainstorm content' in file_content
        assert file_content.count('## Brainstorm: Explore weekly Automated Test coverage Sync to TestRail (111025)') == 2
    
    def test_brainstorm_task_not_found(self):
        """Test brainstorming for non-existent task."""
        manager = BrainstormManager(
            brainstorm_file=self.paths['brainstorms'],
            tasks_file=self.paths['tasks'],
            task_details_file=self.paths['task_details']
        )
        
        result = manager.process_brainstorm_query('brainstorm task id NON-EXISTENT')
        
        assert result['success'] is False
        assert 'not found' in result['error'].lower()
    
    def test_brainstorm_by_title_partial_match(self):
        """Test brainstorming by partial title match."""
        with open(self.paths['brainstorms'], 'w') as f:
            f.write("# Task Brainstorms\n\n")
        
        with patch('src.agents.task_brainstorm.RAGAgent') as mock_rag_agent, \
             patch('src.agents.task_brainstorm.OpenAIModel') as mock_model, \
             patch('src.agents.task_brainstorm.Agent') as mock_agent_class, \
             patch('src.agents.task_brainstorm.get_chromadb_client') as mock_chroma:
            
            # Setup mocks
            mock_chroma.return_value = Mock()
            mock_rag_instance = Mock()
            mock_rag_instance.run.return_value = Mock(data="RAG context")
            mock_rag_agent.return_value = mock_rag_instance
            
            mock_llm_result = Mock()
            mock_llm_result.data = {
                'overview': 'Job search strategy brainstorm',
                'considerations': ['Market conditions', 'Skill requirements'],
                'approaches': ['Networking', 'Direct applications'],
                'risks': ['Market competition'],
                'recommendations': ['Update resume', 'Practice interviews']
            }
            
            mock_agent_instance = Mock()
            mock_agent_instance.run.return_value = mock_llm_result
            mock_agent_class.return_value = mock_agent_instance
            
            manager = BrainstormManager(
                brainstorm_file=self.paths['brainstorms'],
                tasks_file=self.paths['tasks'],
                task_details_file=self.paths['task_details']
            )
            
            # Test brainstorming by partial title match
            result = manager.process_brainstorm_query('brainstorm task title "job"')
            
            assert result['success'] is True
            assert result['newly_generated'] is True
            assert 'job search' in result['content'].lower()
    
    def test_invalid_brainstorm_query(self):
        """Test handling invalid brainstorm queries."""
        manager = BrainstormManager(
            brainstorm_file=self.paths['brainstorms'],
            tasks_file=self.paths['tasks'],
            task_details_file=self.paths['task_details']
        )
        
        invalid_queries = [
            'just some random text',
            'brainstorm without task reference',
            'task without brainstorm keyword'
        ]
        
        for query in invalid_queries:
            result = manager.process_brainstorm_query(query)
            assert result['success'] is False
            assert 'could not parse' in result['error'].lower()
    
    @patch('src.agents.task_brainstorm.RAGAgent')
    def test_rag_failure_handling(self, mock_rag_agent):
        """Test handling when RAG agent fails."""
        # Mock RAG agent to raise exception
        mock_rag_instance = Mock()
        mock_rag_instance.run.side_effect = Exception("RAG connection failed")
        mock_rag_agent.return_value = mock_rag_instance
        
        with patch('src.agents.task_brainstorm.OpenAIModel') as mock_model, \
             patch('src.agents.task_brainstorm.Agent') as mock_agent_class, \
             patch('src.agents.task_brainstorm.get_chromadb_client') as mock_chroma:
            
            mock_chroma.return_value = Mock()
            
            # LLM should still work even if RAG fails
            mock_llm_result = Mock()
            mock_llm_result.data = {
                'overview': 'Brainstorm without RAG context',
                'considerations': ['Basic consideration'],
                'approaches': ['Basic approach'],
                'risks': ['Basic risk'],
                'recommendations': ['Basic recommendation']
            }
            
            mock_agent_instance = Mock()
            mock_agent_instance.run.return_value = mock_llm_result
            mock_agent_class.return_value = mock_agent_instance
            
            manager = BrainstormManager(
                brainstorm_file=self.paths['brainstorms'],
                tasks_file=self.paths['tasks'],
                task_details_file=self.paths['task_details']
            )
            
            result = manager.process_brainstorm_query('brainstorm task id 111025')
            
            # Should still succeed but without RAG context
            assert result['success'] is True
            assert 'Brainstorm without RAG context' in result['content']
    
    @patch('src.agents.task_brainstorm.get_chromadb_client')
    def test_llm_failure_handling(self, mock_chroma):
        """Test handling when LLM generation fails."""
        mock_chroma.return_value = Mock()
        
        with patch('src.agents.task_brainstorm.RAGAgent') as mock_rag_agent, \
             patch('src.agents.task_brainstorm.OpenAIModel') as mock_model, \
             patch('src.agents.task_brainstorm.Agent') as mock_agent_class:
            
            # RAG should work
            mock_rag_instance = Mock()
            mock_rag_instance.run.return_value = Mock(data="RAG context")
            mock_rag_agent.return_value = mock_rag_instance
            
            # LLM should fail
            mock_agent_instance = Mock()
            mock_agent_instance.run.side_effect = Exception("LLM API failed")
            mock_agent_class.return_value = mock_agent_instance
            
            manager = BrainstormManager(
                brainstorm_file=self.paths['brainstorms'],
                tasks_file=self.paths['tasks'],
                task_details_file=self.paths['task_details']
            )
            
            result = manager.process_brainstorm_query('brainstorm task id 111025')
            
            # Should fail gracefully
            assert result['success'] is False
            assert 'error generating brainstorm' in result['error'].lower()
    
    @patch('src.agents.task_brainstorm.RAGAgent')
    @patch('src.agents.task_brainstorm.OpenAIModel')
    @patch('src.agents.task_brainstorm.Agent')
    @patch('src.agents.task_brainstorm.get_chromadb_client')
    def test_llm_json_string_response(self, mock_chroma, mock_agent_class, mock_model, mock_rag_agent):
        """Test handling when LLM returns JSON as string (the bug that was fixed)."""
        # Mock ChromaDB client
        mock_chroma.return_value = Mock()
        
        # Mock RAG agent
        mock_rag_instance = Mock()
        mock_rag_instance.run.return_value = Mock(
            data="TestRail API context from RAG"
        )
        mock_rag_agent.return_value = mock_rag_instance
        
        # Mock LLM agent returning JSON as string (the case that caused the error)
        mock_llm_result = Mock()
        # This is what was causing the "string indices must be integers" error
        mock_llm_result.data = '''{
            "overview": "This task involves integrating automated test coverage with TestRail",
            "considerations": ["API limits", "Authentication"],
            "approaches": ["Direct API", "Batch processing"],
            "risks": ["Performance impact"],
            "recommendations": ["Start with pilot"]
        }'''
        
        mock_agent_instance = Mock()
        mock_agent_instance.run.return_value = mock_llm_result
        mock_agent_class.return_value = mock_agent_instance
        
        # Create manager and test workflow
        manager = BrainstormManager(
            brainstorm_file=self.paths['brainstorms'],
            tasks_file=self.paths['tasks'],
            task_details_file=self.paths['task_details']
        )
        
        # Test brainstorming - should NOT fail with string indices error
        result = manager.process_brainstorm_query('brainstorm task id 111025')
        
        assert result['success'] is True
        assert result['newly_generated'] is True
        assert 'This task involves integrating automated test coverage' in result['content']
        assert 'API limits' in result['content']
        
        # Verify the brainstorm was saved correctly
        with open(self.paths['brainstorms'], 'r') as f:
            file_content = f.read()
        
        assert 'This task involves integrating automated test coverage' in file_content
        assert '- API limits' in file_content


class TestPlannerIntegration:
    """Test integration with planner system."""
    
    def setup_method(self):
        """Set up test data for planner integration."""
        # Create temporary files
        self.tasks_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        self.details_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        self.brainstorm_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
        
        # Write minimal test data
        yaml.dump([{
            'id': '111025',
            'title': 'TestRail Integration Task',
            'status': 'pending'
        }], self.tasks_file)
        
        yaml.dump([{
            'id': '111025',
            'title': 'TestRail Integration Task',
            'objective': 'Integrate with TestRail API',
            'tasks': ['Research API', 'Implement integration'],
            'acceptance_criteria': ['API integration working']
        }], self.details_file)
        
        self.brainstorm_file.write("# Task Brainstorms\n\n")
        
        # Close files
        self.tasks_file.close()
        self.details_file.close()
        self.brainstorm_file.close()
    
    def teardown_method(self):
        """Clean up test files."""
        for path in [self.tasks_file.name, self.details_file.name, self.brainstorm_file.name]:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
    
    @patch('src.agents.planner.BrainstormManager')
    def test_brainstorm_task_planner_function(self, mock_manager_class):
        """Test brainstorm_task function in planner module."""
        # Mock BrainstormManager
        mock_manager = Mock()
        mock_manager.process_brainstorm_query.return_value = {
            'success': True,
            'content': 'Generated brainstorm content',
            'newly_generated': True,
            'source': 'generated'
        }
        mock_manager_class.return_value = mock_manager
        
        # Test the planner function
        result = brainstorm_task('brainstorm task id 111025', {
            'tasks': self.tasks_file.name,
            'task_details': self.details_file.name,
            'brainstorms': self.brainstorm_file.name
        })
        
        assert result['success'] is True
        assert result['content'] == 'Generated brainstorm content'
        assert result['newly_generated'] is True
        
        # Verify manager was created with correct paths
        mock_manager_class.assert_called_once()
        call_kwargs = mock_manager_class.call_args.kwargs
        assert call_kwargs['tasks_file'] == self.tasks_file.name
        assert call_kwargs['task_details_file'] == self.details_file.name
        assert call_kwargs['brainstorm_file'] == self.brainstorm_file.name
        
        # Verify query was processed
        mock_manager.process_brainstorm_query.assert_called_once_with('brainstorm task id 111025')
    
    @patch('src.agents.planner.BrainstormManager')
    def test_get_task_brainstorm_planner_function(self, mock_manager_class):
        """Test get_task_brainstorm function in planner module."""
        # Mock existing brainstorm content
        existing_content = """## Brainstorm: TestRail Integration Task (111025)

**Generated:** 2025-06-02 10:00:00
**Type:** initial

### Overview
Existing brainstorm for TestRail integration.
"""
        
        mock_manager = Mock()
        mock_manager.get_brainstorm.return_value = {
            'success': True,
            'content': existing_content,
            'newly_generated': False,
            'source': 'existing'
        }
        mock_manager_class.return_value = mock_manager
        
        # Test getting existing brainstorm
        result = get_task_brainstorm('111025', {
            'tasks': self.tasks_file.name,
            'task_details': self.details_file.name,
            'brainstorms': self.brainstorm_file.name
        })
        
        assert result['success'] is True
        assert result['content'] == existing_content
        assert result['newly_generated'] is False
        assert 'TestRail integration' in result['content']
        
        # Verify manager was called correctly
        mock_manager.get_brainstorm.assert_called_once_with('id', '111025', force_regenerate=False)
    
    def test_default_file_paths(self):
        """Test that default file paths are used when not specified."""
        with patch('src.agents.planner.BrainstormManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.process_brainstorm_query.return_value = {'success': True}
            mock_manager_class.return_value = mock_manager
            
            # Call without specifying paths
            brainstorm_task('brainstorm task id 111025')
            
            # Verify default paths were used
            call_kwargs = mock_manager_class.call_args.kwargs
            assert 'data/tasks.yaml' in call_kwargs['tasks_file']
            assert 'data/task_details.yaml' in call_kwargs['task_details_file']
            assert 'task_brainstorms.md' in call_kwargs['brainstorm_file']


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""
    
    def setup_method(self):
        """Set up complete test environment."""
        # Create all necessary files
        self.tasks_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        self.details_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        self.brainstorm_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
        
        # Comprehensive test data
        tasks_data = [
            {
                'id': '111025',
                'title': 'Explore weekly Automated Test coverage Sync to TestRail',
                'priority': 'high',
                'status': 'pending',
                'due_date': '2025-06-09'
            }
        ]
        
        details_data = [
            {
                'id': '111025',
                'title': 'Weekly Automated Test Coverage Integration with TestRail',
                'objective': 'Explore the integration of weekly automated test coverage analysis with TestRail using its API.',
                'tasks': [
                    'Review existing automated test coverage',
                    'Evaluate TestRail API capabilities',
                    'Research tools that generate test coverage reports'
                ],
                'acceptance_criteria': [
                    'Summary document outlines current tools and gaps',
                    'Technical review confirms usable TestRail API endpoints'
                ]
            }
        ]
        
        yaml.dump(tasks_data, self.tasks_file)
        yaml.dump(details_data, self.details_file)
        self.brainstorm_file.write("# Task Brainstorms\n\nBrainstorming sessions for project tasks.\n\n")
        
        self.tasks_file.close()
        self.details_file.close()
        self.brainstorm_file.close()
    
    def teardown_method(self):
        """Clean up test environment."""
        for path in [self.tasks_file.name, self.details_file.name, self.brainstorm_file.name]:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
    
    @patch('src.agents.task_brainstorm.RAGAgent')
    @patch('src.agents.task_brainstorm.OpenAIModel')
    @patch('src.agents.task_brainstorm.Agent')
    @patch('src.agents.task_brainstorm.get_chromadb_client')
    def test_complete_workflow_multiple_brainstorms(self, mock_chroma, mock_agent_class, mock_model, mock_rag_agent):
        """Test complete workflow with multiple brainstorm operations."""
        # Setup comprehensive mocks
        mock_chroma.return_value = Mock()
        
        mock_rag_instance = Mock()
        mock_rag_instance.run.return_value = Mock(
            data="TestRail API documentation shows REST endpoints for test management. Coverage tools like Istanbul and Jest provide detailed reports."
        )
        mock_rag_agent.return_value = mock_rag_instance
        
        # Different LLM responses for different calls
        responses = [
            {
                'overview': 'Initial brainstorm for TestRail integration focusing on API capabilities and coverage tool compatibility.',
                'considerations': ['API authentication', 'Rate limiting', 'Data format compatibility'],
                'approaches': ['REST API integration', 'Batch processing', 'Real-time streaming'],
                'risks': ['API changes', 'Performance impact', 'Data accuracy'],
                'recommendations': ['Start with pilot', 'Implement monitoring', 'Document thoroughly']
            },
            {
                'overview': 'Improved brainstorm with enhanced insights on TestRail integration and better architectural considerations.',
                'considerations': ['Enhanced security model', 'Scalability requirements', 'Error handling strategies'],
                'approaches': ['Microservice architecture', 'Event-driven processing', 'Cached reporting'],
                'risks': ['System complexity', 'Maintenance overhead', 'Integration dependencies'],
                'recommendations': ['Phased implementation', 'Comprehensive testing', 'Performance monitoring']
            }
        ]
        
        mock_agent_instance = Mock()
        mock_agent_instance.run.side_effect = [Mock(data=resp) for resp in responses]
        mock_agent_class.return_value = mock_agent_instance
        
        manager = BrainstormManager(
            brainstorm_file=self.brainstorm_file.name,
            tasks_file=self.tasks_file.name,
            task_details_file=self.details_file.name
        )
        
        # Step 1: Initial brainstorm
        result1 = manager.process_brainstorm_query('brainstorm task id 111025')
        
        assert result1['success'] is True
        assert result1['newly_generated'] is True
        assert 'Initial brainstorm for TestRail' in result1['content']
        
        # Step 2: Try to get the same brainstorm (should return existing)
        result2 = manager.process_brainstorm_query('brainstorm task id 111025')
        
        assert result2['success'] is True
        assert result2['newly_generated'] is False
        assert result2['source'] == 'existing'
        assert 'Initial brainstorm for TestRail' in result2['content']
        
        # Step 3: Replace/improve the brainstorm
        result3 = manager.process_brainstorm_query('improve brainstorm for task 111025')
        
        assert result3['success'] is True
        assert result3['newly_generated'] is True
        assert 'Improved brainstorm with enhanced insights' in result3['content']
        
        # Verify file contains both brainstorms
        with open(self.brainstorm_file.name, 'r') as f:
            file_content = f.read()
        
        assert 'Initial brainstorm for TestRail' in file_content
        assert 'Improved brainstorm with enhanced insights' in file_content
        assert file_content.count('## Brainstorm: Explore weekly Automated Test coverage Sync to TestRail (111025)') == 2
        
        # Verify RAG was called multiple times
        assert mock_rag_instance.run.call_count == 2
        
        # Verify LLM was called multiple times
        assert mock_agent_instance.run.call_count == 2