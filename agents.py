from __future__ import annotations
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from rich.markdown import Markdown
from rich.console import Console
from rich.live import Live
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
import json

# Import the get_model function to be used for context generation
from . import get_model # Assuming get_model is in the same directory or adjust path

load_dotenv('local.env')

# ========== Helper function to get model configuration ==========
# def get_model(): # This function is already defined globally, we'll use the imported one
#     llm = os.getenv('MODEL_CHOICE', 'gpt-4.1-mini')
#     base_url = os.getenv('BASE_URL', 'https://api.openai.com/v1')
#     api_key = os.getenv('LLM_API_KEY', 'no-api-key-provided')

#     print(f"Using {llm} model with base URL: {base_url}");
#     return OpenAIModel(llm, provider=OpenAIProvider(base_url=base_url, api_key=api_key))

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

# ========== Create RAG agent with ChromaDB ==========
class ChromaDBServer:
    def __init__(self, persist_dir: str = "./chroma_db"):
        self.client = chromadb.Client(Settings(
            persist_directory=persist_dir,
            is_persistent=True
        ))
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"}
        )
        # Initialize the model for context generation
        self.context_gen_model_instance = get_model()
    
    async def _generate_chunk_context(self, whole_document: str, chunk_content: str) -> str:
        """Generate context for a chunk using an LLM."""
        prompt = f"""<document>
{whole_document}
</document>
Here is the chunk we want to situate within the whole document
<chunk>
{chunk_content}
</chunk>
Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""
        
        try:
            # Using a temporary agent to run the prompt with the context_gen_model_instance
            # Ensure the model instance is compatible with pydantic_ai.Agent
            temp_agent = Agent(self.context_gen_model_instance, system_prompt="You are a helpful assistant designed to generate context.") # More specific system prompt
            result = await temp_agent.run(prompt) # No need for message_history for this specific task
            
            # Check if result and result.data are not None and result.data is a string
            if result and hasattr(result, 'data') and isinstance(result.data, str):
                return result.data.strip() # Strip whitespace
            else:
                print(f"Warning: Context generation did not return a string. Result: {result}")
                return ""
        except Exception as e:
            print(f"Error generating chunk context: {str(e)}")
            return ""

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Try to break at a sentence or paragraph boundary
            chunk = text[start:end]
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            
            if last_period > chunk_size * 0.7:
                end = start + last_period + 1
            elif last_newline > chunk_size * 0.7:
                end = start + last_newline + 1
            
            chunks.append(text[start:end])
            start = end - overlap
        
        return chunks
    
    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read content from a file based on its type"""
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            mime_type, _ = mimetypes.guess_type(file_path)
            
            # Handle text files
            if mime_type and mime_type.startswith('text/'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            # Handle specific file extensions
            text_extensions = {'.py', '.js', '.ts', '.html', '.css', '.md', '.txt', 
                             '.json', '.xml', '.yaml', '.yml', '.sh', '.sql', '.env'}
            
            if path.suffix.lower() in text_extensions:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            return None
            
        except Exception as e:
            print(f"Error reading file {file_path}: {str(e)}")
            return None
    
    def _get_directory_files(self, directory_path: str, recursive: bool = True, 
                           include_extensions: Optional[List[str]] = None) -> List[str]:
        """Get all readable files from a directory"""
        try:
            path = Path(directory_path)
            if not path.exists() or not path.is_dir():
                return []
            
            files = []
            pattern = "**/*" if recursive else "*"
            
            for file_path in path.glob(pattern):
                if file_path.is_file():
                    # Skip hidden files and common non-text files
                    if file_path.name.startswith('.'):
                        continue
                    
                    # Filter by extensions if specified
                    if include_extensions:
                        if file_path.suffix.lower() not in include_extensions:
                            continue
                    
                    # Check if file is readable
                    if self._read_file_content(str(file_path)) is not None:
                        files.append(str(file_path))
            
            return files
            
        except Exception as e:
            print(f"Error reading directory {directory_path}: {str(e)}")
            return []
    
    async def add_documents(self, texts: List[str], metadatas: Optional[List[dict]] = None) -> List[str]:
        """Add documents to the vector store"""
        
        # Robust ID generation to avoid collisions
        # This uses a combination of file stem, chunk index, and a simple counter based on the number of texts being added.
        # For more robust global uniqueness, a UUID or hash of the content could be considered.
        ids = []
        for i, text_content in enumerate(texts):
            file_path_stem = "unknown_source"
            chunk_idx_str = str(i)
            if metadatas and i < len(metadatas) and metadatas[i]:
                if 'file_path' in metadatas[i] and metadatas[i]['file_path']:
                    file_path_stem = pathlib.Path(metadatas[i]['file_path']).stem
                if 'chunk_index' in metadatas[i]:
                    chunk_idx_str = str(metadatas[i]['chunk_index'])
            
            # Simple hash of the first 50 chars of the content to add more uniqueness
            content_hash_prefix = hex(hash(text_content[:50]))[2:10] # first 8 hex chars
            ids.append(f"doc_{file_path_stem}_{chunk_idx_str}_{content_hash_prefix}_{i}")

        self.collection.add(
            documents=texts,
            metadatas=metadatas if metadatas else [{"source": "user"} for _ in texts],
            ids=ids
        )
        return ids
    
    async def add_file(self, file_path: str, chunk_size: int = 1000) -> dict[str, Any]:
        """Add a single file to the vector store with contextualized chunks"""
        content = self._read_file_content(file_path)
        if content is None or not content.strip(): # Also check if content is not just whitespace
            error_msg = f"Could not read file or file is empty: {file_path}"
            print(error_msg)
            return {"success": False, "error": error_msg}
        
        original_chunks = self._chunk_text(content, chunk_size)
        if not original_chunks:
            print(f"No chunks generated for file: {file_path}")
            return {"success": True, "file_path": file_path, "chunks_added": 0, "document_ids": []} # Success but 0 chunks

        contextualized_chunks = []
        
        # Consider batching calls to _generate_chunk_context if possible and beneficial
        # For now, processing sequentially
        for chunk_content in original_chunks:
            if not chunk_content.strip(): # Skip empty or whitespace-only chunks
                print(f"Skipping empty chunk in file {file_path}")
                continue
            context_prefix = await self._generate_chunk_context(content, chunk_content)
            contextualized_chunks.append(f"{context_prefix}\\n\\n{chunk_content}") # Add extra newline for clarity
            
        if not contextualized_chunks: # If all chunks were empty or context gen failed for all
             print(f"No contextualized chunks to add for file: {file_path}")
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
            print(f"Notice: Number of contextualized chunks ({len(contextualized_chunks)}) differs from original ({len(original_chunks)}) for file {file_path} due to empty chunk skipping.")
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
    
    async def search(self, query: str, n_results: int = 3) -> List[dict]:
        """Search for relevant documents"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return {
            "documents": results["documents"][0],
            "metadatas": results["metadatas"][0],
            "distances": results["distances"][0]
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
    - Include file paths and chunk information when available""",
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
async def search_knowledge_base(query: str, n_results: int = 3) -> dict[str, Any]:
    """
    Search the ChromaDB vector store for relevant documents.
    
    Args:
        query: The search query
        n_results: Number of results to return (default: 3)
        
    Returns:
        Dictionary containing matched documents, their metadata, and similarity scores
    """
    results = await chroma_server.search(query, n_results)
    return results

# ========== Create the primary orchestration agent ==========
primary_agent = Agent(
    get_model(),
    system_prompt="""You are a primary orchestration agent that can call upon specialized subagents 
    to perform various tasks. Each subagent is an expert in interacting with a specific third-party service.
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
    print(f"Calling Brave agent with query: {query}")
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
    print(f"Calling Filesystem agent with query: {query}")
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
    print(f"Calling GitHub agent with query: {query}")
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
    print(f"Calling Slack agent with query: {query}")
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
    print(f"Calling Analyzer agent with query: {query}")
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
    print(f"Calling RAG agent with query: {query}")
    result = await rag_agent.run(query)
    return {"result": result.data}

# ========== Main execution function ==========
async def main():
    """Run the primary agent with a given query."""
    print("MCP Agent Army - Multi-agent system using Model Context Protocol")
    print("Enter 'exit' to quit the program.")

    # Initialize ChromaDB
    print("Initializing ChromaDB vector store...")
    try:
        # This will create or load the existing database
        chroma_server = ChromaDBServer()
        print("ChromaDB initialized successfully!")
    except Exception as e:
        print(f"Error initializing ChromaDB: {str(e)}")
        return

    # Use AsyncExitStack to manage all MCP servers in one context
    async with AsyncExitStack() as stack:
        # Start all the subagent MCP servers
        print("Starting MCP servers...")
        await stack.enter_async_context(brave_agent.run_mcp_servers())
        await stack.enter_async_context(filesystem_agent.run_mcp_servers())
        await stack.enter_async_context(github_agent.run_mcp_servers())
        await stack.enter_async_context(slack_agent.run_mcp_servers())
        print("All MCP servers started successfully!")

        console = Console()
        messages = []        
        
        while True:
            # Get user input
            user_input = input("\n[You] ")
            
            # Check if user wants to exit
            if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                print("Goodbye!")
                break
            
            try:
                # Process the user input and output the response
                print("\n[Assistant]")
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
                print(f"\n[Error] An error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
