from __future__ import annotations
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from rich.markdown import Markdown
from rich.console import Console
from rich.live import Live

from src.log_utils import log_info, log_warning, log_error
from src.planner_agent import PlannerAgent
import asyncio
import os
import pathlib
import mimetypes
from pathlib import Path

from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai import Agent, RunContext
from chromadb import Client, Settings
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import json

from src.crawler import run_crawler # Added import for the crawler
from src.image_processor import run_image_processor, extract_text_from_image, parse_conversation_from_text, process_conversation_and_index # Added import for the image processor

# Removed incorrect relative import: from . import get_model

load_dotenv('local.env')

# ========== Helper function to get model configuration ==========
def get_model():
    llm = os.getenv('MODEL_CHOICE', 'gpt-4o-mini') # Defaulting to gpt-4o-mini as seen in README
    base_url = os.getenv('BASE_URL', 'https://api.openai.com/v1')
    api_key = os.getenv('LLM_API_KEY', 'no-api-key-provided')

    log_info(f"Using {llm} model with base URL: {base_url}")
    return OpenAIModel(llm, provider=OpenAIProvider(base_url=base_url, api_key=api_key))

# ========== Set up MCP servers for each service ==========

# Brave Search MCP server
brave_server = MCPServerStdio(
    'npx', ['-y', '@modelcontextprotocol/server-brave-search'],
    env={"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")}
)

# Filesystem MCP server
filesystem_server = MCPServerStdio(
    'npx', ['-y', '@modelcontextprotocol/server-filesystem', os.getenv("LOCAL_FILE_DIR"), os.getenv("LOCAL_FILE_DIR_KNOWLEDGE_BASE")]
)

# GitHub MCP server
github_server = MCPServerStdio(
    'npx', ['-y', '@modelcontextprotocol/server-github'],
    env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN")}
)

# Slack MCP server
slack_server = MCPServerStdio(
    'npx', ['-y', '@modelcontextprotocol/server-slack'],
    env={
        "SLACK_BOT_TOKEN": os.getenv("SLACK_BOT_TOKEN"),
        "SLACK_TEAM_ID": os.getenv("SLACK_TEAM_ID")
    }
)

# ========== Create subagents with their MCP servers ==========

# Brave search agent
brave_agent = Agent(
    get_model(),
    system_prompt="You are a web search specialist using Brave Search. Find relevant information on the web.",
    mcp_servers=[brave_server],
    instrument=False
)

# Filesystem agent
filesystem_agent = Agent(
    get_model(),
    system_prompt="You are a filesystem specialist. Help users manage their files and directories.",
    mcp_servers=[filesystem_server],
    instrument=False
)

analyzer_agent = Agent(
    get_model(),
    system_prompt="You are a test report analyzer. Help users analyze their test reports.",
    #mcp_servers=[analyzer_server],
    instrument=False
)

# GitHub agent
github_agent = Agent(
    get_model(),
    system_prompt="You are a GitHub specialist. Help users interact with GitHub repositories and features.",
    mcp_servers=[github_server],
    instrument=False
)

# Slack agent
slack_agent = Agent(
    get_model(),
    system_prompt="You are a Slack specialist. Help users interact with Slack workspaces and channels.",
    mcp_servers=[slack_server],
    instrument=False
)

# Planner agent
planner_agent_core = PlannerAgent()
planner_agent = Agent(
    get_model(),
    system_prompt="You are a planning specialist that creates daily summaries and schedules.",
    instrument=False,
)

@planner_agent.tool_plain
async def generate_plan(payload: dict) -> dict[str, str]:
    """Generate a plan and summary for the target date."""
    return planner_agent_core.run(payload)

