"""Integration tests for analyzer agent with RAG and task creation."""
import pytest
import json
import yaml
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.agents.analyzer import AnalyzerAgent, SuggestedTask
from src.agents.rag import RAGAgent


class TestAnalyzerIntegration:
    """Integration tests for analyzer agent functionality."""
    
    @pytest.fixture
    def sample_meeting_content(self):
        """Sample meeting content for testing."""
        return """
        Team Standup Meeting - June 8, 2025
        
        Participants: Alice (PM), Bob (Dev), Charlie (QA)
        
        Discussion:
        - Alice reported that the user authentication feature is 80% complete
        - Bob mentioned he needs to review the new API endpoints before deployment
        - Charlie found 3 critical bugs in the payment system that need immediate attention
        - Team agreed to extend the sprint deadline by 3 days due to the critical bugs
        
        Action Items:
        1. Bob to complete API review by June 10
        2. Charlie to create detailed bug reports for payment issues
        3. Alice to update project timeline and communicate with stakeholders
        
        Next Steps:
        - Schedule emergency bug triage meeting for June 9
        - Deploy hotfix for payment system by June 12
        - Review sprint retrospective process
        """
    
    @pytest.fixture
    def mock_settings(self):
        """Mock application settings."""
        with patch('src.agents.analyzer.get_settings') as mock:
            mock.return_value.base_url = "https://api.openai.com/v1"
            mock.return_value.llm_api_key = "test-key"
            yield mock
    
    @pytest.fixture
    def analyzer_agent(self, mock_settings):
        """Create analyzer agent with mocked dependencies."""
        with patch('src.agents.analyzer.OpenAIProvider'), \
             patch('src.agents.analyzer.OpenAIModel'), \
             patch('src.agents.analyzer.Agent'):
            return AnalyzerAgent()
    
    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(self, analyzer_agent, sample_meeting_content):
        """Test complete workflow from meeting analysis to task creation."""
        # Mock the LLM response for analysis
        mock_analysis_response = {
            "summary": "Team discussed sprint progress, identified critical payment bugs, and adjusted timeline",
            "key_decisions": [
                "Extend sprint deadline by 3 days",
                "Prioritize payment system bug fixes"
            ],
            "action_items": [
                "Bob to complete API review by June 10",
                "Charlie to create detailed bug reports",
                "Alice to update project timeline"
            ],
            "participants": ["Alice", "Bob", "Charlie"],
            "next_steps": [
                "Schedule emergency bug triage meeting",
                "Deploy payment hotfix",
                "Review retrospective process"
            ],
            "suggested_tasks": [
                {
                    "title": "Review API endpoints for deployment",
                    "description": "Complete review of new API endpoints to ensure they meet security and performance standards",
                    "priority": "high",
                    "deadline": "2025-06-10",
                    "assignee": "Bob",
                    "category": "review",
                    "confidence": 0.95,
                    "context": "Bob mentioned need to review API endpoints before deployment"
                },
                {
                    "title": "Create payment system bug reports",
                    "description": "Document the 3 critical bugs found in payment system with detailed reproduction steps",
                    "priority": "high",
                    "deadline": "2025-06-09",
                    "assignee": "Charlie",
                    "category": "bug_report",
                    "confidence": 0.9,
                    "context": "Charlie found critical bugs requiring immediate attention"
                },
                {
                    "title": "Update project timeline and stakeholder communication",
                    "description": "Revise project timeline due to 3-day extension and communicate changes to stakeholders",
                    "priority": "medium",
                    "deadline": "2025-06-09",
                    "assignee": "Alice",
                    "category": "communication",
                    "confidence": 0.85,
                    "context": "Timeline needs updating due to sprint extension"
                }
            ],
            "confidence_score": 0.88
        }
        
        # Mock agent response
        mock_response = Mock()
        mock_response.data = json.dumps(mock_analysis_response)
        analyzer_agent.agent.run = AsyncMock(return_value=mock_response)
        
        # Mock RAG context retrieval
        mock_rag_contexts = [
            {
                'content': 'API review guidelines: Security checks must include authentication validation, input sanitization, and rate limiting verification.',
                'metadata': {'source': 'api_guidelines.md'},
                'relevance_score': 0.9
            },
            {
                'content': 'Bug reporting template: Include steps to reproduce, expected vs actual behavior, environment details, and severity assessment.',
                'metadata': {'source': 'bug_template.md'},
                'relevance_score': 0.85
            }
        ]
        
        with patch('src.agents.analyzer.get_enhanced_rag_context') as mock_rag:
            mock_rag.return_value = mock_rag_contexts
            
            # Run analysis
            result = await analyzer_agent.analyze_meeting(
                meeting_content=sample_meeting_content,
                meeting_date="2025-06-08",
                meeting_title="Team Standup"
            )
        
        # Verify analysis results
        assert result is not None
        assert result.meeting_title == "Team Standup"
        assert result.meeting_date == "2025-06-08"
        assert len(result.suggested_tasks) == 3
        assert result.confidence_score == 0.88
        
        # Verify suggested tasks
        api_review_task = next(task for task in result.suggested_tasks if "API" in task.title)
        assert api_review_task.assignee == "Bob"
        assert api_review_task.priority == "high"
        assert api_review_task.deadline == "2025-06-10"
        
        bug_report_task = next(task for task in result.suggested_tasks if "bug" in task.title.lower())
        assert bug_report_task.assignee == "Charlie"
        assert bug_report_task.category == "bug_report"
        
        # Verify RAG context was included
        assert len(result.rag_context) == 2
        assert "API review guidelines" in result.rag_context[0]
    
    @pytest.mark.asyncio
    async def test_task_enhancement_with_rag(self, analyzer_agent):
        """Test enhancing a suggested task with RAG context."""
        suggested_task = SuggestedTask(
            title="Review API endpoints for deployment",
            description="Complete review of new API endpoints",
            priority="high",
            deadline="2025-06-10",
            assignee="Bob",
            category="review",
            confidence=0.95,
            context="API review needed before deployment"
        )
        
        # Mock RAG agent response
        mock_rag_response = Mock()
        mock_rag_response.data = "API review best practices: Validate authentication, check rate limiting, verify input sanitization, test error handling, ensure proper logging."
        
        mock_rag_agent = Mock()
        mock_rag_agent.run = AsyncMock(return_value=mock_rag_response)
        
        # Mock enhancement response
        mock_enhancement_response = Mock()
        mock_enhancement_response.data = """
        Enhanced API Review Task:
        
        1. Security Validation:
           - Verify authentication mechanisms are properly implemented
           - Check that all endpoints require appropriate authorization
           - Validate input sanitization for all parameters
        
        2. Performance Testing:
           - Test rate limiting implementation
           - Verify response times meet SLA requirements
           - Check for potential bottlenecks
        
        3. Error Handling:
           - Ensure proper HTTP status codes are returned
           - Verify error messages don't expose sensitive information
           - Test edge cases and invalid inputs
        
        4. Documentation:
           - Confirm API documentation is up to date
           - Verify examples work as expected
           - Check that breaking changes are noted
        
        Success Criteria:
        - All security checks pass
        - Performance benchmarks are met
        - Error handling is comprehensive
        - Documentation is accurate and complete
        """
        
        analyzer_agent.agent.run = AsyncMock(return_value=mock_enhancement_response)
        
        with patch('src.agents.analyzer.RAGAgent') as mock_rag_class:
            mock_rag_class.return_value = mock_rag_agent
            
            result = await analyzer_agent.enhance_task_with_rag(suggested_task)
        
        assert result['success'] is True
        assert 'Security Validation' in result['enhanced_todo']
        assert 'Performance Testing' in result['enhanced_todo']
        assert 'Success Criteria' in result['enhanced_todo']
        assert len(result['rag_context']) > 0
    
    @pytest.mark.asyncio
    async def test_save_and_load_analysis(self, analyzer_agent, tmp_path):
        """Test saving and loading meeting analysis."""
        suggested_task = SuggestedTask(
            title="Test task",
            description="Test description",
            priority="medium",
            deadline="2025-06-15",
            assignee="Test User",
            category="test",
            confidence=0.8,
            context="Test context"
        )
        
        from src.agents.analyzer import MeetingAnalysis
        analysis = MeetingAnalysis(
            meeting_date="2025-06-08",
            meeting_title="Test Meeting",
            analysis_timestamp=datetime.now(),
            summary="Test meeting summary",
            key_decisions=["Test decision"],
            action_items=["Test action"],
            suggested_tasks=[suggested_task],
            next_steps=["Test step"],
            participants=["Test participant"],
            rag_context=["Test RAG context"],
            confidence_score=0.85
        )
        
        # Save analysis
        result = analyzer_agent.save_analysis(analysis, str(tmp_path))
        
        assert result['success'] is True
        filepath = result['filepath']
        assert os.path.exists(filepath)
        
        # Load and verify
        with open(filepath, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data['meeting_title'] == "Test Meeting"
        assert saved_data['confidence_score'] == 0.85
        assert len(saved_data['suggested_tasks']) == 1
        assert saved_data['suggested_tasks'][0]['title'] == "Test task"
        
        # Verify we can recreate the analysis object
        recreated_analysis = MeetingAnalysis.from_dict(saved_data)
        assert recreated_analysis.meeting_title == analysis.meeting_title
        assert len(recreated_analysis.suggested_tasks) == 1
        assert recreated_analysis.suggested_tasks[0].title == suggested_task.title
    
    @pytest.mark.asyncio
    async def test_analysis_with_no_rag_context(self, analyzer_agent, sample_meeting_content):
        """Test analysis workflow when RAG context retrieval fails."""
        mock_analysis_response = {
            "summary": "Team meeting summary",
            "key_decisions": ["Decision 1"],
            "action_items": ["Action 1"],
            "participants": ["Alice"],
            "next_steps": ["Step 1"],
            "suggested_tasks": [{
                "title": "Simple task",
                "description": "Simple description",
                "priority": "medium",
                "deadline": None,
                "assignee": None,
                "category": "action_item",
                "confidence": 0.8,
                "context": "Meeting context"
            }],
            "confidence_score": 0.75
        }
        
        mock_response = Mock()
        mock_response.data = json.dumps(mock_analysis_response)
        analyzer_agent.agent.run = AsyncMock(return_value=mock_response)
        
        # Mock RAG failure
        with patch('src.agents.analyzer.get_enhanced_rag_context') as mock_rag:
            mock_rag.side_effect = Exception("RAG service unavailable")
            
            result = await analyzer_agent.analyze_meeting(
                meeting_content=sample_meeting_content,
                meeting_date="2025-06-08",
                meeting_title="Team Meeting"
            )
        
        # Should still work without RAG context
        assert result is not None
        assert result.meeting_title == "Team Meeting"
        assert len(result.suggested_tasks) == 1
        assert len(result.rag_context) == 0  # No RAG context due to failure
    
    @pytest.mark.asyncio
    async def test_create_task_from_analysis(self, analyzer_agent):
        """Test creating actual task records from analysis results."""
        suggested_task = SuggestedTask(
            title="Implement user authentication",
            description="Add OAuth2 authentication to the user service",
            priority="high",
            deadline="2025-06-20",
            assignee="Development Team",
            category="feature",
            confidence=0.9,
            context="Discussed as critical security requirement"
        )
        
        # Mock task enhancement
        enhanced_result = {
            'success': True,
            'enhanced_todo': """
            Implement OAuth2 Authentication:
            
            1. Set up OAuth2 provider integration
            2. Create user authentication middleware
            3. Implement token validation and refresh
            4. Add proper error handling and logging
            5. Write comprehensive tests
            6. Update API documentation
            
            Acceptance Criteria:
            - Users can authenticate via OAuth2
            - Tokens are properly validated
            - Session management works correctly
            - Security best practices are followed
            """,
            'rag_context': 'OAuth2 implementation guidelines found in security documentation'
        }
        
        analyzer_agent.enhance_task_with_rag = AsyncMock(return_value=enhanced_result)
        
        # Test enhancement
        result = await analyzer_agent.enhance_task_with_rag(suggested_task)
        
        assert result['success'] is True
        assert 'OAuth2 Authentication' in result['enhanced_todo']
        assert 'Acceptance Criteria' in result['enhanced_todo']
        
        # Verify that the enhanced todo contains actionable steps
        enhanced_todo = result['enhanced_todo']
        assert '1.' in enhanced_todo  # Numbered steps
        assert 'OAuth2' in enhanced_todo
        assert 'tests' in enhanced_todo.lower()
        assert 'documentation' in enhanced_todo.lower()
    
    def test_meeting_analysis_serialization(self):
        """Test serialization and deserialization of meeting analysis."""
        suggested_task = SuggestedTask(
            title="Serialization test task",
            description="Test task for serialization",
            priority="low",
            deadline="2025-06-30",
            assignee="Test Engineer",
            category="testing",
            confidence=0.75,
            context="Testing context"
        )
        
        from src.agents.analyzer import MeetingAnalysis
        original_analysis = MeetingAnalysis(
            meeting_date="2025-06-08",
            meeting_title="Serialization Test Meeting",
            analysis_timestamp=datetime.now(),
            summary="Test summary for serialization",
            key_decisions=["Serialization decision"],
            action_items=["Serialization action"],
            suggested_tasks=[suggested_task],
            next_steps=["Serialization step"],
            participants=["Serialization participant"],
            rag_context=["Serialization RAG context"],
            confidence_score=0.92
        )
        
        # Convert to dict and back
        analysis_dict = original_analysis.to_dict()
        recreated_analysis = MeetingAnalysis.from_dict(analysis_dict)
        
        # Verify all fields are preserved
        assert recreated_analysis.meeting_date == original_analysis.meeting_date
        assert recreated_analysis.meeting_title == original_analysis.meeting_title
        assert recreated_analysis.summary == original_analysis.summary
        assert recreated_analysis.confidence_score == original_analysis.confidence_score
        assert len(recreated_analysis.suggested_tasks) == len(original_analysis.suggested_tasks)
        
        # Verify suggested task is preserved
        recreated_task = recreated_analysis.suggested_tasks[0]
        assert recreated_task.title == suggested_task.title
        assert recreated_task.assignee == suggested_task.assignee
        assert recreated_task.confidence == suggested_task.confidence