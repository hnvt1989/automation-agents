"""Integration tests for multi-collection ChromaDB functionality."""
import pytest
import asyncio
from pathlib import Path
from typing import Dict, List, Any
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.storage.chromadb_client import ChromaDBClient, get_chromadb_client
from src.core.exceptions import ChromaDBError


class TestMultiCollectionIntegration:
    """Integration tests for multi-collection ChromaDB functionality."""
    
    @pytest.fixture
    def temp_persist_dir(self):
        """Create a temporary directory for ChromaDB persistence."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def collection_clients(self, temp_persist_dir):
        """Create ChromaDB clients for different collections."""
        clients = {}
        collection_names = [
            "automation_agents_websites",
            "automation_agents_conversations", 
            "automation_agents_knowledge"
        ]
        
        for collection_name in collection_names:
            clients[collection_name] = ChromaDBClient(
                persist_directory=temp_persist_dir,
                collection_name=collection_name
            )
        
        return clients
    
    def test_separate_collections_isolation(self, collection_clients):
        """Test that data in different collections remains isolated."""
        # Add different data to each collection
        test_data = {
            "automation_agents_websites": {
                "documents": ["This is a website about Python programming"],
                "metadatas": [{"source_type": "website", "url": "https://python.org"}]
            },
            "automation_agents_conversations": {
                "documents": ["User: How do I use ChromaDB? Assistant: ChromaDB is a vector database"],
                "metadatas": [{"source_type": "conversation", "platform": "slack"}]
            },
            "automation_agents_knowledge": {
                "documents": ["ChromaDB is an open-source embedding database"],
                "metadatas": [{"source_type": "knowledge", "file_path": "/docs/chromadb.md"}]
            }
        }
        
        # Add data to each collection
        for collection_name, client in collection_clients.items():
            data = test_data[collection_name]
            client.add_documents(
                documents=data["documents"],
                metadatas=data["metadatas"]
            )
        
        # Query each collection and verify isolation
        query = ["ChromaDB"]
        
        # Website collection should not find the ChromaDB content
        web_results = collection_clients["automation_agents_websites"].query(query, n_results=5)
        assert len(web_results['ids'][0]) == 0 or "ChromaDB" not in web_results['documents'][0][0]
        
        # Conversation collection should find its ChromaDB content
        conv_results = collection_clients["automation_agents_conversations"].query(query, n_results=5)
        assert len(conv_results['ids'][0]) > 0
        assert "ChromaDB" in conv_results['documents'][0][0]
        
        # Knowledge collection should find its ChromaDB content
        know_results = collection_clients["automation_agents_knowledge"].query(query, n_results=5)
        assert len(know_results['ids'][0]) > 0
        assert "ChromaDB" in know_results['documents'][0][0]
    
    def test_bulk_indexing_performance(self, collection_clients):
        """Test performance of bulk indexing across collections."""
        import time
        
        # Generate test documents
        num_docs_per_collection = 100
        
        performance_metrics = {}
        
        for collection_name, client in collection_clients.items():
            documents = []
            metadatas = []
            
            # Generate documents based on collection type
            for i in range(num_docs_per_collection):
                if "websites" in collection_name:
                    doc = f"Website content {i}: This is article about topic {i}"
                    meta = {"source_type": "website", "url": f"https://example{i}.com"}
                elif "conversations" in collection_name:
                    doc = f"User: Question {i}? Assistant: Answer {i}"
                    meta = {"source_type": "conversation", "conversation_id": f"conv_{i}"}
                else:  # knowledge
                    doc = f"Knowledge document {i}: Information about subject {i}"
                    meta = {"source_type": "knowledge", "file_path": f"/docs/doc_{i}.md"}
                
                documents.append(doc)
                metadatas.append(meta)
            
            # Measure indexing time
            start_time = time.time()
            client.add_documents(documents, metadatas)
            end_time = time.time()
            
            performance_metrics[collection_name] = {
                "num_docs": num_docs_per_collection,
                "time_seconds": end_time - start_time,
                "docs_per_second": num_docs_per_collection / (end_time - start_time)
            }
        
        # Verify all collections were indexed
        for collection_name, client in collection_clients.items():
            stats = client.get_collection_stats()
            assert stats['count'] == num_docs_per_collection
        
        # Log performance metrics
        for collection, metrics in performance_metrics.items():
            print(f"\n{collection}:")
            print(f"  Indexed {metrics['num_docs']} documents in {metrics['time_seconds']:.2f}s")
            print(f"  Rate: {metrics['docs_per_second']:.2f} docs/second")
    
    def test_concurrent_collection_operations(self, temp_persist_dir):
        """Test concurrent operations on different collections."""
        collection_names = [
            "automation_agents_websites",
            "automation_agents_conversations",
            "automation_agents_knowledge"
        ]
        
        def index_and_query_collection(collection_name: str, doc_count: int):
            """Index documents and perform queries on a collection."""
            client = ChromaDBClient(
                persist_directory=temp_persist_dir,
                collection_name=collection_name
            )
            
            # Add documents
            documents = [f"Document {i} in {collection_name}" for i in range(doc_count)]
            metadatas = [{"source_type": collection_name.split('_')[-1], "doc_id": i} 
                        for i in range(doc_count)]
            
            client.add_documents(documents, metadatas)
            
            # Query documents
            results = client.query(["Document"], n_results=5)
            
            return {
                "collection": collection_name,
                "indexed": doc_count,
                "found": len(results['ids'][0])
            }
        
        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(index_and_query_collection, name, 50): name
                for name in collection_names
            }
            
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    pytest.fail(f"Concurrent operation failed: {e}")
        
        # Verify all operations completed successfully
        assert len(results) == 3
        for result in results:
            assert result['indexed'] == 50
            assert result['found'] > 0
    
    def test_cross_collection_search(self, collection_clients):
        """Test searching across multiple collections with result merging."""
        # Add diverse content to each collection
        test_content = {
            "automation_agents_websites": [
                {
                    "doc": "Machine learning is transforming web development",
                    "meta": {"source_type": "website", "url": "https://ml-web.com", "relevance": "high"}
                },
                {
                    "doc": "Python tutorials for beginners",
                    "meta": {"source_type": "website", "url": "https://python-tutorial.com"}
                }
            ],
            "automation_agents_conversations": [
                {
                    "doc": "User: What is machine learning? Assistant: Machine learning is a subset of AI",
                    "meta": {"source_type": "conversation", "platform": "slack", "relevance": "high"}
                },
                {
                    "doc": "User: How do I install Python? Assistant: You can download Python from python.org",
                    "meta": {"source_type": "conversation", "platform": "discord"}
                }
            ],
            "automation_agents_knowledge": [
                {
                    "doc": "Machine learning algorithms include supervised and unsupervised learning",
                    "meta": {"source_type": "knowledge", "file_path": "/ml-guide.md", "relevance": "high"}
                },
                {
                    "doc": "Python is a high-level programming language",
                    "meta": {"source_type": "knowledge", "file_path": "/python-intro.md"}
                }
            ]
        }
        
        # Index content
        for collection_name, client in collection_clients.items():
            content = test_content[collection_name]
            documents = [item["doc"] for item in content]
            metadatas = [item["meta"] for item in content]
            client.add_documents(documents, metadatas)
        
        # Search for "machine learning" across all collections
        query = ["machine learning"]
        all_results = []
        
        for collection_name, client in collection_clients.items():
            results = client.query(query, n_results=10)
            
            # Process results
            for i in range(len(results['ids'][0])):
                all_results.append({
                    'collection': collection_name,
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'distance': results['distances'][0][i],
                    'metadata': results['metadatas'][0][i]
                })
        
        # Sort by relevance (distance)
        all_results.sort(key=lambda x: x['distance'])
        
        # Verify we got results from multiple collections
        collections_found = set(r['collection'] for r in all_results)
        assert len(collections_found) >= 2  # Should find in at least 2 collections
        
        # Verify machine learning content is found
        ml_docs = [r for r in all_results if 'machine learning' in r['document'].lower()]
        assert len(ml_docs) >= 3  # Should find at least 3 ML-related documents
    
    def test_metadata_filtering_per_collection(self, collection_clients):
        """Test metadata filtering within specific collections."""
        # Add documents with various metadata
        for collection_name, client in collection_clients.items():
            documents = []
            metadatas = []
            
            # Add documents with different metadata attributes
            for i in range(10):
                if "websites" in collection_name:
                    doc = f"Web content {i}"
                    meta = {
                        "source_type": "website",
                        "domain": f"example{i % 3}.com",
                        "language": "en" if i % 2 == 0 else "es"
                    }
                elif "conversations" in collection_name:
                    doc = f"Conversation {i}"
                    meta = {
                        "source_type": "conversation",
                        "platform": "slack" if i % 2 == 0 else "discord",
                        "user_count": i % 3 + 1
                    }
                else:  # knowledge
                    doc = f"Knowledge {i}"
                    meta = {
                        "source_type": "knowledge",
                        "category": "technical" if i % 2 == 0 else "general",
                        "priority": "high" if i % 3 == 0 else "normal"
                    }
                
                documents.append(doc)
                metadatas.append(meta)
            
            client.add_documents(documents, metadatas)
        
        # Test filtering in website collection
        web_client = collection_clients["automation_agents_websites"]
        web_results = web_client.query(
            ["content"],
            n_results=10,
            where={"language": "en"}
        )
        # Verify only English documents are returned
        for metadata in web_results['metadatas'][0]:
            assert metadata.get('language') == 'en'
        
        # Test filtering in conversation collection
        conv_client = collection_clients["automation_agents_conversations"]
        conv_results = conv_client.query(
            ["conversation"],
            n_results=10,
            where={"platform": "slack"}
        )
        # Verify only Slack conversations are returned
        for metadata in conv_results['metadatas'][0]:
            assert metadata.get('platform') == 'slack'
        
        # Test filtering in knowledge collection
        know_client = collection_clients["automation_agents_knowledge"]
        know_results = know_client.query(
            ["knowledge"],
            n_results=10,
            where={"category": "technical"}
        )
        # Verify only technical documents are returned
        for metadata in know_results['metadatas'][0]:
            assert metadata.get('category') == 'technical'
    
    @pytest.mark.asyncio
    async def test_async_collection_operations(self, temp_persist_dir):
        """Test asynchronous operations on multiple collections."""
        collection_names = [
            "automation_agents_websites",
            "automation_agents_conversations",
            "automation_agents_knowledge"
        ]
        
        async def async_index_collection(collection_name: str):
            """Asynchronously index documents to a collection."""
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            def sync_operation():
                client = ChromaDBClient(
                    persist_directory=temp_persist_dir,
                    collection_name=collection_name
                )
                
                documents = [f"Async doc {i} for {collection_name}" for i in range(20)]
                metadatas = [{"source_type": collection_name.split('_')[-1], "async": True} 
                           for i in range(20)]
                
                client.add_documents(documents, metadatas)
                return client.get_collection_stats()
            
            return await loop.run_in_executor(None, sync_operation)
        
        # Run async operations
        tasks = [async_index_collection(name) for name in collection_names]
        results = await asyncio.gather(*tasks)
        
        # Verify all collections were indexed
        assert len(results) == 3
        for result in results:
            assert result['count'] == 20
    
    def test_collection_migration(self, temp_persist_dir):
        """Test migrating data from single collection to multiple collections."""
        # Create original single collection
        original_client = ChromaDBClient(
            persist_directory=temp_persist_dir,
            collection_name="automation_agents"
        )
        
        # Add mixed content to original collection
        mixed_documents = [
            "Website: Python programming guide",
            "Conversation: User asked about ChromaDB",
            "Knowledge: Machine learning fundamentals",
            "Website: JavaScript tutorial",
            "Conversation: Discussion about vectors",
            "Knowledge: Database optimization techniques"
        ]
        
        mixed_metadatas = [
            {"source_type": "website", "url": "https://python.org"},
            {"source_type": "conversation", "platform": "slack"},
            {"source_type": "knowledge", "file_path": "/ml-basics.md"},
            {"source_type": "website", "url": "https://js-tutorial.com"},
            {"source_type": "conversation", "platform": "discord"},
            {"source_type": "knowledge", "file_path": "/db-optimization.md"}
        ]
        
        original_client.add_documents(mixed_documents, mixed_metadatas)
        
        # Get all documents from original collection
        all_docs = original_client.get_documents(limit=1000)
        
        # Create new collections
        new_collections = {
            "website": ChromaDBClient(temp_persist_dir, "automation_agents_websites"),
            "conversation": ChromaDBClient(temp_persist_dir, "automation_agents_conversations"),
            "knowledge": ChromaDBClient(temp_persist_dir, "automation_agents_knowledge")
        }
        
        # Migrate data to appropriate collections
        for i in range(len(all_docs['ids'])):
            doc_id = all_docs['ids'][i]
            document = all_docs['documents'][i]
            metadata = all_docs['metadatas'][i]
            
            source_type = metadata.get('source_type', 'knowledge')
            
            if source_type in new_collections:
                new_collections[source_type].add_documents(
                    documents=[document],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
        
        # Verify migration
        assert new_collections['website'].get_collection_stats()['count'] == 2
        assert new_collections['conversation'].get_collection_stats()['count'] == 2
        assert new_collections['knowledge'].get_collection_stats()['count'] == 2
        
        # Verify data integrity
        web_docs = new_collections['website'].get_documents()
        for metadata in web_docs['metadatas']:
            assert metadata['source_type'] == 'website'