# ========== Create RAG agent with ChromaDB ==========
class ChromaDBServer:
    def __init__(self, persist_dir: str = "./chroma_db"):
        """Initialize the ChromaDB client and collection.

        The collection uses the OpenAI embedding function so that both file
        indexing and the web crawler can store embeddings with the same
        dimensionality (1536).
        """

        openai_api_key = os.getenv("LLM_API_KEY")
        embedding_function = None
        if openai_api_key:
            embedding_function = OpenAIEmbeddingFunction(
                api_key=openai_api_key,
                model_name="text-embedding-3-small",
            )

        self.client = chromadb.Client(
            Settings(persist_directory=persist_dir, is_persistent=True)
        )
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"},
            embedding_function=embedding_function,
        )
        # Initialize the model for context generation
        self.context_gen_model_instance = get_model()
    
    def _sanitize_metadata(self, metadata: dict) -> dict:
        """
        Sanitize metadata to ensure all values are compatible with ChromaDB.
        ChromaDB only accepts str, int, float, or bool values in metadata.
        """
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, (list, dict)):
                # Convert complex types to JSON strings
                sanitized[key] = json.dumps(value)
            elif isinstance(value, (str, int, float, bool, type(None))):
                # Keep simple types as-is (None becomes null in JSON, but let's convert to string)
                sanitized[key] = str(value) if value is None else value
            else:
                # Convert any other type to string
                sanitized[key] = str(value)
        return sanitized

    async def _generate_chunk_context(self, whole_document: str, chunk_content: str) -> str:
        """Generate a contextualized summary for a chunk"""
        system_prompt = """You are an expert at creating context summaries. Given a full document and a specific chunk from that document, create a brief context that will help with semantic search and retrieval.

Your context should:
1. Describe what type of content this chunk contains
2. Mention relevant topics, concepts, or entities
3. Be 1-2 sentences maximum
4. Focus on searchable keywords and concepts

Example output: "Code implementation for user authentication using JWT tokens and middleware validation."
"""
        
        user_prompt = f"""Full document excerpt:
{whole_document[:2000]}...

Specific chunk to contextualize:
{chunk_content}

Create a brief context summary:"""

        try:
            result = await self.context_gen_model_instance.run(
                user_prompt,
                message_history=[{"role": "system", "content": system_prompt}]
            )
            return result.data
        except Exception as e:
            log_warning(f"Failed to generate context for chunk: {str(e)}")
            return "Document content"

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # If this isn't the last chunk, try to find a good breaking point
            if end < len(text):
                # Look for sentence endings in the last 200 characters
                breaking_zone = text[max(start, end - 200):end]
                sentence_endings = ['.', '!', '?', '\n\n']
                
                best_break = -1
                for ending in sentence_endings:
                    pos = breaking_zone.rfind(ending)
                    if pos > best_break:
                        best_break = pos
                
                if best_break > -1:
                    end = max(start, end - 200) + best_break + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - overlap
            if start >= len(text):
                break
                
        return chunks
    
    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read content from a file with encoding detection"""
        import mimetypes
        
        # Check if file is likely to be text-based
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and not mime_type.startswith('text/'):
            # Additional check for common text file extensions
            text_extensions = {'.py', '.js', '.ts', '.html', '.css', '.md', '.txt', 
                             '.json', '.xml', '.yaml', '.yml', '.sh', '.sql', '.env'}
            if not any(file_path.lower().endswith(ext) for ext in text_extensions):
                log_warning(f"Skipping binary file: {file_path}")
                return None
        
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                log_error(f"Error reading {file_path}: {str(e)}")
                return None
        
        log_error(f"Could not decode file with any encoding: {file_path}")
        return None
    
    def _get_directory_files(self, directory_path: str, recursive: bool = True, 
                           include_extensions: Optional[List[str]] = None) -> List[str]:
        """Get all files from directory with optional filtering"""
        import os
        
        files = []
        try:
            if recursive:
                for root, _, filenames in os.walk(directory_path):
                    for filename in filenames:
                        if filename.startswith('.'):  # Skip hidden files
                            continue
                        
                        file_path = os.path.join(root, filename)
                        
                        if include_extensions:
                            if any(filename.lower().endswith(ext.lower()) for ext in include_extensions):
                                files.append(file_path)
                        else:
                            files.append(file_path)
            else:
                for filename in os.listdir(directory_path):
                    if filename.startswith('.'):  # Skip hidden files
                        continue
                    
                    file_path = os.path.join(directory_path, filename)
                    if os.path.isfile(file_path):
                        if include_extensions:
                            if any(filename.lower().endswith(ext.lower()) for ext in include_extensions):
                                files.append(file_path)
                        else:
                            files.append(file_path)
        except Exception as e:
            log_error(f"Error scanning directory {directory_path}: {str(e)}")
            return []
    
    async def add_documents(self, texts: List[str], metadatas: Optional[List[dict]] = None) -> List[str]:
        """Add documents to the vector store"""
        
        # Sanitize metadata to ensure ChromaDB compatibility
        sanitized_metadatas = None
        if metadatas:
            sanitized_metadatas = [self._sanitize_metadata(metadata) for metadata in metadatas]
        
        # Robust ID generation to avoid collisions
        # This uses a combination of file stem, chunk index, and a simple counter based on the number of texts being added.
        # For more robust global uniqueness, a UUID or hash of the content could be considered.
        ids = []
        for i, text_content in enumerate(texts):
            file_path_stem = "unknown_source"
            chunk_idx_str = str(i)
            if sanitized_metadatas and i < len(sanitized_metadatas) and sanitized_metadatas[i]:
                if 'file_path' in sanitized_metadatas[i] and sanitized_metadatas[i]['file_path']:
                    file_path_stem = pathlib.Path(sanitized_metadatas[i]['file_path']).stem
                if 'chunk_index' in sanitized_metadatas[i]:
                    chunk_idx_str = str(sanitized_metadatas[i]['chunk_index'])
            
            # Simple hash of the first 50 chars of the content to add more uniqueness
            content_hash_prefix = hex(hash(text_content[:50]))[2:10] # first 8 hex chars
            ids.append(f"doc_{file_path_stem}_{chunk_idx_str}_{content_hash_prefix}_{i}")

        self.collection.add(
            documents=texts,
            metadatas=sanitized_metadatas if sanitized_metadatas else [{"source": "user"} for _ in texts],
            ids=ids
        )
        return ids
    
    async def add_file(self, file_path: str, chunk_size: int = 1000) -> dict[str, Any]:
        """Add a single file to the vector store with contextualized chunks"""
        content = self._read_file_content(file_path)
        if content is None or not content.strip(): # Also check if content is not just whitespace
            error_msg = f"Could not read file or file is empty: {file_path}"
            log_error(error_msg)
            return {"success": False, "error": error_msg}
        
        original_chunks = self._chunk_text(content, chunk_size)
        if not original_chunks:
            log_warning(f"No chunks generated for file: {file_path}")
            return {"success": True, "file_path": file_path, "chunks_added": 0, "document_ids": []} # Success but 0 chunks

        contextualized_chunks = []
        
        # Consider batching calls to _generate_chunk_context if possible and beneficial
        # For now, processing sequentially
        for chunk_content in original_chunks:
            if not chunk_content.strip(): # Skip empty or whitespace-only chunks
                log_warning(f"Skipping empty chunk in file {file_path}")
                continue
            context_prefix = await self._generate_chunk_context(content, chunk_content)
            contextualized_chunks.append(f"{context_prefix}\\n\\n{chunk_content}") # Add extra newline for clarity
            
        if not contextualized_chunks: # If all chunks were empty or context gen failed for all
             log_warning(f"No contextualized chunks to add for file: {file_path}")
             return {"success": True, "file_path": file_path, "chunks_added": 0, "document_ids": []}


        metadatas = [
            {
                "source": "file",
                "file_path": file_path,
                "chunk_index": i, # This index refers to original_chunks
                "total_chunks": len(original_chunks),
                # "original_chunk": original_chunks[i] # Optionally store original chunk if needed
            }
            # Ensure metadata list matches the length of contextualized_chunks
            # If some original chunks were skipped, this needs adjustment
            # For now, assuming original_chunks and contextualized_chunks will have a direct mapping
            # or that metadata is generated based on the final list of chunks to be added.
            # Let's regenerate metadatas based on the length of contextualized_chunks,
            # assuming chunk_index should correspond to the index in contextualized_chunks.
            for i in range(len(contextualized_chunks)) 
        ]
        
        # Regenerate metadatas if original_chunks were skipped
        if len(contextualized_chunks) != len(original_chunks):
            log_warning(
                f"Notice: Number of contextualized chunks ({len(contextualized_chunks)}) differs from original ({len(original_chunks)}) for file {file_path} due to empty chunk skipping."
            )
            current_original_chunk_idx = -1
            new_metadatas = []
            temp_original_chunks_for_metadata = [c for c in original_chunks if c.strip()]

            for i in range(len(contextualized_chunks)):
                 # This assumes a direct 1-to-1 mapping of non-empty original chunks to contextualized chunks
                 # This metadata generation might need to be more robust if the relationship is complex
                new_metadatas.append({
                    "source": "file",
                    "file_path": file_path,
                    "original_chunk_index": i, # This mapping might be tricky if original chunks are skipped.
                                                # Storing the index from the *filtered* original_chunks list.
                    "total_original_chunks": len(original_chunks), # Total before filtering
                     # "original_chunk": temp_original_chunks_for_metadata[i] # if storing original
                })
            metadatas = new_metadatas


        doc_ids = await self.add_documents(contextualized_chunks, metadatas)
        
        return {
            "success": True,
            "file_path": file_path,
            "chunks_added": len(contextualized_chunks),
            "document_ids": doc_ids
        }
    
    async def add_directory(self, directory_path: str, recursive: bool = True, 
                          include_extensions: Optional[List[str]] = None,
                          chunk_size: int = 1000) -> dict[str, Any]:
        """Add all files from a directory to the vector store"""
        files = self._get_directory_files(directory_path, recursive, include_extensions)
        
        if not files:
            return {"success": False, "error": f"No readable files found in: {directory_path}"}
        
        total_chunks = 0
        processed_files = []
        errors = []
        
        for file_path in files:
            try:
                result = await self.add_file(file_path, chunk_size)
                if result["success"]:
                    processed_files.append({
                        "file_path": file_path,
                        "chunks": result["chunks_added"]
                    })
                    total_chunks += result["chunks_added"]
                else:
                    errors.append(f"{file_path}: {result['error']}")
            except Exception as e:
                errors.append(f"{file_path}: {str(e)}")
        
        return {
            "success": len(processed_files) > 0,
            "directory_path": directory_path,
            "files_processed": len(processed_files),
            "total_files_found": len(files),
            "total_chunks_added": total_chunks,
            "processed_files": processed_files,
            "errors": errors
        }
    
    async def search(self, query: str, n_results: int = 3, *, rerank: bool = False, search_k: Optional[int] = None) -> List[dict]:
        """Search for relevant documents with optional reranking."""
        if search_k is None:
            search_k = max(n_results, 10) if rerank else n_results

        results = self.collection.query(
            query_texts=[query],
            n_results=search_k,
        )

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        if rerank:
            from difflib import SequenceMatcher

            embed_scores = [1 - d for d in distances]
            text_scores = [SequenceMatcher(None, query.lower(), doc.lower()).ratio() for doc in documents]
            combined = [0.5 * e + 0.5 * t for e, t in zip(embed_scores, text_scores)]
            ranked_indices = sorted(range(len(documents)), key=lambda i: combined[i], reverse=True)
            top_indices = ranked_indices[:n_results]
            documents = [documents[i] for i in top_indices]
            metadatas = [metadatas[i] for i in top_indices]
            distances = [distances[i] for i in top_indices]
        else:
            documents = documents[:n_results]
            metadatas = metadatas[:n_results]
            distances = distances[:n_results]

        return {
            "documents": documents,
            "metadatas": metadatas,
            "distances": distances,
        }

# Initialize ChromaDB server
chroma_server = ChromaDBServer()

# Create RAG agent
rag_agent = Agent(
    get_model(),
    system_prompt="""You are a RAG (Retrieval Augmented Generation) specialist that uses ChromaDB as your vector store. You help users by:
    1. Indexing documents and content into the vector store:
       - Individual text documents from user input
       - Single files (supports various text formats: .py, .js, .ts, .html, .css, .md, .txt, .json, .xml, .yaml, .yml, .sh, .sql, .env, etc.)
       - Entire directories (with optional filtering by file extensions)
       - Recursive directory scanning
    2. Performing semantic search to find relevant context
    3. Generating responses based on the retrieved context
    4. Managing the knowledge base
    
    Always explain what you're doing and provide relevant excerpts from retrieved documents.
    
    When indexing documents:
    - Split long texts into smaller, overlapping chunks for better retrieval
    - Maintain detailed document metadata (source, file paths, chunk information)
    - Confirm successful indexing with statistics
    - Handle various text file formats automatically
    
    When indexing files:
    - Support both individual files and entire directories
    - Automatically detect and read text-based files
    - Skip binary files and hidden files
    - Allow filtering by file extensions
    - Provide detailed results including files processed, chunks created, and any errors
    
    When searching:
    - Use semantic search to find relevant documents
    - Consider similarity scores
    - Return the most relevant context with source information
    - Include file paths and chunk information when available
    
    - Crawling websites or sitemaps to index their content.
    
    Always explain what you're doing and provide relevant excerpts from retrieved documents.""",
    instrument=False
)

