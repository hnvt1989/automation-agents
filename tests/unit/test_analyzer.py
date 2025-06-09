"""Tests for the meeting analyzer agent."""
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.agents.analyzer import (
    AnalyzerAgent, MeetingAnalysis, SuggestedTask
)


class TestSuggestedTask:
    """Test SuggestedTask dataclass."""
    
    def test_suggested_task_creation(self):
        """Test creating a SuggestedTask."""
        task = SuggestedTask(
            title="Review project requirements",
            description="Analyze the updated project requirements document",
            priority="high",
            deadline="2025-06-15",
            assignee="John Doe",
            category="review",
            confidence=0.9,
            context="Discussed in team meeting"
        )
        
        assert task.title == "Review project requirements"
        assert task.priority == "high"
        assert task.confidence == 0.9
    
    def test_suggested_task_to_dict(self):
        """Test converting SuggestedTask to dict."""
        task = SuggestedTask(
            title="Test task",
            description="Test description",
            priority="medium",
            deadline=None,
            assignee=None,
            category="action_item",
            confidence=0.8,
            context="Test context"
        )
        
        result = task.to_dict()
        
        assert result["title"] == "Test task"
        assert result["priority"] == "medium"
        assert result["deadline"] is None
        assert result["confidence"] == 0.8
    
    def test_suggested_task_from_dict(self):
        """Test creating SuggestedTask from dict."""
        data = {
            "title": "Test task",
            "description": "Test description",
            "priority": "low",
            "deadline": "2025-07-01",
            "assignee": "Jane Smith",
            "category": "follow_up",
            "confidence": 0.7,
            "context": "Test context"
        }
        
        task = SuggestedTask.from_dict(data)
        
        assert task.title == "Test task"
        assert task.priority == "low"
        assert task.deadline == "2025-07-01"
        assert task.assignee == "Jane Smith"


class TestMeetingAnalysis:
    """Test MeetingAnalysis dataclass."""
    
    def test_meeting_analysis_creation(self):
        """Test creating a MeetingAnalysis."""
        task1 = SuggestedTask(
            title="Task 1", description="Desc 1", priority="high",
            deadline=None, assignee=None, category="action_item",
            confidence=0.9, context="Context 1"
        )
        
        analysis = MeetingAnalysis(
            meeting_date="2025-06-08",
            meeting_title="Team Standup",
            analysis_timestamp=datetime.now(),
            summary="Brief meeting summary",
            key_decisions=["Decision 1", "Decision 2"],
            action_items=["Action 1", "Action 2"],
            suggested_tasks=[task1],
            next_steps=["Next step 1"],
            participants=["Alice", "Bob"],
            rag_context=["Context from RAG"],
            confidence_score=0.85
        )
        
        assert analysis.meeting_title == "Team Standup"
        assert len(analysis.suggested_tasks) == 1
        assert analysis.confidence_score == 0.85
    
    def test_meeting_analysis_to_dict(self):
        """Test converting MeetingAnalysis to dict."""
        task1 = SuggestedTask(
            title="Task 1", description="Desc 1", priority="high",
            deadline=None, assignee=None, category="action_item",
            confidence=0.9, context="Context 1"
        )
        
        timestamp = datetime.now()
        analysis = MeetingAnalysis(
            meeting_date="2025-06-08",
            meeting_title="Team Meeting",
            analysis_timestamp=timestamp,
            summary="Summary",
            key_decisions=["Decision"],
            action_items=["Action"],
            suggested_tasks=[task1],
            next_steps=["Step"],
            participants=["Person"],
            rag_context=["Context"],
            confidence_score=0.8
        )
        
        result = analysis.to_dict()
        
        assert result["meeting_title"] == "Team Meeting"
        assert result["analysis_timestamp"] == timestamp.isoformat()
        assert len(result["suggested_tasks"]) == 1
        assert result["suggested_tasks"][0]["title"] == "Task 1"
    
    def test_meeting_analysis_from_dict(self):
        """Test creating MeetingAnalysis from dict."""
        timestamp = datetime.now()
        data = {
            "meeting_date": "2025-06-08",
            "meeting_title": "Test Meeting",
            "analysis_timestamp": timestamp.isoformat(),
            "summary": "Test summary",
            "key_decisions": ["Test decision"],
            "action_items": ["Test action"],
            "suggested_tasks": [{
                "title": "Test task",
                "description": "Test desc",
                "priority": "medium",
                "deadline": None,
                "assignee": None,
                "category": "action_item",
                "confidence": 0.8,
                "context": "Test context"
            }],
            "next_steps": ["Test step"],
            "participants": ["Test person"],
            "rag_context": ["Test context"],
            "confidence_score": 0.9
        }
        
        analysis = MeetingAnalysis.from_dict(data)
        
        assert analysis.meeting_title == "Test Meeting"
        assert len(analysis.suggested_tasks) == 1
        assert analysis.suggested_tasks[0].title == "Test task"


