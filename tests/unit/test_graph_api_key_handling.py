"""Unit tests for GraphKnowledgeManager API key handling."""
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from src.storage.graph_knowledge_manager import GraphKnowledgeManager, GRAPHITI_AVAILABLE
from src.core.exceptions import GraphDBError


class TestGraphKnowledgeManagerAPIKey:
    """Test API key handling in GraphKnowledgeManager."""
    
    @pytest.fixture
    def graph_manager_params(self):
        """Basic parameters for GraphKnowledgeManager."""
        return {
            "neo4j_uri": "bolt://localhost:7687",
            "neo4j_user": "neo4j",
            "neo4j_password": "test_password",
            "openai_api_key": "test_api_key"
        }
    
    def test_initialization_with_api_key(self, graph_manager_params):
        """Test GraphKnowledgeManager initializes with API key."""
        manager = GraphKnowledgeManager(**graph_manager_params)
        
        assert manager.neo4j_uri == graph_manager_params["neo4j_uri"]
        assert manager.neo4j_user == graph_manager_params["neo4j_user"]
        assert manager.neo4j_password == graph_manager_params["neo4j_password"]
        assert manager.openai_api_key == graph_manager_params["openai_api_key"]
        assert manager._initialized is False
    
    def test_initialization_without_api_key(self):
        """Test GraphKnowledgeManager can initialize without API key."""
        manager = GraphKnowledgeManager(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="test_password"
        )
        
        assert manager.openai_api_key is None
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not GRAPHITI_AVAILABLE, reason="Graphiti not installed")
    async def test_initialize_sets_openai_env_var(self, graph_manager_params):
        """Test that initialize() sets OPENAI_API_KEY environment variable."""
        manager = GraphKnowledgeManager(**graph_manager_params)
        
        # Mock Graphiti client
        with patch('src.storage.graph_knowledge_manager.Graphiti') as mock_graphiti:
            # Create a mock client instance
            mock_client = MagicMock()
            mock_client.driver = MagicMock()
            mock_client.build_indices_and_constraints = AsyncMock()
            mock_graphiti.return_value = mock_client
            
            # Store original env var
            original_api_key = os.environ.get("OPENAI_API_KEY")
            
            try:
                # Initialize manager
                await manager.initialize()
                
                # Check that OPENAI_API_KEY was set
                assert os.environ.get("OPENAI_API_KEY") == "test_api_key"
                
                # Verify Graphiti was initialized with correct params
                mock_graphiti.assert_called_once_with(
                    graph_manager_params["neo4j_uri"],
                    graph_manager_params["neo4j_user"],
                    graph_manager_params["neo4j_password"]
                )
                
                # Verify indices were built
                mock_client.build_indices_and_constraints.assert_called_once()
                
                # Verify manager is marked as initialized
                assert manager._initialized is True
                
            finally:
                # Restore original env var
                if original_api_key:
                    os.environ["OPENAI_API_KEY"] = original_api_key
                elif "OPENAI_API_KEY" in os.environ:
                    del os.environ["OPENAI_API_KEY"]
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not GRAPHITI_AVAILABLE, reason="Graphiti not installed")
    async def test_initialize_without_api_key_no_env_set(self):
        """Test that initialize() doesn't set env var when no API key provided."""
        manager = GraphKnowledgeManager(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="test_password"
        )
        
        with patch('src.storage.graph_knowledge_manager.Graphiti') as mock_graphiti:
            mock_client = MagicMock()
            mock_client.driver = MagicMock()
            mock_client.build_indices_and_constraints = AsyncMock()
            mock_graphiti.return_value = mock_client
            
            # Store original env var
            original_api_key = os.environ.get("OPENAI_API_KEY")
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
            
            try:
                await manager.initialize()
                
                # Check that OPENAI_API_KEY was not set
                assert "OPENAI_API_KEY" not in os.environ
                
            finally:
                # Restore original env var
                if original_api_key:
                    os.environ["OPENAI_API_KEY"] = original_api_key
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not GRAPHITI_AVAILABLE, reason="Graphiti not installed")
    async def test_initialize_handles_duplicate_index_error(self, graph_manager_params):
        """Test that initialize() handles duplicate index errors gracefully."""
        manager = GraphKnowledgeManager(**graph_manager_params)
        
        with patch('src.storage.graph_knowledge_manager.Graphiti') as mock_graphiti:
            mock_client = MagicMock()
            mock_client.driver = MagicMock()
            
            # Mock build_indices_and_constraints to raise duplicate index error
            mock_client.build_indices_and_constraints = AsyncMock(
                side_effect=Exception(
                    "{code: Neo.ClientError.Schema.EquivalentSchemaRuleAlreadyExists} "
                    "{message: An equivalent index already exists}"
                )
            )
            mock_graphiti.return_value = mock_client
            
            # Initialize should succeed despite the duplicate index error
            await manager.initialize()
            
            # Verify manager is marked as initialized
            assert manager._initialized is True
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not GRAPHITI_AVAILABLE, reason="Graphiti not installed")
    async def test_initialize_reraises_non_duplicate_errors(self, graph_manager_params):
        """Test that initialize() re-raises non-duplicate index errors."""
        manager = GraphKnowledgeManager(**graph_manager_params)
        
        with patch('src.storage.graph_knowledge_manager.Graphiti') as mock_graphiti:
            mock_client = MagicMock()
            mock_client.driver = MagicMock()
            
            # Mock build_indices_and_constraints to raise a different error
            mock_client.build_indices_and_constraints = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            mock_graphiti.return_value = mock_client
            
            # Initialize should fail with the connection error
            with pytest.raises(GraphDBError) as exc_info:
                await manager.initialize()
            
            assert "Connection refused" in str(exc_info.value)
            assert manager._initialized is False
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not GRAPHITI_AVAILABLE, reason="Graphiti not installed")
    async def test_multiple_initialize_calls_skip_reinitialization(self, graph_manager_params):
        """Test that multiple initialize() calls don't reinitialize."""
        manager = GraphKnowledgeManager(**graph_manager_params)
        
        with patch('src.storage.graph_knowledge_manager.Graphiti') as mock_graphiti:
            mock_client = MagicMock()
            mock_client.driver = MagicMock()
            mock_client.build_indices_and_constraints = AsyncMock()
            mock_graphiti.return_value = mock_client
            
            # First initialization
            await manager.initialize()
            assert manager._initialized is True
            
            # Reset the mock
            mock_graphiti.reset_mock()
            
            # Second initialization should skip
            await manager.initialize()
            
            # Graphiti should not be called again
            mock_graphiti.assert_not_called()