# Add ChromaDB methods as tools for the RAG agent
@rag_agent.tool_plain
async def add_to_knowledge_base(texts: List[str], metadatas: Optional[List[dict]] = None) -> dict[str, Any]:
    """
    Add documents to the ChromaDB vector store.
    
    Args:
        texts: List of text documents to add
        metadatas: Optional list of metadata dictionaries for each document
        
    Returns:
        Dictionary containing the IDs of added documents
    """
    doc_ids = await chroma_server.add_documents(texts, metadatas)
    return {"document_ids": doc_ids}

@rag_agent.tool_plain
async def index_file(file_path: str, chunk_size: int = 1000) -> dict[str, Any]:
    """
    Index a single file into the ChromaDB vector store.
    
    Args:
        file_path: Path to the file to index
        chunk_size: Size of text chunks (default: 1000)
        
    Returns:
        Dictionary containing indexing results and metadata
    """
    result = await chroma_server.add_file(file_path, chunk_size)
    return result

@rag_agent.tool_plain
async def index_directory(directory_path: str, recursive: bool = True, 
                         include_extensions: Optional[List[str]] = None,
                         chunk_size: int = 1000) -> dict[str, Any]:
    """
    Index all files from a directory into the ChromaDB vector store.
    
    Args:
        directory_path: Path to the directory to index
        recursive: Whether to include subdirectories (default: True)
        include_extensions: List of file extensions to include (e.g., ['.py', '.txt'])
        chunk_size: Size of text chunks (default: 1000)
        
    Returns:
        Dictionary containing indexing results and metadata
    """
    result = await chroma_server.add_directory(directory_path, recursive, include_extensions, chunk_size)
    return result

