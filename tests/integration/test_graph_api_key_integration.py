"""Integration tests for GraphKnowledgeManager API key handling."""
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile
import shutil

from src.storage.graph_knowledge_manager import GraphKnowledgeManager, GRAPHITI_AVAILABLE
from src.core.exceptions import GraphDBError
from src.agents.filesystem import FilesystemAgent
from src.agents.rag import RAGAgent


@pytest.mark.integration
class TestGraphAPIKeyIntegration:
    """Integration tests for API key handling across the system."""
    
    @pytest.fixture
    def temp_env_file(self):
        """Create a temporary environment file."""
        temp_dir = tempfile.mkdtemp()
        env_file = os.path.join(temp_dir, "local.env")
        
        # Write test environment variables
        with open(env_file, 'w') as f:
            f.write("LLM_API_KEY=test_integration_key\n")
            f.write("NEO4J_URI=bolt://localhost:7687\n")
            f.write("NEO4J_USER=neo4j\n")
            f.write("NEO4J_PASSWORD=test_password\n")
        
        yield env_file
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not GRAPHITI_AVAILABLE, reason="Graphiti not installed")
    async def test_end_to_end_api_key_flow(self, temp_env_file):
        """Test complete flow from env file to GraphKnowledgeManager."""
        # Patch the env file path
        with patch('src.core.config.env_path', temp_env_file):
            # Force reload of settings
            import src.core.config
            src.core.config._settings = None
            
            from src.core.config import get_settings
            settings = get_settings()
            
            # Verify settings loaded correctly
            assert settings.llm_api_key == "test_integration_key"
            
            # Mock GraphKnowledgeManager to verify it receives the key
            with patch('src.storage.graph_knowledge_manager.Graphiti') as mock_graphiti:
                mock_client = MagicMock()
                mock_client.driver = MagicMock()
                mock_client.build_indices_and_constraints = AsyncMock()
                mock_graphiti.return_value = mock_client
                
                # Create and initialize GraphKnowledgeManager
                manager = GraphKnowledgeManager(
                    neo4j_uri=settings.neo4j_uri,
                    neo4j_user=settings.neo4j_user,
                    neo4j_password=settings.neo4j_password,
                    openai_api_key=settings.llm_api_key
                )
                
                # Store original env var
                original_api_key = os.environ.get("OPENAI_API_KEY")
                
                try:
                    # Initialize and verify OPENAI_API_KEY is set
                    await manager.initialize()
                    assert os.environ.get("OPENAI_API_KEY") == "test_integration_key"
                    
                finally:
                    # Restore original env var
                    if original_api_key:
                        os.environ["OPENAI_API_KEY"] = original_api_key
                    elif "OPENAI_API_KEY" in os.environ:
                        del os.environ["OPENAI_API_KEY"]
    
    @pytest.mark.asyncio
    async def test_filesystem_agent_initialization_with_env(self, temp_env_file):
        """Test FilesystemAgent initialization with environment file."""
        with patch('src.core.config.env_path', temp_env_file):
            # Force reload of settings
            import src.core.config
            src.core.config._settings = None
            
            # Mock dependencies
            with patch('src.agents.filesystem.get_chromadb_client') as mock_chromadb:
                with patch('src.agents.filesystem.GraphKnowledgeManager') as mock_graph_manager:
                    with patch('src.agents.filesystem.CollectionManager'):
                        # Set up mocks
                        mock_chromadb.return_value = MagicMock()
                        mock_graph_instance = MagicMock()
                        mock_graph_manager.return_value = mock_graph_instance
                        
                        # Create filesystem agent (this triggers initialization)
                        from pydantic_ai.models.openai import OpenAIModel
                        model = OpenAIModel("gpt-4o-mini", api_key="dummy_key")
                        agent = FilesystemAgent(model)
                        
                        # Verify GraphKnowledgeManager was initialized with LLM_API_KEY
                        mock_graph_manager.assert_called_with(
                            neo4j_uri="bolt://localhost:7687",
                            neo4j_user="neo4j",
                            neo4j_password="test_password",
                            openai_api_key="test_integration_key"
                        )
    
    @pytest.mark.asyncio
    async def test_duplicate_index_error_handling_integration(self):
        """Test that duplicate index errors are handled properly in real usage."""
        # Create a manager
        manager = GraphKnowledgeManager(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="test_password",
            openai_api_key="test_key"
        )
        
        with patch('src.storage.graph_knowledge_manager.Graphiti') as mock_graphiti:
            mock_client = MagicMock()
            mock_client.driver = MagicMock()
            
            # First call succeeds
            mock_client.build_indices_and_constraints = AsyncMock()
            mock_graphiti.return_value = mock_client
            
            # Initialize successfully
            await manager.initialize()
            assert manager._initialized is True
            
            # Reset for second manager
            manager2 = GraphKnowledgeManager(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="test_password",
                openai_api_key="test_key"
            )
            
            # Second call raises duplicate index error
            mock_client.build_indices_and_constraints = AsyncMock(
                side_effect=Exception(
                    "{code: Neo.ClientError.Schema.EquivalentSchemaRuleAlreadyExists} "
                    "{message: An equivalent index already exists, 'Index( id=5, "
                    "name='community_uuid', type='RANGE', schema=(:Community {uuid}), "
                    "indexProvider='range-1.0' )'.}"
                )
            )
            
            # Should still initialize successfully
            await manager2.initialize()
            assert manager2._initialized is True


@pytest.mark.integration
class TestGraphManagerLifecycle:
    """Test GraphKnowledgeManager lifecycle in collection manager."""
    
    @pytest.mark.asyncio
    async def test_collection_manager_handles_graph_initialization_errors(self):
        """Test that CollectionManager handles graph initialization errors gracefully."""
        from src.storage.collection_manager import CollectionManager
        
        # Create mock ChromaDB client
        mock_chromadb = MagicMock()
        
        # Create mock graph manager that fails to initialize
        mock_graph_manager = MagicMock(spec=GraphKnowledgeManager)
        mock_graph_manager.initialize = AsyncMock(
            side_effect=GraphDBError("Failed to connect to Neo4j")
        )
        
        # Create collection manager
        collection_manager = CollectionManager(
            chromadb_client=mock_chromadb,
            graph_manager=mock_graph_manager
        )
        
        # Indexing should still work even if graph fails
        with patch.object(collection_manager, '_index_to_chromadb') as mock_index:
            mock_index.return_value = (True, "Success", 5)
            
            success, message, count = await collection_manager.index_file(
                "test_file.txt",
                collection_name="knowledge_base"
            )
            
            # Should succeed with ChromaDB even if graph fails
            assert success is True
            assert count == 5
            assert "Failed to add to graph" in message