class TestGraphKnowledgeManagerIntegration:
    """Integration tests with filesystem and RAG agents."""
    
    @pytest.mark.asyncio
    async def test_filesystem_agent_passes_llm_api_key(self):
        """Test that filesystem agent correctly passes LLM_API_KEY."""
        from src.core.config import Settings
        
        # Mock settings with LLM_API_KEY
        mock_settings = MagicMock(spec=Settings)
        mock_settings.llm_api_key = "test_llm_key"
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j" 
        mock_settings.neo4j_password = "password"
        
        with patch('src.core.config.get_settings', return_value=mock_settings):
            with patch('src.agents.filesystem.GraphKnowledgeManager') as mock_graph_manager:
                with patch('src.agents.filesystem.get_chromadb_client'):
                    with patch('src.agents.filesystem.CollectionManager'):
                        with patch('src.agents.filesystem.get_mcp_server_manager') as mock_mcp:
                            # Mock MCP server manager
                            mock_mcp_instance = MagicMock()
                            mock_mcp_instance.get_server.return_value = MagicMock()
                            mock_mcp.return_value = mock_mcp_instance
                            
                            # Import here to trigger initialization with mocked settings
                            from src.agents.filesystem import FilesystemAgent
                            
                            model = MagicMock()
                            agent = FilesystemAgent(model)
                            
                            # Verify GraphKnowledgeManager was called with llm_api_key
                            mock_graph_manager.assert_called_with(
                                neo4j_uri="bolt://localhost:7687",
                                neo4j_user="neo4j",
                                neo4j_password="password",
                                openai_api_key="test_llm_key"
                            )
    
    @pytest.mark.asyncio
    async def test_rag_agent_passes_llm_api_key(self):
        """Test that RAG agent correctly passes LLM_API_KEY."""
        from src.core.config import Settings
        
        # Mock settings with LLM_API_KEY
        mock_settings = MagicMock(spec=Settings)
        mock_settings.llm_api_key = "test_llm_key"
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        
        with patch('src.core.config.get_settings', return_value=mock_settings):
            with patch('src.agents.rag.GraphKnowledgeManager') as mock_graph_manager:
                with patch('src.agents.rag.get_chromadb_client'):
                    with patch('src.agents.rag.CollectionManager'):
                        # Import here to trigger initialization with mocked settings
                        from src.agents.rag import RAGAgent
                        from pydantic_ai.models.openai import OpenAIModel
                        
                        model = MagicMock()
                        agent = RAGAgent(model)
                        
                        # Verify GraphKnowledgeManager was called with llm_api_key
                        mock_graph_manager.assert_called_with(
                            neo4j_uri="bolt://localhost:7687",
                            neo4j_user="neo4j",
                            neo4j_password="password",
                            openai_api_key="test_llm_key"
                        )