@rag_agent.tool_plain
async def search_knowledge_base(
    query: str,
    n_results: int = 3,
    *,
    rerank: bool = False,
    search_k: Optional[int] = None,
) -> dict[str, Any]:
    """
    Search the ChromaDB vector store for relevant documents.
    
    Args:
        query: The search query
        n_results: Number of results to return (default: 3)
        rerank: Whether to apply reranking to the retrieved results
        search_k: Candidate pool size for reranking. If not provided and
            rerank is True, defaults to ``max(n_results, 10)``.
        
    Returns:
        Dictionary containing matched documents, their metadata, and similarity scores
    """
    results = await chroma_server.search(
        query, n_results, rerank=rerank, search_k=search_k
    )
    return results

@rag_agent.tool_plain
async def crawl_website_and_index(url: Optional[str] = None, sitemap_url: Optional[str] = None) -> str:
    """Crawls a website and indexes it into the ChromaDB knowledge base.
    
    Args:
        url: Direct URL to crawl (optional)
        sitemap_url: Sitemap URL to extract URLs from (optional)
        
    Returns:
        A string confirming the initiation of the crawling process.
    """
    if not url and not sitemap_url:
        return "Error: Please provide either a 'url' or a 'sitemap_url' to crawl."

    urls_to_crawl_list = [url] if url else []
    target = url if url else sitemap_url

    log_info(f"RAG Agent: Received request to crawl and index: {target}")
    try:
        # Pass the chroma_collection from the chroma_server instance
        await run_crawler(
            urls_to_crawl=urls_to_crawl_list, 
            chroma_collection=chroma_server.collection,  # Pass the required collection parameter
            sitemap_url=sitemap_url
        )
        confirmation_message = f"Crawling and indexing initiated for '{target}'. Check console logs for progress and completion status."
        log_info(f"RAG Agent: {confirmation_message}")
        return confirmation_message
    except Exception as e:
        error_message = f"Error during crawling and indexing for '{target}': {str(e)}"
        log_error(f"RAG Agent: {error_message}")
        return error_message

