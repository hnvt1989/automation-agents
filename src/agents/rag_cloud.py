"""Enhanced RAG agent with cloud support for Supabase vectors and Neo4j Aura."""

import os
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field
from pydantic_ai import RunContext
from pydantic_ai.models.openai import OpenAIModel

from src.agents.base import BaseAgent
from src.core.constants import AgentType, SYSTEM_PROMPTS
from src.utils.logging import log_info, log_error, log_warning
from src.storage.reranker import ResultReranker, RerankResult


class RAGAgentDeps(BaseModel):
    """Dependencies for the RAG agent."""
    vector_client: Any = Field(default=None)
    graph_client: Any = Field(default=None)
    
    class Config:
        arbitrary_types_allowed = True


class CloudRAGAgent(BaseAgent):
    """Enhanced RAG agent supporting both local and cloud storage."""
    
    def __init__(self, model: OpenAIModel, use_cloud: bool = True):
        """Initialize the RAG agent.
        
        Args:
            model: OpenAI model to use
            use_cloud: If True, use cloud services (Supabase/Neo4j Aura)
        """
        self.use_cloud = use_cloud
        
        # Initialize vector client
        if not os.getenv("SUPABASE_URL"):
            raise ValueError("Supabase configuration required. Please set SUPABASE_URL and SUPABASE_KEY environment variables.")
        
        from src.storage.supabase_vector import SupabaseVectorClient
        self.vector_client = SupabaseVectorClient(enable_contextual=True)
        # Disable cross-encoder by default unless sentence-transformers is installed
        self.reranker = ResultReranker(use_cross_encoder=False, use_llm_rerank=False)
        log_info("Using Supabase for vector storage with contextual RAG and reranking")
        
        # Initialize graph client
        self.graph_client = None
        if os.getenv("NEO4J_URI"):
            try:
                from src.storage.neo4j_cloud import get_neo4j_cloud_client
                self.graph_client = get_neo4j_cloud_client()
                log_info("Using Neo4j for knowledge graph")
            except Exception as e:
                log_warning(f"Failed to initialize Neo4j: {str(e)}")
        else:
            log_info("Graph operations disabled (Neo4j not configured)")
        
        # Create deps
        deps = RAGAgentDeps(
            vector_client=self.vector_client,
            graph_client=self.graph_client
        )
        
        # Initialize base agent
        super().__init__(
            name=AgentType.RAG,
            model=model,
            system_prompt=SYSTEM_PROMPTS[AgentType.RAG],
            deps_type=RAGAgentDeps
        )
        
        self._register_tools()
    
    def _register_tools(self):
        """Register tools for the RAG agent."""
        
        @self.agent.tool
        async def search_knowledge_base(
            ctx: RunContext[RAGAgentDeps],
            query: str,
            collection: Optional[str] = None,
            n_results: int = 5
        ) -> str:
            """Search through indexed documents using vector similarity.
            
            Args:
                query: Search query
                collection: Optional collection to search (default: all)
                n_results: Number of results to return
                
            Returns:
                Formatted search results
            """
            try:
                vector_client = self.vector_client
                
                # If no collection specified, search all collections
                if not collection:
                    log_info(f"Searching across all collections for: {query}")
                    all_results = []
                    
                    # Define collections to search
                    collections_to_search = ["documents", "knowledge_base", "default", "websites", "conversations"]
                    
                    for coll in collections_to_search:
                        try:
                            log_info(f"Searching collection '{coll}'...")
                            
                            if self.use_cloud:
                                # For Supabase
                                from src.storage.supabase_vector import SupabaseVectorClient
                                temp_client = SupabaseVectorClient(coll)
                                coll_results = temp_client.query([query], n_results=n_results)
                            else:
                                # For ChromaDB
                                if hasattr(vector_client, 'query_collection'):
                                    coll_results = vector_client.query_collection(coll, [query], n_results=n_results)
                                else:
                                    continue
                            
                            # Add collection info to results
                            if coll_results and coll_results.get('documents') and coll_results['documents'][0]:
                                for i, doc in enumerate(coll_results['documents'][0]):
                                    result_with_collection = {
                                        'document': doc,
                                        'metadata': coll_results.get('metadatas', [[]])[0][i] if coll_results.get('metadatas') else {},
                                        'distance': coll_results.get('distances', [[]])[0][i] if coll_results.get('distances') else 0.5,
                                        'collection': coll
                                    }
                                    all_results.append(result_with_collection)
                                log_info(f"Found {len(coll_results['documents'][0])} results in '{coll}'")
                            
                        except Exception as e:
                            log_warning(f"Failed to search collection '{coll}': {str(e)}")
                            continue
                    
                    # Sort all results by relevance
                    all_results.sort(key=lambda x: x['distance'])
                    
                    # Take top n_results
                    top_results = all_results[:n_results]
                    
                    # Format combined results
                    if not top_results:
                        return "No relevant documents found in any collection."
                    
                    # Convert to standard format
                    results = {
                        'documents': [[r['document'] for r in top_results]],
                        'metadatas': [[r['metadata'] for r in top_results]],
                        'distances': [[r['distance'] for r in top_results]]
                    }
                    
                    # Add collection info to formatted output
                    formatted_results = []
                    for i, result in enumerate(top_results):
                        score = 1 - result['distance']
                        formatted = f"\n{i+1}. **[Collection: {result['collection']}]** **Relevance Score**: {score:.2f}"
                        
                        # Add metadata if available
                        if result['metadata']:
                            if 'source' in result['metadata']:
                                formatted += f"\n   **Source**: {result['metadata']['source']}"
                            if 'title' in result['metadata']:
                                formatted += f"\n   **Title**: {result['metadata']['title']}"
                            if 'chunk_index' in result['metadata']:
                                formatted += f" (chunk {result['metadata']['chunk_index']})"
                        
                        # Add document content (truncated)
                        content = result['document'][:500] + "..." if len(result['document']) > 500 else result['document']
                        formatted += f"\n   **Content**: {content}"
                        
                        formatted_results.append(formatted)
                    
                    return f"Found {len(top_results)} relevant documents across all collections:\n" + "\n".join(formatted_results)
                    
                # Single collection search (existing code)
                elif collection and self.use_cloud:
                    # For Supabase, switch collection
                    from src.storage.supabase_vector import SupabaseVectorClient
                    vector_client = SupabaseVectorClient(collection)
                    results = vector_client.query(
                        [query],
                        n_results=n_results
                    )
                elif collection and hasattr(vector_client, 'query_collection'):
                    # For ChromaDB, use query_collection
                    results = vector_client.query_collection(
                        collection,
                        [query],
                        n_results=n_results
                    )
                else:
                    # Default query
                    results = vector_client.query(
                        [query],
                        n_results=n_results
                    )
                
                # Format results
                if not results or not results.get('documents') or not results['documents'][0]:
                    return "No relevant documents found."
                
                formatted_results = []
                documents = results['documents'][0]
                metadatas = results.get('metadatas', [[]])[0] if results.get('metadatas') else [{}] * len(documents)
                distances = results.get('distances', [[]])[0] if results.get('distances') else [0.5] * len(documents)
                
                # Ensure all lists have the same length
                max_len = len(documents)
                if len(metadatas) < max_len:
                    metadatas.extend([{}] * (max_len - len(metadatas)))
                if len(distances) < max_len:
                    distances.extend([0.5] * (max_len - len(distances)))
                
                for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
                    result = f"\n{i+1}. **Relevance Score**: {1 - distance:.2f}"
                    
                    # Add metadata if available
                    if metadata:
                        if 'source' in metadata:
                            result += f"\n   **Source**: {metadata['source']}"
                        if 'title' in metadata:
                            result += f"\n   **Title**: {metadata['title']}"
                        if 'chunk_index' in metadata:
                            result += f" (chunk {metadata['chunk_index']})"
                    
                    # Add document content (truncated)
                    content = doc[:500] + "..." if len(doc) > 500 else doc
                    result += f"\n   **Content**: {content}"
                    
                    formatted_results.append(result)
                
                return f"Found {len(formatted_results)} relevant documents:\n" + "\n".join(formatted_results)
                
            except Exception as e:
                log_error(f"Search error: {str(e)}")
                return f"Error searching knowledge base: {str(e)}"
        
        @self.agent.tool
        async def hybrid_search(
            ctx: RunContext[RAGAgentDeps],
            query: str,
            collection: Optional[str] = None,
            n_results: int = 5,
            alpha: float = 0.7,
            use_reranking: bool = True
        ) -> str:
            """Perform hybrid search combining vector and full-text search.
            
            Args:
                query: Search query
                collection: Optional collection to search
                n_results: Number of results to return
                alpha: Weight for vector search (1-alpha for text search)
                use_reranking: Whether to apply reranking
                
            Returns:
                Formatted search results
            """
            try:
                log_info(f"Performing hybrid search for: {query}")
                
                # Get appropriate vector client
                if collection and self.use_cloud:
                    from src.storage.supabase_vector import SupabaseVectorClient
                    vector_client = SupabaseVectorClient(collection, enable_contextual=True)
                else:
                    vector_client = self.vector_client
                
                # Perform hybrid search
                results = vector_client.hybrid_search(
                    query=query,
                    n_results=n_results * 2 if use_reranking else n_results,
                    alpha=alpha
                )
                
                if not results or not results.get('documents') or not results['documents'][0]:
                    return "No relevant documents found."
                
                # Prepare results for reranking
                search_results = []
                documents = results['documents'][0]
                metadatas = results.get('metadatas', [[]])[0]
                distances = results.get('distances', [[]])[0]
                
                for i, doc in enumerate(documents):
                    search_results.append({
                        'content': doc,
                        'metadata': metadatas[i] if i < len(metadatas) else {},
                        'score': 1 - distances[i] if i < len(distances) else 0.5
                    })
                
                # Apply reranking if enabled
                if use_reranking and self.reranker:
                    reranked = await self.reranker.rerank_results(
                        query=query,
                        results=search_results,
                        top_k=n_results
                    )
                    
                    # Format reranked results
                    formatted_results = []
                    for i, result in enumerate(reranked):
                        formatted = f"\n{i+1}. **Combined Score**: {result.combined_score:.3f}"
                        formatted += f" (Vector: {result.original_score:.2f}, Rerank: {result.rerank_score:.2f})"
                        
                        if result.metadata:
                            if 'source' in result.metadata:
                                formatted += f"\n   **Source**: {result.metadata['source']}"
                            if 'has_context' in result.metadata:
                                formatted += " ✓ Contextual"
                        
                        content = result.content[:500] + "..." if len(result.content) > 500 else result.content
                        formatted += f"\n   **Content**: {content}"
                        
                        formatted_results.append(formatted)
                    
                    return f"Found {len(formatted_results)} relevant documents (hybrid search + reranking):\n" + "\n".join(formatted_results)
                else:
                    # Format without reranking
                    formatted_results = []
                    for i, result in enumerate(search_results[:n_results]):
                        formatted = f"\n{i+1}. **Score**: {result['score']:.2f}"
                        
                        metadata = result['metadata']
                        if metadata:
                            if 'source' in metadata:
                                formatted += f"\n   **Source**: {metadata['source']}"
                            if 'has_context' in metadata:
                                formatted += " ✓ Contextual"
                        
                        content = result['content'][:500] + "..." if len(result['content']) > 500 else result['content']
                        formatted += f"\n   **Content**: {content}"
                        
                        formatted_results.append(formatted)
                    
                    return f"Found {len(formatted_results)} relevant documents (hybrid search):\n" + "\n".join(formatted_results)
                    
            except Exception as e:
                log_error(f"Hybrid search error: {str(e)}")
                # Fallback to regular search
                return await search_knowledge_base(ctx, query, n_results)
        
        @self.agent.tool
        async def add_document_with_context(
            ctx: RunContext[RAGAgentDeps],
            content: str,
            metadata: Optional[Dict[str, Any]] = None,
            collection: str = "default",
            use_llm_context: bool = False
        ) -> str:
            """Add a document with contextual chunking.
            
            Args:
                content: Document content
                metadata: Document metadata
                collection: Collection to add to
                use_llm_context: Whether to use LLM for context generation
                
            Returns:
                Success message
            """
            try:
                if self.use_cloud:
                    from src.storage.supabase_vector import SupabaseVectorClient
                    vector_client = SupabaseVectorClient(collection, enable_contextual=True)
                else:
                    vector_client = self.vector_client
                
                # Prepare context info
                context_info = metadata.copy() if metadata else {}
                context_info['source_type'] = context_info.get('source_type', 'document')
                
                # Add with contextual chunking
                doc_ids = vector_client.add_documents_with_context(
                    content=content,
                    context_info=context_info,
                    use_llm_context=use_llm_context
                )
                
                return f"Successfully added document with {len(doc_ids)} contextual chunks to collection '{collection}'."
                
            except Exception as e:
                log_error(f"Error adding contextual document: {str(e)}")
                return f"Error adding document: {str(e)}"
        
        @self.agent.tool
        async def list_collections(ctx: RunContext[RAGAgentDeps]) -> str:
            """List available collections in the knowledge base."""
            try:
                if self.use_cloud:
                    # For Supabase, query collection stats
                    from src.storage.supabase_client import get_supabase_client
                    client = get_supabase_client()
                    result = client.client.rpc("get_collection_stats").execute()
                    
                    if result.data:
                        collections = []
                        for stat in result.data:
                            collections.append(
                                f"- **{stat['collection_name']}**: "
                                f"{stat['document_count']} documents "
                                f"(avg {stat['avg_content_length']:.0f} chars)"
                            )
                        return "Available collections:\n" + "\n".join(collections)
                    else:
                        return "No collections found."
                else:
                    # For ChromaDB
                    collections = self.vector_client.client.list_collections()
                    if collections:
                        collection_info = []
                        for coll in collections:
                            count = coll.count()
                            collection_info.append(f"- **{coll.name}**: {count} documents")
                        return "Available collections:\n" + "\n".join(collection_info)
                    else:
                        return "No collections found."
                        
            except Exception as e:
                log_error(f"Error listing collections: {str(e)}")
                return f"Error listing collections: {str(e)}"
        
        @self.agent.tool
        async def search_knowledge_graph(
            ctx: RunContext[RAGAgentDeps],
            query: str,
            entity_type: Optional[str] = None,
            limit: int = 10
        ) -> str:
            """Search the knowledge graph for entities and relationships.
            
            Args:
                query: Search query
                entity_type: Optional entity type filter
                limit: Maximum results
                
            Returns:
                Formatted graph search results
            """
            if not self.graph_client:
                return "Knowledge graph is not available."
            
            try:
                if self.use_cloud:
                    # Use Neo4j cloud client
                    results = self.graph_client.search_entities(query, limit=limit)
                    
                    if not results:
                        return f"No entities found matching '{query}'."
                    
                    formatted_results = []
                    for i, result in enumerate(results):
                        entity = result['entity']
                        labels = result.get('labels', [])
                        
                        info = f"\n{i+1}. **Entity**: {entity.get('name', entity.get('id', 'Unknown'))}"
                        info += f"\n   **Type**: {', '.join(labels)}"
                        
                        # Add key properties
                        for key, value in entity.items():
                            if key not in ['id', 'name'] and value:
                                info += f"\n   **{key.title()}**: {value}"
                        
                        formatted_results.append(info)
                    
                    return f"Found {len(results)} entities:\n" + "\n".join(formatted_results)
                else:
                    # Use local graph manager
                    results = self.graph_client.search_entities(query, limit=limit)
                    # Format similarly
                    return self._format_graph_results(results)
                    
            except Exception as e:
                log_error(f"Graph search error: {str(e)}")
                return f"Error searching knowledge graph: {str(e)}"
        
        @self.agent.tool
        async def get_entity_relationships(
            ctx: RunContext[RAGAgentDeps],
            entity_id: str,
            relationship_type: Optional[str] = None
        ) -> str:
            """Get relationships for a specific entity.
            
            Args:
                entity_id: ID of the entity
                relationship_type: Optional filter by relationship type
                
            Returns:
                Formatted relationship information
            """
            if not self.graph_client:
                return "Knowledge graph is not available."
            
            try:
                results = self.graph_client.find_related(
                    entity_id,
                    relationship_type=relationship_type
                )
                
                if not results:
                    return f"No relationships found for entity '{entity_id}'."
                
                formatted_results = []
                for result in results:
                    related = result['entity']
                    rel_type = result['relationship_type']
                    
                    info = f"- **{rel_type}** → {related.get('name', related.get('id', 'Unknown'))}"
                    if 'description' in related:
                        info += f"\n  {related['description']}"
                    
                    formatted_results.append(info)
                
                return f"Relationships for '{entity_id}':\n" + "\n".join(formatted_results)
                
            except Exception as e:
                log_error(f"Error getting relationships: {str(e)}")
                return f"Error getting relationships: {str(e)}"
        
        @self.agent.tool
        async def add_to_knowledge_base(
            ctx: RunContext[RAGAgentDeps],
            content: str,
            metadata: Optional[Dict[str, Any]] = None,
            collection: str = "default"
        ) -> str:
            """Add new content to the knowledge base.
            
            Args:
                content: Content to add
                metadata: Optional metadata
                collection: Collection to add to
                
            Returns:
                Success message
            """
            try:
                if self.use_cloud:
                    from src.storage.supabase_vector import SupabaseVectorClient
                    vector_client = SupabaseVectorClient(collection)
                else:
                    vector_client = self.vector_client
                
                # Chunk content if it's long
                chunks = vector_client.chunk_text(content)
                
                # Add chunks with metadata
                metadatas = []
                for i, chunk in enumerate(chunks):
                    chunk_metadata = metadata.copy() if metadata else {}
                    chunk_metadata['chunk_index'] = i
                    chunk_metadata['total_chunks'] = len(chunks)
                    metadatas.append(chunk_metadata)
                
                vector_client.add_documents(chunks, metadatas=metadatas)
                
                return f"Successfully added {len(chunks)} chunks to collection '{collection}'."
                
            except Exception as e:
                log_error(f"Error adding to knowledge base: {str(e)}")
                return f"Error adding to knowledge base: {str(e)}"
        
        @self.agent.tool
        async def get_storage_info(ctx: RunContext[RAGAgentDeps]) -> str:
            """Get information about current storage configuration."""
            info = []
            
            # Vector storage info
            if self.use_cloud:
                info.append("**Vector Storage**: Supabase pgvector")
                info.append("**Embedding Model**: OpenAI text-embedding-ada-002")
            else:
                info.append("**Vector Storage**: ChromaDB (local)")
                info.append("**Embedding Model**: OpenAI text-embedding-ada-002")
            
            # Get stats
            try:
                stats = self.vector_client.get_collection_stats()
                info.append(f"**Documents**: {stats.get('count', 0)}")
            except:
                pass
            
            # Graph storage info
            if self.graph_client:
                if self.use_cloud:
                    info.append("**Knowledge Graph**: Neo4j Aura (cloud)")
                else:
                    info.append("**Knowledge Graph**: Neo4j (local)")
                
                try:
                    summary = self.graph_client.get_graph_summary()
                    info.append(f"**Nodes**: {summary.get('node_count', 0)}")
                    info.append(f"**Relationships**: {summary.get('relationship_count', 0)}")
                except:
                    pass
            else:
                info.append("**Knowledge Graph**: Not configured")
            
            return "\n".join(info)
    
    def _format_graph_results(self, results: List[Dict]) -> str:
        """Format graph search results."""
        if not results:
            return "No results found."
        
        formatted = []
        for i, result in enumerate(results[:10]):
            info = f"{i+1}. {result.get('name', result.get('id', 'Unknown'))}"
            if 'type' in result:
                info += f" ({result['type']})"
            if 'description' in result:
                info += f"\n   {result['description']}"
            formatted.append(info)
        
        return "\n".join(formatted)