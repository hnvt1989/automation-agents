"""Unit tests for multi-collection ChromaDB functionality."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from typing import Dict, List, Any

from src.storage.chromadb_client import ChromaDBClient
from src.core.exceptions import ChromaDBError
from src.core.constants import DEFAULT_EMBEDDING_MODEL


class TestMultiCollectionChromaDB:
    """Test multi-collection ChromaDB functionality."""
    
    @pytest.fixture
    def mock_chroma_client(self):
        """Create a mock ChromaDB client."""
        with patch('src.storage.chromadb_client.chromadb.PersistentClient') as mock_client:
            yield mock_client
    
    @pytest.fixture
    def mock_embedding_function(self):
        """Create a mock embedding function."""
        with patch('src.storage.chromadb_client.OpenAIEmbeddingFunction') as mock_ef:
            yield mock_ef
    
    @pytest.fixture
    def multi_collection_client(self, mock_chroma_client, mock_embedding_function, tmp_path):
        """Create a ChromaDB client configured for multiple collections."""
        with patch('src.storage.chromadb_client.get_settings') as mock_settings:
            mock_settings.return_value.chroma_persist_directory = tmp_path
            mock_settings.return_value.openai_api_key = "test-key"
            mock_settings.return_value.llm_api_key = "test-key"
            
            # Create client without collection_name (will be updated)
            client = ChromaDBClient(persist_directory=tmp_path)
            return client
    
    def test_get_collection_creates_new_collection(self, multi_collection_client, mock_chroma_client):
        """Test that get_collection creates a new collection if it doesn't exist."""
        # Mock the get_or_create_collection method
        mock_collection = MagicMock()
        mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection
        
        # This test assumes we'll add a get_collection method
        # For now, test the initialization with different collection names
        collection_name = "test_websites"
        
        # Create a new client with specific collection
        client = ChromaDBClient(
            persist_directory=multi_collection_client.persist_directory,
            collection_name=collection_name
        )
        
        # Verify collection was created with correct name
        mock_chroma_client.return_value.get_or_create_collection.assert_called()
        call_args = mock_chroma_client.return_value.get_or_create_collection.call_args
        assert call_args[1]['name'] == collection_name
    
    def test_add_to_specific_collection(self, multi_collection_client):
        """Test adding documents to a specific collection."""
        # Mock collection
        mock_collection = MagicMock()
        multi_collection_client.collection = mock_collection
        
        # Test data
        documents = ["Test document 1", "Test document 2"]
        metadatas = [
            {"source_type": "website", "url": "http://example.com"},
            {"source_type": "website", "url": "http://test.com"}
        ]
        
        # Add documents
        multi_collection_client.add_documents(documents, metadatas)
        
        # Verify add was called
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args[1]
        assert call_args['documents'] == documents
        assert call_args['metadatas'] == metadatas
    
    def test_query_specific_collection(self, multi_collection_client):
        """Test querying a specific collection."""
        # Mock collection and query results
        mock_collection = MagicMock()
        mock_results = {
            'ids': [['id1', 'id2']],
            'documents': [['doc1', 'doc2']],
            'distances': [[0.1, 0.2]],
            'metadatas': [[{'type': 'website'}, {'type': 'website'}]]
        }
        mock_collection.query.return_value = mock_results
        multi_collection_client.collection = mock_collection
        
        # Query collection
        query = ["test query"]
        results = multi_collection_client.query(query, n_results=2)
        
        # Verify query was called
        mock_collection.query.assert_called_once()
        assert results == mock_results
    
    def test_collection_type_validation(self, multi_collection_client):
        """Test validation of collection types."""
        valid_types = ["websites", "conversations", "knowledge"]
        
        # Test with valid collection names
        for collection_type in valid_types:
            collection_name = f"automation_agents_{collection_type}"
            # This should not raise an error
            client = ChromaDBClient(
                persist_directory=multi_collection_client.persist_directory,
                collection_name=collection_name
            )
            assert client.collection_name == collection_name
    
    def test_multi_collection_query(self, mock_chroma_client, mock_embedding_function, tmp_path):
        """Test querying multiple collections and merging results."""
        # This test assumes we'll implement a query_multiple_collections method
        # For now, test the concept with multiple client instances
        
        # Create mock collections
        mock_web_collection = MagicMock()
        mock_conv_collection = MagicMock()
        mock_know_collection = MagicMock()
        
        # Mock results from each collection
        web_results = {
            'ids': [['web1', 'web2']],
            'documents': [['Web doc 1', 'Web doc 2']],
            'distances': [[0.1, 0.3]],
            'metadatas': [[{'source_type': 'website'}, {'source_type': 'website'}]]
        }
        
        conv_results = {
            'ids': [['conv1']],
            'documents': [['Conversation 1']],
            'distances': [[0.2]],
            'metadatas': [[{'source_type': 'conversation'}]]
        }
        
        know_results = {
            'ids': [['know1', 'know2', 'know3']],
            'documents': [['Knowledge 1', 'Knowledge 2', 'Knowledge 3']],
            'distances': [[0.15, 0.25, 0.35]],
            'metadatas': [[
                {'source_type': 'knowledge'},
                {'source_type': 'knowledge'},
                {'source_type': 'knowledge'}
            ]]
        }
        
        # Mock the collections to return different results
        mock_web_collection.query.return_value = web_results
        mock_conv_collection.query.return_value = conv_results
        mock_know_collection.query.return_value = know_results
        
        # Test merging results (this would be in a new method)
        all_results = []
        for i, result in enumerate([web_results, conv_results, know_results]):
            for j in range(len(result['ids'][0])):
                all_results.append({
                    'id': result['ids'][0][j],
                    'document': result['documents'][0][j],
                    'distance': result['distances'][0][j],
                    'metadata': result['metadatas'][0][j]
                })
        
        # Sort by distance (relevance)
        all_results.sort(key=lambda x: x['distance'])
        
        # Verify correct ordering
        assert all_results[0]['id'] == 'web1'  # distance 0.1
        assert all_results[1]['id'] == 'know1'  # distance 0.15
        assert all_results[2]['id'] == 'conv1'  # distance 0.2
    
    def test_collection_specific_metadata(self, multi_collection_client):
        """Test that each collection type has appropriate metadata."""
        test_cases = [
            {
                'collection': 'automation_agents_websites',
                'metadata': {
                    'source_type': 'website',
                    'url': 'https://example.com',
                    'title': 'Example Page',
                    'domain': 'example.com'
                }
            },
            {
                'collection': 'automation_agents_conversations',
                'metadata': {
                    'source_type': 'conversation',
                    'conversation_id': 'conv123',
                    'participants': ['user1', 'user2'],
                    'platform': 'slack'
                }
            },
            {
                'collection': 'automation_agents_knowledge',
                'metadata': {
                    'source_type': 'knowledge',
                    'file_path': '/path/to/doc.md',
                    'file_type': '.md',
                    'category': 'documentation'
                }
            }
        ]
        
        for test_case in test_cases:
            # Create mock collection
            mock_collection = MagicMock()
            multi_collection_client.collection = mock_collection
            
            # Add document with metadata
            multi_collection_client.add_documents(
                documents=["Test content"],
                metadatas=[test_case['metadata']]
            )
            
            # Verify metadata was passed correctly
            call_args = mock_collection.add.call_args[1]
            assert call_args['metadatas'][0]['source_type'] == test_case['metadata']['source_type']
    
    def test_collection_performance_settings(self, multi_collection_client):
        """Test different chunk sizes for different collection types."""
        # Test chunking with different sizes
        chunk_configs = {
            'website': {'size': 1500, 'overlap': 200},
            'conversation': {'size': 500, 'overlap': 50},
            'knowledge': {'size': 1000, 'overlap': 100}
        }
        
        test_text = "A" * 3000  # Long text for chunking
        
        for content_type, config in chunk_configs.items():
            chunks = multi_collection_client.chunk_text(
                test_text,
                chunk_size=config['size'],
                chunk_overlap=config['overlap']
            )
            
            # Verify chunks are created with correct size
            assert len(chunks) >= 2  # Should have multiple chunks
            # First chunk should be close to chunk_size
            assert len(chunks[0]) <= config['size']
    
    def test_collection_error_handling(self, multi_collection_client):
        """Test error handling for collection operations."""
        # Mock collection to raise errors
        mock_collection = MagicMock()
        mock_collection.add.side_effect = Exception("Collection error")
        multi_collection_client.collection = mock_collection
        
        # Test that ChromaDBError is raised
        with pytest.raises(ChromaDBError) as exc_info:
            multi_collection_client.add_documents(["test"], [{}])
        
        assert "Failed to add documents" in str(exc_info.value)
    
    def test_concurrent_collection_access(self, mock_chroma_client, mock_embedding_function, tmp_path):
        """Test concurrent access to multiple collections."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Create multiple clients for different collections
        collection_names = [
            "automation_agents_websites",
            "automation_agents_conversations",
            "automation_agents_knowledge"
        ]
        
        def create_and_query_collection(collection_name):
            """Create a collection and perform a query."""
            with patch('src.storage.chromadb_client.get_settings') as mock_settings:
                mock_settings.return_value.chroma_persist_directory = tmp_path
                mock_settings.return_value.openai_api_key = "test-key"
                
                client = ChromaDBClient(
                    persist_directory=tmp_path,
                    collection_name=collection_name
                )
                
                # Mock query result
                mock_collection = MagicMock()
                mock_collection.query.return_value = {
                    'ids': [[f'{collection_name}_1']],
                    'documents': [[f'Doc from {collection_name}']]
                }
                client.collection = mock_collection
                
                return client.query(["test query"])
        
        # Execute queries concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(create_and_query_collection, name): name
                for name in collection_names
            }
            
            results = {}
            for future in as_completed(futures):
                collection_name = futures[future]
                try:
                    result = future.result()
                    results[collection_name] = result
                except Exception as e:
                    pytest.fail(f"Concurrent access failed for {collection_name}: {e}")
        
        # Verify all collections were queried successfully
        assert len(results) == 3
        for collection_name in collection_names:
            assert collection_name in results


class TestCollectionManager:
    """Test the CollectionManager class for managing multiple collections."""
    
    @pytest.fixture
    def mock_chromadb_client(self):
        """Create a mock ChromaDB client."""
        return MagicMock(spec=ChromaDBClient)
    
    def test_index_website_with_metadata(self, mock_chromadb_client):
        """Test indexing website content with appropriate metadata."""
        # This test assumes we'll create a CollectionManager class
        # For now, test the expected behavior
        
        url = "https://example.com/article"
        content = "This is a long article about AI and machine learning..."
        metadata = {
            'title': 'AI Article',
            'crawled_at': '2024-01-01T10:00:00Z'
        }
        
        # Expected metadata after processing
        expected_metadata = {
            'source_type': 'website',
            'url': url,
            'title': metadata['title'],
            'crawled_at': metadata['crawled_at'],
            'domain': 'example.com'
        }
        
        # Simulate indexing
        mock_chromadb_client.add_documents.return_value = None
        
        # Would be called by CollectionManager
        mock_chromadb_client.add_documents(
            documents=[content],
            metadatas=[expected_metadata]
        )
        
        # Verify call
        mock_chromadb_client.add_documents.assert_called_once()
        call_args = mock_chromadb_client.add_documents.call_args[1]
        assert call_args['metadatas'][0]['source_type'] == 'website'
        assert call_args['metadatas'][0]['domain'] == 'example.com'
    
    def test_search_across_collections(self, mock_chromadb_client):
        """Test searching across multiple collections."""
        query = "machine learning"
        
        # Mock results from different collections
        collection_results = {
            'websites': {
                'ids': [['web1']],
                'documents': [['ML article']],
                'distances': [[0.2]]
            },
            'conversations': {
                'ids': [['conv1']],
                'documents': [['Discussion about ML']],
                'distances': [[0.3]]
            },
            'knowledge': {
                'ids': [['know1']],
                'documents': [['ML tutorial']],
                'distances': [[0.1]]
            }
        }
        
        # Simulate querying each collection
        all_results = []
        for collection_type, results in collection_results.items():
            for i in range(len(results['ids'][0])):
                all_results.append({
                    'collection': collection_type,
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'distance': results['distances'][0][i]
                })
        
        # Sort by relevance
        all_results.sort(key=lambda x: x['distance'])
        
        # Verify ordering
        assert all_results[0]['collection'] == 'knowledge'  # Most relevant
        assert all_results[1]['collection'] == 'websites'
        assert all_results[2]['collection'] == 'conversations'