# ========== Create the primary orchestration agent ==========
primary_agent = Agent(
    get_model(),
    system_prompt="""You are a primary orchestration agent that can call upon specialized subagents 
    to perform various tasks. Each subagent is an expert in interacting with a specific third-party service.
    
    Available capabilities include:
    - Web search using Brave Search
    - File system operations (read, write, list files)
    - GitHub repository interactions
    - Slack workspace management
    - Test report analysis
    - Document indexing and RAG-based question answering
    - Image text extraction and OCR processing
    
    - **Image Processing Agent**: Extract text from images (screenshots, documents, diagrams) and optionally index the content into the knowledge base. Can also parse conversation logs from chat platform screenshots (Slack, Discord, Teams, etc.) and structure them as searchable conversation data. Can process multiple images concurrently and supports various formats including JPEG, PNG, GIF, BMP, TIFF, WebP. 
      - For text extraction: Use when users want to extract text from image files or URLs
      - For conversation parsing: Use when users want to parse chat logs, conversation screenshots, or message histories from images
    
    When users want to search for information in documents or need contextual answers, use the RAG agent.
    
    Analyze the user request and delegate the work to the appropriate subagent.""",
    instrument=False
)

# ========== Define tools for the primary agent to call subagents ==========
@primary_agent.tool_plain
async def use_brave_search_agent(query: str) -> dict[str, str]:
    """
    Search the web using Brave Search through the Brave subagent.
    Use this tool when the user needs to find information on the internet or research a topic.

    Args:
        ctx: The run context.
        query: The search query or instruction for the Brave search agent.

    Returns:
        The search results or response from the Brave agent.
    """
    log_info(f"Calling Brave agent with query: {query}")
    result = await brave_agent.run(query)
    return {"result": result.data}

@primary_agent.tool_plain
async def use_filesystem_agent(query: str) -> dict[str, str]:
    """
    Interact with the file system through the filesystem subagent.
    Use this tool when the user needs to read, write, list, or modify files.

    Args:
        ctx: The run context.
        query: The instruction for the filesystem agent.

    Returns:
        The response from the filesystem agent.
    """
    log_info(f"Calling Filesystem agent with query: {query}")
    result = await filesystem_agent.run(query)
    return {"result": result.data}

@primary_agent.tool_plain
async def use_github_agent(query: str) -> dict[str, str]:
    """
    Interact with GitHub through the GitHub subagent.
    Use this tool when the user needs to access repositories, issues, PRs, or other GitHub resources.

    Args:
        ctx: The run context.
        query: The instruction for the GitHub agent.

    Returns:
        The response from the GitHub agent.
    """
    log_info(f"Calling GitHub agent with query: {query}")
    result = await github_agent.run(query)
    return {"result": result.data}

@primary_agent.tool_plain
async def use_slack_agent(query: str) -> dict[str, str]:
    """
    Interact with Slack through the Slack subagent.
    Use this tool when the user needs to send messages, access channels, or retrieve Slack information.

    Args:
        ctx: The run context.
        query: The instruction for the Slack agent.

    Returns:
        The response from the Slack agent.
    """
    log_info(f"Calling Slack agent with query: {query}")
    result = await slack_agent.run(query)
    return {"result": result.data}

