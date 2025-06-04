"""RAG (Retrieval-Augmented Generation) agent for searching indexed documents."""
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field
from pydantic_ai import RunContext
from pydantic_ai.models.openai import OpenAIModel

from src.agents.base import BaseAgent
from src.core.constants import AgentType, SYSTEM_PROMPTS
from src.storage.chromadb_client import get_chromadb_client
from src.storage.collection_manager import CollectionManager
from src.utils.logging import log_info, log_error, log_warning

# Optional graph support
try:
    from src.storage.graph_knowledge_manager import GraphKnowledgeManager
    GRAPH_SUPPORT = True
except ImportError:
    GraphKnowledgeManager = None
    GRAPH_SUPPORT = False


class RAGAgentDeps(BaseModel):
    """Dependencies for the RAG agent."""
    chromadb_client: Any = Field(default=None)
    collection_manager: Any = Field(default=None)
    graph_manager: Any = Field(default=None)
    
    class Config:
        arbitrary_types_allowed = True


class RAGAgent(BaseAgent):
    """Agent for searching through indexed documents using ChromaDB."""
    
    def __init__(self, model: OpenAIModel):
        """Initialize the RAG agent.
        
        Args:
            model: OpenAI model to use
        """
        # Initialize ChromaDB client and collection manager
        try:
            self.chromadb_client = get_chromadb_client()
            
            # Initialize graph manager if available and Neo4j is configured
            self.graph_manager = None
            if GRAPH_SUPPORT:
                try:
                    from src.core.config import get_settings
                    settings = get_settings()
                    if hasattr(settings, 'neo4j_uri') and settings.neo4j_uri:
                        self.graph_manager = GraphKnowledgeManager(
                            neo4j_uri=settings.neo4j_uri,
                            neo4j_user=settings.neo4j_user,
                            neo4j_password=settings.neo4j_password,
                            openai_api_key=settings.llm_api_key
                        )
                        log_info("RAG agent initialized with knowledge graph support")
                    else:
                        log_info("RAG agent initialized without knowledge graph (Neo4j not configured)")
                except Exception as e:
                    log_info(f"RAG agent initialized without knowledge graph: {str(e)}")
            else:
                log_info("RAG agent initialized without knowledge graph (Graphiti not installed)")
            
            # Now create CollectionManager with graph_manager
            self.collection_manager = CollectionManager(self.chromadb_client, graph_manager=self.graph_manager)
            log_info(f"RAG agent initialized with multi-collection support")
        except Exception as e:
            log_error(f"Failed to initialize ChromaDB client: {str(e)}")
            self.chromadb_client = None
            self.collection_manager = None
            self.graph_manager = None
        
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
            n_results: int = 5
        ) -> str:
            """Search the knowledge base for relevant documents.
            
            Args:
                query: Search query
                n_results: Number of results to return
                
            Returns:
                Search results as formatted string
            """
            log_info(f"Searching knowledge base for: {query}")
            
            if not ctx.deps.chromadb_client:
                return "ChromaDB client not initialized. Cannot search knowledge base."
            
            try:
                # Use collection manager if available for multi-collection search
                if hasattr(ctx.deps, 'collection_manager') and ctx.deps.collection_manager:
                    results = ctx.deps.collection_manager.search_all(
                        query=query,
                        n_results=n_results
                    )
                    
                    if not results:
                        return f"No results found for query: {query}"
                    
                    formatted_results = []
                    for i, result in enumerate(results):
                        result_text = f"**Result {i+1}** (relevance: {1-result['distance']:.2f})\n"
                        result_text += f"Collection: {result['collection'].split('_')[-1]}\n"
                        
                        # Add source info from metadata
                        metadata = result.get('metadata', {})
                        if 'source' in metadata:
                            result_text += f"Source: {metadata['source']}\n"
                        elif 'url' in metadata:
                            result_text += f"URL: {metadata['url']}\n"
                        elif 'file_path' in metadata:
                            result_text += f"File: {metadata['file_path']}\n"
                        
                        # Add document content
                        document = result['document']
                        result_text += f"Content: {document[:500]}...\n" if len(document) > 500 else f"Content: {document}\n"
                        
                        formatted_results.append(result_text)
                    
                    return "\n---\n".join(formatted_results)
                else:
                    # Fallback to single collection query
                    results = ctx.deps.chromadb_client.query(
                        query_texts=[query],
                        n_results=n_results
                    )
                    
                    # Format results
                    if not results['ids'] or not results['ids'][0]:
                        return f"No results found for query: {query}"
                    
                    formatted_results = []
                    for i, doc_id in enumerate(results['ids'][0]):
                        document = results['documents'][0][i] if results['documents'] else ""
                        metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                        distance = results['distances'][0][i] if results['distances'] else 0
                        
                        result_text = f"**Result {i+1}** (relevance: {1-distance:.2f})\n"
                        
                        # Add source info from metadata
                        if 'source' in metadata:
                            result_text += f"Source: {metadata['source']}\n"
                        
                        # Add document content
                        result_text += f"Content: {document[:500]}...\n" if len(document) > 500 else f"Content: {document}\n"
                        
                        formatted_results.append(result_text)
                    
                    return "\n---\n".join(formatted_results)
                
            except Exception as e:
                log_error(f"Error searching knowledge base: {str(e)}")
                return f"Error searching knowledge base: {str(e)}"
        
        @self.agent.tool
        async def get_collection_stats(ctx: RunContext[RAGAgentDeps]) -> str:
            """Get statistics about the knowledge base collection.
            
            Returns:
                Collection statistics as formatted string
            """
            log_info("Getting collection statistics")
            
            if not ctx.deps.chromadb_client:
                return "ChromaDB client not initialized."
            
            try:
                # Get stats from all collections if using collection manager
                if hasattr(ctx.deps, 'collection_manager') and ctx.deps.collection_manager:
                    all_stats = ctx.deps.collection_manager.get_collection_stats()
                    
                    stats_text = "Knowledge Base Statistics:\n\n"
                    total_docs = 0
                    
                    for collection_name, stats in all_stats.items():
                        if 'error' not in stats:
                            collection_type = collection_name.split('_')[-1].title()
                            stats_text += f"**{collection_type} Collection**:\n"
                            stats_text += f"- Documents: {stats['count']}\n"
                            stats_text += f"- Description: {stats['metadata'].get('description', 'N/A')}\n\n"
                            total_docs += stats['count']
                    
                    stats_text += f"**Total Documents**: {total_docs}"
                    return stats_text
                else:
                    # Fallback to single collection stats
                    stats = ctx.deps.chromadb_client.get_collection_stats()
                    
                    return f"""Knowledge Base Statistics:
- Collection Name: {stats['name']}
- Total Documents: {stats['count']}
- Embedding Function: {stats['embedding_function']}
- Metadata: {stats.get('metadata', {})}"""
                
            except Exception as e:
                log_error(f"Error getting collection stats: {str(e)}")
                return f"Error getting collection stats: {str(e)}"
        
        @self.agent.tool
        async def list_recent_documents(
            ctx: RunContext[RAGAgentDeps], 
            limit: int = 10
        ) -> str:
            """List recent documents in the knowledge base.
            
            Args:
                limit: Maximum number of documents to return
                
            Returns:
                List of recent documents as formatted string
            """
            log_info(f"Listing recent documents (limit: {limit})")
            
            if not ctx.deps.chromadb_client:
                return "ChromaDB client not initialized."
            
            try:
                # Get documents
                docs = ctx.deps.chromadb_client.get_documents(limit=limit)
                
                if not docs['ids']:
                    return "No documents found in the knowledge base."
                
                formatted_docs = []
                for i, doc_id in enumerate(docs['ids']):
                    metadata = docs['metadatas'][i] if docs['metadatas'] else {}
                    document = docs['documents'][i] if docs['documents'] else ""
                    
                    doc_text = f"**Document {i+1}**\n"
                    doc_text += f"ID: {doc_id}\n"
                    
                    if 'source' in metadata:
                        doc_text += f"Source: {metadata['source']}\n"
                    if 'indexed_at' in metadata:
                        doc_text += f"Indexed: {metadata['indexed_at']}\n"
                    
                    doc_text += f"Preview: {document[:200]}...\n" if len(document) > 200 else f"Content: {document}\n"
                    
                    formatted_docs.append(doc_text)
                
                return "\n---\n".join(formatted_docs)
                
            except Exception as e:
                log_error(f"Error listing documents: {str(e)}")
                return f"Error listing documents: {str(e)}"
        
        @self.agent.tool
        async def search_by_type(
            ctx: RunContext[RAGAgentDeps],
            query: str,
            source_types: List[str],
            n_results: int = 5
        ) -> str:
            """Search specific collection types in the knowledge base.
            
            Args:
                query: Search query
                source_types: List of source types to search (e.g., ['website', 'conversation', 'knowledge'])
                n_results: Number of results to return
                
            Returns:
                Search results as formatted string
            """
            log_info(f"Searching {source_types} for: {query}")
            
            if not hasattr(ctx.deps, 'collection_manager') or not ctx.deps.collection_manager:
                return "Collection manager not available. Cannot search by type."
            
            try:
                results = ctx.deps.collection_manager.search_by_type(
                    query=query,
                    source_types=source_types,
                    n_results=n_results
                )
                
                if not results:
                    return f"No results found in {', '.join(source_types)} for query: {query}"
                
                formatted_results = []
                for i, result in enumerate(results):
                    result_text = f"**Result {i+1}** (relevance: {1-result['distance']:.2f})\n"
                    result_text += f"Type: {result['collection'].split('_')[-1]}\n"
                    
                    # Add source info from metadata
                    metadata = result.get('metadata', {})
                    if 'url' in metadata:
                        result_text += f"URL: {metadata['url']}\n"
                    elif 'file_path' in metadata:
                        result_text += f"File: {metadata['file_path']}\n"
                    elif 'conversation_id' in metadata:
                        result_text += f"Conversation: {metadata['conversation_id']}\n"
                    
                    # Add document content
                    document = result['document']
                    result_text += f"Content: {document[:500]}...\n" if len(document) > 500 else f"Content: {document}\n"
                    
                    formatted_results.append(result_text)
                
                return "\n---\n".join(formatted_results)
                
            except Exception as e:
                log_error(f"Error searching by type: {str(e)}")
                return f"Error searching by type: {str(e)}"
        
        @self.agent.tool
        async def search_with_graph_context(
            ctx: RunContext[RAGAgentDeps],
            query: str,
            n_results: int = 10,
            use_hybrid: bool = True
        ) -> str:
            """Search using both vector search and knowledge graph for richer context.
            
            Args:
                query: Search query
                n_results: Number of results to return
                use_hybrid: Whether to use hybrid search (combines vector + graph)
                
            Returns:
                Enhanced search results with graph context
            """
            log_info(f"Searching with graph context for: {query}")
            
            if not ctx.deps.graph_manager:
                # Fallback to regular search if no graph
                return await search_knowledge_base(ctx, query, n_results)
            
            try:
                if use_hybrid:
                    # Get vector results first
                    vector_results = ctx.deps.collection_manager.search_all(
                        query=query,
                        n_results=n_results
                    )
                    
                    # Convert to ChromaDB format for hybrid search
                    chroma_format = {
                        'ids': [[r['id'] for r in vector_results]],
                        'documents': [[r['document'] for r in vector_results]],
                        'distances': [[r['distance'] for r in vector_results]],
                        'metadatas': [[r['metadata'] for r in vector_results]]
                    }
                    
                    # Perform hybrid search
                    results = await ctx.deps.graph_manager.hybrid_search(
                        query=query,
                        vector_results=chroma_format,
                        num_results=n_results
                    )
                else:
                    # Parallel vector and graph search
                    import asyncio
                    
                    vector_task = asyncio.create_task(
                        ctx.deps.collection_manager.search_all(query, n_results)
                    )
                    graph_task = asyncio.create_task(
                        ctx.deps.graph_manager.search_entities(query, num_results=n_results)
                    )
                    
                    vector_results, graph_results = await asyncio.gather(
                        vector_task, graph_task
                    )
                    
                    # Format results
                    results = []
                    
                    # Add vector results
                    for vr in vector_results[:n_results//2]:
                        results.append({
                            'type': 'vector',
                            'content': vr['document'],
                            'score': 1.0 - vr['distance'],
                            'metadata': vr['metadata']
                        })
                    
                    # Add graph results
                    for gr in graph_results[:n_results//2]:
                        results.append({
                            'type': 'graph',
                            'content': gr.fact,
                            'score': gr.relevance_score,
                            'metadata': gr.metadata
                        })
                
                # Format enhanced results
                formatted_results = []
                for i, result in enumerate(results):
                    result_text = f"**Result {i+1}** "
                    result_text += f"[{result.get('type', 'hybrid')}] "
                    result_text += f"(relevance: {result.get('score', 0):.2f})\n"
                    
                    # Add source info
                    metadata = result.get('metadata', {})
                    if 'source' in metadata:
                        result_text += f"Source: {metadata['source']}\n"
                    elif 'url' in metadata:
                        result_text += f"URL: {metadata['url']}\n"
                    
                    # Add content
                    content = result.get('content', '')
                    result_text += f"Content: {content[:500]}...\n" if len(content) > 500 else f"Content: {content}\n"
                    
                    formatted_results.append(result_text)
                
                return "\n---\n".join(formatted_results)
                
            except Exception as e:
                log_error(f"Error in graph-enhanced search: {str(e)}")
                # Fallback to regular search
                return await search_knowledge_base(ctx, query, n_results)
        
        @self.agent.tool
        async def explore_entity(
            ctx: RunContext[RAGAgentDeps],
            entity_name: str,
            max_depth: int = 2
        ) -> str:
            """Explore relationships and facts about a specific entity.
            
            Args:
                entity_name: Name of the entity to explore
                max_depth: Maximum depth for relationship traversal
                
            Returns:
                Information about the entity and its relationships
            """
            log_info(f"Exploring entity: {entity_name}")
            
            if not ctx.deps.graph_manager:
                return "Knowledge graph not available. Cannot explore entities."
            
            try:
                # Get entity relationships
                relationships = await ctx.deps.graph_manager.get_entity_relationships(
                    entity_name
                )
                
                # Find related entities
                related_entities = await ctx.deps.graph_manager.find_related_entities(
                    entity_name,
                    max_depth=max_depth
                )
                
                # Format results
                result = f"**Entity: {entity_name}**\n\n"
                
                if relationships:
                    result += f"**Relationships ({len(relationships)}):**\n"
                    for rel in relationships[:10]:  # Limit to first 10
                        result += f"- {rel.fact}\n"
                else:
                    result += "No direct relationships found.\n"
                
                result += "\n"
                
                if related_entities:
                    result += f"**Related Entities ({len(related_entities)}):**\n"
                    # Group by type
                    by_type = {}
                    for entity in related_entities:
                        entity_type = entity.entity_type
                        if entity_type not in by_type:
                            by_type[entity_type] = []
                        by_type[entity_type].append(entity.name)
                    
                    for entity_type, names in by_type.items():
                        result += f"- {entity_type.title()}: {', '.join(names[:5])}"
                        if len(names) > 5:
                            result += f" (+{len(names)-5} more)"
                        result += "\n"
                else:
                    result += "No related entities found.\n"
                
                return result
                
            except Exception as e:
                log_error(f"Error exploring entity: {str(e)}")
                return f"Error exploring entity: {str(e)}"
        
        @self.agent.tool
        async def find_connections(
            ctx: RunContext[RAGAgentDeps],
            entity1: str,
            entity2: str
        ) -> str:
            """Find connections between two entities in the knowledge graph.
            
            Args:
                entity1: First entity name
                entity2: Second entity name
                
            Returns:
                Connections and relationships between the entities
            """
            log_info(f"Finding connections between '{entity1}' and '{entity2}'")
            
            if not ctx.deps.graph_manager:
                return "Knowledge graph not available. Cannot find connections."
            
            try:
                # Search for facts mentioning both entities
                query = f"{entity1} AND {entity2}"
                results = await ctx.deps.graph_manager.search_entities(
                    query=query,
                    num_results=10
                )
                
                if results:
                    connections = f"**Connections between {entity1} and {entity2}:**\n\n"
                    for i, result in enumerate(results):
                        connections += f"{i+1}. {result.fact}\n"
                    return connections
                else:
                    # Try to find indirect connections
                    entity1_rels = await ctx.deps.graph_manager.get_entity_relationships(entity1)
                    entity2_rels = await ctx.deps.graph_manager.get_entity_relationships(entity2)
                    
                    # Find common entities
                    entity1_targets = {r.target_id for r in entity1_rels}
                    entity2_targets = {r.target_id for r in entity2_rels}
                    common = entity1_targets.intersection(entity2_targets)
                    
                    if common:
                        return f"No direct connections found, but both entities are connected through {len(common)} common entities."
                    else:
                        return f"No connections found between {entity1} and {entity2}."
                        
            except Exception as e:
                log_error(f"Error finding connections: {str(e)}")
                return f"Error finding connections: {str(e)}"
    
        @self.agent.tool
        async def contextual_search(
            ctx: RunContext[RAGAgentDeps],
            query: str,
            collection_name: str = "knowledge_base",
            n_results: int = 5,
            use_hybrid: bool = False
        ) -> str:
            """Search with contextual RAG for improved retrieval.
            
            Args:
                query: Search query
                collection_name: Collection to search (default: knowledge_base)
                n_results: Number of results to return
                use_hybrid: Whether to use hybrid search (embeddings + BM25)
                
            Returns:
                Contextually enhanced search results
            """
            log_info(f"Performing contextual search for: {query}")
            
            if not hasattr(ctx.deps, 'collection_manager') or not ctx.deps.collection_manager:
                return "Collection manager not available. Cannot perform contextual search."
            
            try:
                # Check if contextual RAG is enabled
                if not ctx.deps.collection_manager.enable_contextual:
                    # Fall back to regular search
                    return await search_knowledge_base(ctx, query, n_results)
                
                if use_hybrid:
                    # Perform hybrid contextual search
                    results = await ctx.deps.collection_manager.hybrid_contextual_search(
                        query=query,
                        collection_name=collection_name,
                        n_results=n_results
                    )
                else:
                    # Perform regular contextual search
                    results = ctx.deps.collection_manager.contextual_search(
                        query=query,
                        collection_name=collection_name,
                        n_results=n_results
                    )
                
                if not results:
                    return f"No results found for query: {query}"
                
                # Format results
                formatted_results = []
                for i, result in enumerate(results):
                    result_text = f"**Result {i+1}** (score: {result.get('score', 0):.2f})\n"
                    
                    # Add metadata info
                    metadata = result.get('metadata', {})
                    if metadata.get('has_context'):
                        result_text += "✓ Enhanced with context\n"
                    
                    if 'source' in metadata:
                        result_text += f"Source: {metadata['source']}\n"
                    elif 'url' in metadata:
                        result_text += f"URL: {metadata['url']}\n"
                    elif 'file_path' in metadata:
                        result_text += f"File: {metadata['file_path']}\n"
                    
                    # Add content
                    content = result.get('content', '')
                    
                    # If we have original text, show both contextual and original
                    if metadata.get('original_text'):
                        result_text += f"\nContext: {content[:200]}...\n"
                        result_text += f"\nOriginal: {metadata['original_text'][:300]}...\n"
                    else:
                        result_text += f"\nContent: {content[:500]}...\n" if len(content) > 500 else f"\nContent: {content}\n"
                    
                    formatted_results.append(result_text)
                
                return "\n---\n".join(formatted_results)
                
            except Exception as e:
                log_error(f"Error in contextual search: {str(e)}")
                # Fallback to regular search
                return await search_knowledge_base(ctx, query, n_results)
    
    async def run(self, prompt: str, deps: Optional[Any] = None, **kwargs) -> Any:
        """Run the RAG agent.
        
        Args:
            prompt: The user prompt
            deps: Optional dependencies (if not provided, will create default)
            **kwargs: Additional arguments
            
        Returns:
            The agent's response
        """
        if deps is None:
            deps = RAGAgentDeps(
                chromadb_client=self.chromadb_client,
                collection_manager=self.collection_manager,
                graph_manager=self.graph_manager
            )
        
        return await super().run(prompt, deps=deps, **kwargs)
    
    async def contextual_search(self, query: str, use_contextual: bool = True, **kwargs) -> Any:
        """Perform contextual search on the knowledge base.
        
        Args:
            query: Search query
            use_contextual: Whether to use contextual search (default: True)
            **kwargs: Additional search parameters
            
        Returns:
            Search results
        """
        if use_contextual and self.collection_manager and self.collection_manager.enable_contextual:
            prompt = f"use contextual search for: {query}"
        else:
            prompt = f"search knowledge base for: {query}"
        
        return await self.run(prompt, **kwargs)