class TestAnalyzerAgent:
    """Test AnalyzerAgent class."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        with patch('src.agents.analyzer.get_settings') as mock:
            mock.return_value.base_url = "https://api.openai.com/v1"
            mock.return_value.llm_api_key = "test-key"
            yield mock
    
    @pytest.fixture
    def analyzer_agent(self, mock_settings):
        """Create an AnalyzerAgent instance."""
        with patch('src.agents.analyzer.OpenAIProvider'), \
             patch('src.agents.analyzer.OpenAIModel'), \
             patch('src.agents.analyzer.Agent'):
            return AnalyzerAgent()
    
    @pytest.mark.asyncio
    async def test_analyze_meeting_success(self, analyzer_agent):
        """Test successful meeting analysis."""
        # Mock the agent response
        mock_response = Mock()
        mock_response.data = json.dumps({
            "summary": "Team discussed project progress and next steps",
            "key_decisions": ["Decided to extend deadline", "Approved new feature"],
            "action_items": ["Review code", "Update documentation"],
            "participants": ["Alice", "Bob", "Charlie"],
            "next_steps": ["Schedule follow-up meeting"],
            "suggested_tasks": [{
                "title": "Update project documentation",
                "description": "Update the README and API docs with latest changes",
                "priority": "high",
                "deadline": "2025-06-15",
                "assignee": "Alice",
                "category": "documentation",
                "confidence": 0.9,
                "context": "Documentation is outdated after recent changes"
            }],
            "confidence_score": 0.85
        })
        
        analyzer_agent.agent.run = AsyncMock(return_value=mock_response)
        
        # Mock RAG context retrieval
        with patch('src.agents.analyzer.get_enhanced_rag_context') as mock_rag:
            mock_rag.return_value = [{
                'content': 'Related documentation guidelines',
                'metadata': {'source': 'docs.md'},
                'relevance_score': 0.8
            }]
            
            result = await analyzer_agent.analyze_meeting(
                meeting_content="Team discussed project status and documentation needs",
                meeting_date="2025-06-08",
                meeting_title="Weekly Standup"
            )
        
        assert result is not None
        assert isinstance(result, MeetingAnalysis)
        assert result.meeting_title == "Weekly Standup"
        assert result.meeting_date == "2025-06-08"
        assert len(result.suggested_tasks) == 1
        assert result.suggested_tasks[0].title == "Update project documentation"
        assert result.confidence_score == 0.85
    
    @pytest.mark.asyncio
    async def test_analyze_meeting_invalid_json(self, analyzer_agent):
        """Test handling of invalid JSON response."""
        # Mock invalid JSON response
        mock_response = Mock()
        mock_response.data = "Invalid JSON response"
        
        analyzer_agent.agent.run = AsyncMock(return_value=mock_response)
        
        with patch('src.agents.analyzer.get_enhanced_rag_context'):
            result = await analyzer_agent.analyze_meeting(
                meeting_content="Test content",
                meeting_date="2025-06-08",
                meeting_title="Test Meeting"
            )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_analyze_meeting_no_data(self, analyzer_agent):
        """Test handling when agent returns no data."""
        # Mock no data response
        mock_response = Mock()
        mock_response.data = None
        
        analyzer_agent.agent.run = AsyncMock(return_value=mock_response)
        
        with patch('src.agents.analyzer.get_enhanced_rag_context'):
            result = await analyzer_agent.analyze_meeting(
                meeting_content="Test content",
                meeting_date="2025-06-08",
                meeting_title="Test Meeting"
            )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_analyze_meeting_rag_failure(self, analyzer_agent):
        """Test handling when RAG context retrieval fails."""
        # Mock successful agent response
        mock_response = Mock()
        mock_response.data = json.dumps({
            "summary": "Test summary",
            "key_decisions": [],
            "action_items": [],
            "participants": [],
            "next_steps": [],
            "suggested_tasks": [],
            "confidence_score": 0.7
        })
        
        analyzer_agent.agent.run = AsyncMock(return_value=mock_response)
        
        # Mock RAG failure
        with patch('src.agents.analyzer.get_enhanced_rag_context') as mock_rag:
            mock_rag.side_effect = Exception("RAG failed")
            
            result = await analyzer_agent.analyze_meeting(
                meeting_content="Test content",
                meeting_date="2025-06-08",
                meeting_title="Test Meeting"
            )
        
        assert result is not None
        assert isinstance(result, MeetingAnalysis)
        assert len(result.rag_context) == 0  # No RAG context due to failure
    
    @pytest.mark.asyncio
    async def test_enhance_task_with_rag_success(self, analyzer_agent):
        """Test successful task enhancement with RAG."""
        task = SuggestedTask(
            title="Review code",
            description="Review the new feature implementation",
            priority="high",
            deadline=None,
            assignee=None,
            category="review",
            confidence=0.8,
            context="Mentioned in standup"
        )
        
        # Mock RAG agent
        mock_rag_agent = Mock()
        mock_rag_result = Mock()
        mock_rag_result.data = "Relevant context about code review process"
        mock_rag_agent.run = AsyncMock(return_value=mock_rag_result)
        
        # Mock enhancement result
        mock_enhancement_result = Mock()
        mock_enhancement_result.data = "Enhanced description with specific steps and criteria"
        analyzer_agent.agent.run = AsyncMock(return_value=mock_enhancement_result)
        
        with patch('src.agents.analyzer.RAGAgent') as mock_rag_class:
            mock_rag_class.return_value = mock_rag_agent
            
            result = await analyzer_agent.enhance_task_with_rag(task)
        
        assert result['success'] is True
        assert 'enhanced_todo' in result
        assert 'rag_context' in result
        assert result['enhanced_todo'] == "Enhanced description with specific steps and criteria"
    
    @pytest.mark.asyncio
    async def test_enhance_task_with_rag_failure(self, analyzer_agent):
        """Test handling of task enhancement failure."""
        task = SuggestedTask(
            title="Test task",
            description="Test description",
            priority="medium",
            deadline=None,
            assignee=None,
            category="action_item",
            confidence=0.8,
            context="Test context"
        )
        
        # Mock RAG agent failure
        with patch('src.agents.analyzer.RAGAgent') as mock_rag_class:
            mock_rag_class.side_effect = Exception("RAG failed")
            
            result = await analyzer_agent.enhance_task_with_rag(task)
        
        assert result['success'] is False
        assert 'error' in result
        assert result['enhanced_todo'] == task.description  # Falls back to original
    
    def test_save_analysis_success(self, analyzer_agent, tmp_path):
        """Test successful saving of meeting analysis."""
        task = SuggestedTask(
            title="Test task",
            description="Test description",
            priority="medium",
            deadline=None,
            assignee=None,
            category="action_item",
            confidence=0.8,
            context="Test context"
        )
        
        analysis = MeetingAnalysis(
            meeting_date="2025-06-08",
            meeting_title="Test Meeting",
            analysis_timestamp=datetime.now(),
            summary="Test summary",
            key_decisions=["Decision"],
            action_items=["Action"],
            suggested_tasks=[task],
            next_steps=["Step"],
            participants=["Person"],
            rag_context=["Context"],
            confidence_score=0.8
        )
        
        result = analyzer_agent.save_analysis(analysis, str(tmp_path))
        
        assert result['success'] is True
        assert 'filepath' in result
        
        # Verify file was created
        expected_file = tmp_path / "2025-06-08_Test_Meeting_analysis.json"
        assert expected_file.exists()
        
        # Verify content
        with open(expected_file) as f:
            saved_data = json.load(f)
        
        assert saved_data['meeting_title'] == "Test Meeting"
        assert len(saved_data['suggested_tasks']) == 1
    
    def test_save_analysis_failure(self, analyzer_agent):
        """Test handling of save analysis failure."""
        task = SuggestedTask(
            title="Test task",
            description="Test description",
            priority="medium",
            deadline=None,
            assignee=None,
            category="action_item",
            confidence=0.8,
            context="Test context"
        )
        
        analysis = MeetingAnalysis(
            meeting_date="2025-06-08",
            meeting_title="Test Meeting",
            analysis_timestamp=datetime.now(),
            summary="Test summary",
            key_decisions=["Decision"],
            action_items=["Action"],
            suggested_tasks=[task],
            next_steps=["Step"],
            participants=["Person"],
            rag_context=["Context"],
            confidence_score=0.8
        )
        
        # Use invalid path to cause failure
        result = analyzer_agent.save_analysis(analysis, "/invalid/path/that/does/not/exist")
        
        assert result['success'] is False
        assert 'error' in result