@primary_agent.tool_plain
async def use_analyzer_agent(query: str) -> dict[str, str]:
    """
    Interact with the analyzer subagent.
    Use this tool when the user needs to analyze their test reports.

    Args:
        ctx: The run context.
        query: The instruction for the analyzer agent.

    Returns:
        The response from the analyzer agent.
    """
    log_info(f"Calling Analyzer agent with query: {query}")
    result = await analyzer_agent.run(query)
    return {"result": result.data}

@primary_agent.tool_plain
async def use_rag_agent(query: str) -> dict[str, str]:
    """
    Interact with the RAG agent for contextual information retrieval and generation.
    Use this tool when the user needs to:
    - Index new documents into the knowledge base
    - Index single files into the vector store  
    - Index entire directories (with optional file filtering)
    - Search for information in indexed documents
    - Get answers based on the knowledge base context
    - Manage the vector store

    The RAG agent supports various text file formats (.py, .js, .ts, .html, .css, .md, .txt, 
    .json, .xml, .yaml, .yml, .sh, .sql, .env, etc.) and can process directories recursively.

    Args:
        query: The instruction for the RAG agent.

    Returns:
        The response from the RAG agent with retrieved context and generated answer.
    """
    log_info(f"Calling RAG agent with query: {query}")
    result = await rag_agent.run(query)
    return {"result": result.data}

