"""RAG (Retrieval-Augmented Generation) agent for searching indexed documents."""
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field
from pydantic_ai import RunContext
from pydantic_ai.models.openai import OpenAIModel

from src.agents.base import BaseAgent
from src.core.constants import AgentType, SYSTEM_PROMPTS
from src.storage.chromadb_client import get_chromadb_client
from src.utils.logging import log_info, log_error, log_warning


class RAGAgentDeps(BaseModel):
    """Dependencies for the RAG agent."""
    chromadb_client: Any = Field(default=None)
    
    class Config:
        arbitrary_types_allowed = True


class RAGAgent(BaseAgent):
    """Agent for searching through indexed documents using ChromaDB."""
    
    def __init__(self, model: OpenAIModel):
        """Initialize the RAG agent.
        
        Args:
            model: OpenAI model to use
        """
        # Initialize ChromaDB client
        try:
            self.chromadb_client = get_chromadb_client()
            log_info(f"RAG agent initialized with collection: {self.chromadb_client.collection_name}")
        except Exception as e:
            log_error(f"Failed to initialize ChromaDB client: {str(e)}")
            self.chromadb_client = None
        
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
                # Query the collection
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
                chromadb_client=self.chromadb_client
            )
        
        return await super().run(prompt, deps=deps, **kwargs)