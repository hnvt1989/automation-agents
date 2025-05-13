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

from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai import Agent, RunContext
from chromadb import Client, Settings
import chromadb
import json

load_dotenv()

# ========== Helper function to get model configuration ==========
def get_model():
    llm = os.getenv('MODEL_CHOICE', 'gpt-4.1-mini')
    base_url = os.getenv('BASE_URL', 'https://api.openai.com/v1')
    api_key = os.getenv('LLM_API_KEY', 'no-api-key-provided')

    return OpenAIModel(llm, provider=OpenAIProvider(base_url=base_url, api_key=api_key))

# ========== Set up MCP servers for each service ==========

# Brave Search MCP server
brave_server = MCPServerStdio(
    'npx', ['-y', '@modelcontextprotocol/server-brave-search'],
    env={"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")}
)

# Filesystem MCP server
filesystem_server = MCPServerStdio(
    'npx', ['-y', '@modelcontextprotocol/server-filesystem', os.getenv("LOCAL_FILE_DIR")]
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
    
    async def add_documents(self, texts: List[str], metadatas: Optional[List[dict]] = None) -> List[str]:
        """Add documents to the vector store"""
        ids = [f"doc_{i}" for i in range(len(texts))]
        self.collection.add(
            documents=texts,
            metadatas=metadatas if metadatas else [{"source": "user"} for _ in texts],
            ids=ids
        )
        return ids
    
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
    1. Indexing documents and content into the vector store
    2. Performing semantic search to find relevant context
    3. Generating responses based on the retrieved context
    4. Managing the knowledge base
    
    Always explain what you're doing and provide relevant excerpts from retrieved documents.
    
    When indexing documents:
    - Split long texts into smaller chunks
    - Maintain document metadata
    - Confirm successful indexing
    
    When searching:
    - Use semantic search to find relevant documents
    - Consider similarity scores
    - Return the most relevant context""",
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
    - Search for information in indexed documents
    - Get answers based on the knowledge base context
    - Manage the vector store

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