@primary_agent.tool_plain
async def use_image_processor(query: str, image_paths: List[str] = None, image_urls: List[str] = None) -> dict[str, str]:
    """
    Extract text from images and optionally index them into the knowledge base.
    Can also parse conversation logs from chat platforms (Slack, Discord, Teams, etc.).
    
    Use this tool when the user needs to:
    - Extract text from image files (PNG, JPG, JPEG, GIF, BMP, TIFF, WebP)
    - Process images from local file paths or URLs
    - Index extracted text into the vector store for later search
    - OCR text from screenshots, documents, charts, or any image with text content
    - Parse conversation logs from chat platform screenshots
    - Structure chat messages with speakers, timestamps, and reactions

    Args:
        query: The instruction for image processing (e.g., "extract text from image", "parse conversation from screenshot")
        image_paths: Optional list of local file paths to image files
        image_urls: Optional list of URLs to image files

    Returns:
        The extracted text content, parsed conversation data, and processing results.
    """
    log_info(f"Calling Image Processor with query: {query}")
    
    try:
        # If no specific paths/URLs provided, try to extract them from the query
        if not image_paths and not image_urls:
            # Basic pattern matching to find file paths or URLs in the query
            import re
            
            # Look for file paths (ending with image extensions) - multiple patterns to handle different scenarios
            # Pattern 1: Quoted filenames (with or without quotes)
            quoted_pattern = r'["\']([^"\']*\.(?:png|jpg|jpeg|gif|bmp|tiff|tif|webp))["\']'
            # Pattern 2: Unquoted filenames - look for likely filename patterns
            unquoted_pattern = r'(?:image|file|screenshot)\s+([^"\s]+(?:\s+[^"\s]+)*\.(?:png|jpg|jpeg|gif|bmp|tiff|tif|webp))(?:\s+(?:in|from|at|file|directory|folder)|$)'
            # Pattern 3: Simple filename without spaces
            simple_pattern = r'([^\s<>"|?*]+\.(?:png|jpg|jpeg|gif|bmp|tiff|tif|webp))'
            
            found_paths = []
            # Try quoted pattern first
            found_paths.extend(re.findall(quoted_pattern, query, re.IGNORECASE))
            # If no quoted paths found, try unquoted pattern
            if not found_paths:
                found_paths.extend(re.findall(unquoted_pattern, query, re.IGNORECASE))
            # Fall back to simple pattern
            if not found_paths:
                found_paths.extend(re.findall(simple_pattern, query, re.IGNORECASE))
            
            # Look for URLs
            url_pattern = r'https?://[\w\-._~:/?#[\]@!$&\'()*+,;=%]+'
            found_urls = re.findall(url_pattern, query, re.IGNORECASE)
            
            image_paths = found_paths if found_paths else None
            image_urls = found_urls if found_urls else None
            
            log_info(f"Extracted from query - Paths: {image_paths}, URLs: {image_urls}")
        
        # If no specific files found, check if user mentioned a directory
        if not image_paths and not image_urls:
            # Look for directory references in the query
            dir_pattern = r'(?:in|at|from)\s+([^"\s]+/?)'
            dir_matches = re.findall(dir_pattern, query, re.IGNORECASE)
            
            for potential_dir in dir_matches:
                potential_dir = potential_dir.rstrip('/')  # Remove trailing slash
                
                # Check if it's a valid directory
                if os.path.isdir(potential_dir):
                    # Find image files in the directory
                    try:
                        image_files = [f for f in os.listdir(potential_dir) 
                                     if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp'))]
                        
                        if image_files:
                            # Auto-detect based on query context
                            if len(image_files) == 1:
                                # Only one image, use it
                                image_paths = [os.path.join(potential_dir, image_files[0])]
                                log_info(f"Auto-detected single image in {potential_dir}: {image_files[0]}")
                            elif 'conversation' in query.lower() or 'chat' in query.lower() or 'screenshot' in query.lower():
                                # Look for the most recent screenshot-like file
                                screenshot_files = [f for f in image_files if 'screenshot' in f.lower()]
                                if screenshot_files:
                                    # Use the most recent screenshot (lexicographically last, assuming timestamp format)
                                    latest_screenshot = sorted(screenshot_files)[-1]
                                    image_paths = [os.path.join(potential_dir, latest_screenshot)]
                                    log_info(f"Auto-detected latest screenshot in {potential_dir}: {latest_screenshot}")
                                else:
                                    # Use the most recent image file
                                    latest_image = sorted(image_files)[-1]
                                    image_paths = [os.path.join(potential_dir, latest_image)]
                                    log_info(f"Auto-detected latest image in {potential_dir}: {latest_image}")
                            else:
                                # Multiple images, use all of them
                                image_paths = [os.path.join(potential_dir, f) for f in image_files]
                                log_info(f"Auto-detected {len(image_files)} images in {potential_dir}")
                            break
                    except Exception as e:
                        log_warning(f"Error scanning directory {potential_dir}: {e}")
            
            log_info(f"After directory detection - Paths: {image_paths}, URLs: {image_urls}")
        
        # Prepare image sources
        image_sources = []
        
        if image_paths:
            for path in image_paths:
                # Handle relative paths by joining with data directory if needed
                if not os.path.isabs(path) and not os.path.exists(path):
                    # Try in data directory
                    data_path = os.path.join("data", path)
                    if os.path.exists(data_path):
                        path = data_path
                    else:
                        # If exact match fails, try fuzzy matching in data directory
                        import difflib
                        try:
                            original_basename = os.path.basename(path)
                            data_files = [f for f in os.listdir("data") if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp'))]
                            # Find the closest match
                            closest_matches = difflib.get_close_matches(os.path.basename(path), data_files, n=1, cutoff=0.8)
                            if closest_matches:
                                fuzzy_path = os.path.join("data", closest_matches[0])
                                if os.path.exists(fuzzy_path):
                                    path = fuzzy_path
                                    log_info(f"Using fuzzy match: {closest_matches[0]} for requested: {original_basename}")
                        except Exception as e:
                            log_warning(f"Error during fuzzy matching: {e}")
                
                if os.path.exists(path):
                    image_sources.append({'source': path, 'type': 'file'})
                    log_info(f"Added image file: {path}")
                else:
                    log_warning(f"Image file not found: {path}")
        
        if image_urls:
            for url in image_urls:
                image_sources.append({'source': url, 'type': 'url'})
                log_info(f"Added image URL: {url}")
        
        if not image_sources:
            return {"result": "No valid image sources found. Please provide image file paths or URLs."}
        
        # Determine if we should index the results or just extract text
        should_index = any(keyword in query.lower() for keyword in ['index', 'store', 'save', 'add to knowledge'])
        
        # Determine if this is specifically for conversation parsing
        is_conversation_request = any(keyword in query.lower() for keyword in [
            'conversation', 'chat', 'messages', 'slack', 'discord', 'teams', 
            'conversation log', 'chat log', 'message log', 'parse conversation'
        ])
        
        if is_conversation_request:
            # Process as conversation logs
            log_info("Processing images as conversation logs...")
            conversation_results = []
            
            for source_info in image_sources:
                try:
                    # First extract text
                    extracted_text = await extract_text_from_image(
                        source_info['source'], 
                        source_info['type']
                    )
                    
                    if extracted_text:
                        # Parse as conversation
                        conversation_log = await parse_conversation_from_text(
                            extracted_text, 
                            source_info['source']
                        )
                        
                        if conversation_log:
                            # Index conversation if requested
                            if should_index:
                                await process_conversation_and_index(
                                    conversation_log, 
                                    chroma_server.collection
                                )
                            
                            conversation_results.append({
                                'source': source_info['source'],
                                'platform': conversation_log.platform,
                                'participants': conversation_log.participants or [],
                                'message_count': len(conversation_log.messages),
                                'conversation': conversation_log
                            })
                            log_info(f"Parsed {len(conversation_log.messages)} messages from {source_info['source']}")
                        else:
                            log_warning(f"Could not parse conversation from {source_info['source']}")
                    else:
                        log_warning(f"No text extracted from {source_info['source']}")
                        
                except Exception as e:
                    log_error(f"Error processing conversation from {source_info['source']}: {e}")
            
            if conversation_results:
                if should_index:
                    result_text = f"Successfully processed and indexed {len(conversation_results)} conversation(s) into the knowledge base:\n\n"
                else:
                    result_text = f"Successfully parsed {len(conversation_results)} conversation(s):\n\n"
                
                for result in conversation_results:
                    result_text += f"**Source:** {result['source']}\n"
                    result_text += f"**Platform:** {result['platform']}\n"
                    result_text += f"**Participants:** {', '.join(result['participants'])}\n"
                    result_text += f"**Messages:** {result['message_count']}\n"
                    
                    if not should_index:
                        # Show conversation details if not indexing
                        result_text += f"**Conversation:**\n"
                        for msg in result['conversation'].messages:
                            timestamp_str = f" ({msg.timestamp})" if msg.timestamp else ""
                            result_text += f"  {msg.speaker}{timestamp_str}: {msg.content}\n"
                    
                    result_text += "\n---\n\n"
            else:
                result_text = "No conversations could be parsed from the provided images."
        
        elif should_index:
            # Extract and index into knowledge base
            log_info("Processing images and indexing into knowledge base...")
            await run_image_processor(
                image_sources=image_sources,
                chroma_collection=chroma_server.collection,
                max_concurrent_processing=3
            )
            
            result_text = f"Successfully processed and indexed {len(image_sources)} image(s) into the knowledge base. "
            result_text += f"Text has been extracted and stored for future search and retrieval."
        
        else:
            # Just extract text without indexing
            log_info("Extracting text from images...")
            extracted_texts = []
            
            for source_info in image_sources:
                try:
                    extracted_text = await extract_text_from_image(
                        source_info['source'], 
                        source_info['type']
                    )
                    if extracted_text:
                        extracted_texts.append({
                            'source': source_info['source'],
                            'text': extracted_text,
                            'length': len(extracted_text)
                        })
                        log_info(f"Extracted {len(extracted_text)} characters from {source_info['source']}")
                    else:
                        log_warning(f"No text extracted from {source_info['source']}")
                except Exception as e:
                    log_error(f"Error processing {source_info['source']}: {e}")
            
            if extracted_texts:
                result_text = f"Successfully extracted text from {len(extracted_texts)} image(s):\n\n"
                for item in extracted_texts:
                    result_text += f"**Source:** {item['source']}\n"
                    result_text += f"**Extracted Text ({item['length']} characters):**\n{item['text']}\n\n---\n\n"
            else:
                result_text = "No text could be extracted from the provided images."
        
        return {"result": result_text}
        
    except Exception as e:
        error_msg = f"Error during image processing: {str(e)}"
        log_error(error_msg)
        return {"result": error_msg}

@primary_agent.tool_plain
async def use_planner_agent(payload: dict) -> dict[str, str]:
    """Generate a daily plan using the Planner agent."""
    log_info("Calling Planner agent")
    result = await planner_agent.run(payload)
    return {"result": json.dumps(result)}

# ========== Main execution function ==========
async def main():
    """Run the primary agent with a given query."""
    log_info("MCP Agent Army - Multi-agent system using Model Context Protocol")
    log_info("Enter 'exit' to quit the program.")

    # Initialize ChromaDB
    log_info("Initializing ChromaDB vector store...")
    try:
        # This will create or load the existing database
        chroma_server = ChromaDBServer()
        log_info("ChromaDB initialized successfully!")
    except Exception as e:
        log_error(f"Error initializing ChromaDB: {str(e)}")
        return

    # Use AsyncExitStack to manage all MCP servers in one context
    async with AsyncExitStack() as stack:
        # Start all the subagent MCP servers
        log_info("Starting MCP servers...")
        await stack.enter_async_context(brave_agent.run_mcp_servers())
        await stack.enter_async_context(filesystem_agent.run_mcp_servers())
        await stack.enter_async_context(github_agent.run_mcp_servers())
        await stack.enter_async_context(slack_agent.run_mcp_servers())
        log_info("All MCP servers started successfully!")

        console = Console()
        messages = []        
        
        while True:
            # Get user input
            user_input = input("\n[You] ")
            
            # Check if user wants to exit
            if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                log_info("Goodbye!")
                break
            
            try:
                # Process the user input and output the response
                log_info("\n[Assistant]")
                curr_message = ""
                with Live('', console=console, vertical_overflow='visible') as live:
                    async with primary_agent.run_stream(
                        user_input, message_history=messages
                    ) as result:
                        async for message in result.stream_text(delta=True):
                            curr_message += message
                            live.update(Markdown(curr_message))
                    
                # Add the new messages to the chat history
                messages.extend(result.all_messages())
                
            except Exception as e:
                log_error(f"\n[Error] An error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
