"""Filesystem operations agent with indexing capabilities."""
from typing import Any, Optional
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai import RunContext
from pydantic_ai.models.openai import OpenAIModel

from src.agents.base import BaseAgent
from src.core.constants import AgentType, SYSTEM_PROMPTS
from src.mcp import get_mcp_manager
from src.storage.chromadb_client import get_chromadb_client
from src.utils.logging import log_info, log_error, log_warning
from src.processors.calendar import parse_calendar_from_image, save_parsed_events_yaml
from src.processors.image import extract_text_from_image, parse_conversation_from_text, process_conversation_and_index


class FilesystemAgentDeps(BaseModel):
    """Dependencies for the filesystem agent."""
    chromadb_client: Any = Field(default=None)
    
    class Config:
        arbitrary_types_allowed = True


class FilesystemAgent(BaseAgent):
    """Agent for performing filesystem operations with indexing capabilities."""
    
    def __init__(self, model: OpenAIModel):
        """Initialize the Filesystem agent.
        
        Args:
            model: OpenAI model to use
        """
        # Get MCP manager and server
        mcp_manager = get_mcp_manager()
        self.filesystem_server = mcp_manager.get_server("filesystem")
        
        # Initialize ChromaDB client for indexing
        try:
            self.chromadb_client = get_chromadb_client()
            log_info("Filesystem agent initialized with ChromaDB indexing")
        except Exception as e:
            log_warning(f"ChromaDB not available for indexing: {str(e)}")
            self.chromadb_client = None
        
        # Update system prompt to include indexing and image analysis capabilities
        enhanced_prompt = SYSTEM_PROMPTS[AgentType.FILESYSTEM] + """
You can also index files into the knowledge base for later retrieval using the RAG agent.
When asked to index a file, use the index_file tool to store its contents in the vector database.
You can analyze calendar screenshots using the analyze_calendar_image tool and save the extracted events to YAML files.
You can analyze conversation screenshots using the analyze_conversation_image tool and index them to the knowledge base."""
        
        super().__init__(
            name=AgentType.FILESYSTEM,
            model=model,
            system_prompt=enhanced_prompt,
            deps_type=FilesystemAgentDeps,
            mcp_servers=[self.filesystem_server]
        )
        
        self._register_tools()
        log_info("Filesystem agent initialized with indexing capabilities")
    
    def _register_tools(self):
        """Register additional tools for the filesystem agent."""
        
        @self.agent.tool
        async def index_file(
            ctx: RunContext[FilesystemAgentDeps],
            file_path: str,
            chunk_size: int = 1000,
            chunk_overlap: int = 200
        ) -> str:
            """Index a file into the knowledge base for RAG retrieval.
            
            Args:
                file_path: Path to the file to index
                chunk_size: Size of text chunks
                chunk_overlap: Overlap between chunks
                
            Returns:
                Status message
            """
            log_info(f"Indexing file: {file_path}")
            
            if not ctx.deps.chromadb_client:
                return "ChromaDB client not initialized. Cannot index files."
            
            try:
                # Read the file content
                path = Path(file_path)
                if not path.exists():
                    return f"File not found: {file_path}"
                
                if not path.is_file():
                    return f"Path is not a file: {file_path}"
                
                # Read file content
                try:
                    content = path.read_text(encoding='utf-8')
                except UnicodeDecodeError:
                    # Try different encodings
                    for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                        try:
                            content = path.read_text(encoding=encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        return f"Unable to read file {file_path} - unsupported encoding"
                
                # Get file metadata
                file_stats = path.stat()
                metadata = {
                    'source': str(path.absolute()),
                    'filename': path.name,
                    'file_type': path.suffix,
                    'file_size': file_stats.st_size,
                    'modified_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                    'indexed_at': datetime.now().isoformat(),
                }
                
                # Chunk the content
                chunks = ctx.deps.chromadb_client.chunk_text(
                    content, 
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                
                if not chunks:
                    return f"No content to index in file: {file_path}"
                
                # Prepare documents and metadata for each chunk
                documents = []
                metadatas = []
                ids = []
                
                for i, chunk in enumerate(chunks):
                    chunk_metadata = metadata.copy()
                    chunk_metadata['chunk_index'] = i
                    chunk_metadata['chunk_total'] = len(chunks)
                    
                    documents.append(chunk)
                    metadatas.append(chunk_metadata)
                    ids.append(f"{path.stem}_chunk_{i}_{datetime.now().timestamp()}")
                
                # Add to ChromaDB
                ctx.deps.chromadb_client.add_documents(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                log_info(f"Successfully indexed {len(chunks)} chunks from {file_path}")
                return f"Successfully indexed file {file_path} ({len(chunks)} chunks, {len(content)} characters)"
                
            except Exception as e:
                log_error(f"Error indexing file {file_path}: {str(e)}")
                return f"Error indexing file: {str(e)}"
        
        @self.agent.tool
        async def index_directory(
            ctx: RunContext[FilesystemAgentDeps],
            directory_path: str,
            file_pattern: str = "*.txt",
            recursive: bool = True
        ) -> str:
            """Index all matching files in a directory into the knowledge base.
            
            Args:
                directory_path: Path to the directory
                file_pattern: Glob pattern for files to index
                recursive: Whether to search recursively
                
            Returns:
                Status message
            """
            log_info(f"Indexing directory: {directory_path} with pattern: {file_pattern}")
            
            if not ctx.deps.chromadb_client:
                return "ChromaDB client not initialized. Cannot index files."
            
            try:
                path = Path(directory_path)
                if not path.exists():
                    return f"Directory not found: {directory_path}"
                
                if not path.is_dir():
                    return f"Path is not a directory: {directory_path}"
                
                # Find matching files
                if recursive:
                    files = list(path.rglob(file_pattern))
                else:
                    files = list(path.glob(file_pattern))
                
                if not files:
                    return f"No files matching pattern '{file_pattern}' found in {directory_path}"
                
                # Index each file
                success_count = 0
                error_count = 0
                
                for file_path in files:
                    try:
                        result = await index_file(ctx, str(file_path))
                        if "Successfully indexed" in result:
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        log_error(f"Error indexing {file_path}: {str(e)}")
                        error_count += 1
                
                summary = f"Indexed {success_count} files successfully"
                if error_count > 0:
                    summary += f" ({error_count} errors)"
                
                return summary
                
            except Exception as e:
                log_error(f"Error indexing directory: {str(e)}")
                return f"Error indexing directory: {str(e)}"
        
        @self.agent.tool
        async def analyze_calendar_image(
            ctx: RunContext[FilesystemAgentDeps],
            image_path: str,
            output_yaml_path: str = "data/meetings.yaml"
        ) -> str:
            """Analyze a calendar screenshot and extract events to a YAML file.
            
            Args:
                image_path: Path to the calendar image
                output_yaml_path: Path where to save the extracted events
                
            Returns:
                Status message
            """
            log_info(f"Analyzing calendar image: {image_path}")
            
            try:
                # Check if image exists
                image_file = Path(image_path)
                if not image_file.exists():
                    return f"Image file not found: {image_path}"
                
                if not image_file.is_file():
                    return f"Path is not a file: {image_path}"
                
                # Use the calendar processor to extract events
                events = await parse_calendar_from_image(str(image_file))
                
                if not events:
                    return f"No calendar events found in image: {image_path}"
                
                # Save events to YAML
                save_parsed_events_yaml(events, output_yaml_path)
                
                # Format summary of events
                event_summary = []
                for event in events[:5]:  # Show first 5 events
                    event_str = f"- {event['date']} {event['time']}: {event['event']}"
                    event_summary.append(event_str)
                
                if len(events) > 5:
                    event_summary.append(f"... and {len(events) - 5} more events")
                
                summary = "\n".join(event_summary)
                
                log_info(f"Successfully extracted {len(events)} events from {image_path}")
                return f"Successfully analyzed calendar image and saved {len(events)} events to {output_yaml_path}:\n\n{summary}"
                
            except Exception as e:
                log_error(f"Error analyzing calendar image: {str(e)}")
                return f"Error analyzing calendar image: {str(e)}"
        
        @self.agent.tool
        async def analyze_conversation_image(
            ctx: RunContext[FilesystemAgentDeps],
            image_path: str,
            index_to_knowledge_base: bool = True
        ) -> str:
            """Analyze a conversation screenshot and optionally index it to the knowledge base.
            
            Args:
                image_path: Path to the conversation image
                index_to_knowledge_base: Whether to index the conversations
                
            Returns:
                Status message
            """
            log_info(f"Analyzing conversation image: {image_path}")
            
            try:
                # Check if image exists
                image_file = Path(image_path)
                if not image_file.exists():
                    return f"Image file not found: {image_path}"
                
                if not image_file.is_file():
                    return f"Path is not a file: {image_path}"
                
                # Extract text from image first
                text = await extract_text_from_image(str(image_file), "file")
                if not text:
                    return f"No text found in image: {image_path}"
                
                # Parse conversations
                conversation_log = await parse_conversation_from_text(text, str(image_file))
                
                if not conversation_log or not conversation_log.messages:
                    return f"No conversations found in image: {image_path}"
                
                # Index if requested
                if index_to_knowledge_base and ctx.deps.chromadb_client:
                    await process_conversation_and_index(
                        conversation_log,
                        ctx.deps.chromadb_client.collection
                    )
                    
                    return f"Successfully analyzed conversation image and indexed {len(conversation_log.messages)} conversation entries to the knowledge base from {image_path}"
                else:
                    # Format summary without indexing
                    conv_summary = []
                    for i, msg in enumerate(conversation_log.messages[:3]):  # Show first 3 messages
                        timestamp_str = f" ({msg.timestamp})" if msg.timestamp else ""
                        content_preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
                        conv_str = f"- {msg.speaker}{timestamp_str}: {content_preview}"
                        conv_summary.append(conv_str)
                    
                    if len(conversation_log.messages) > 3:
                        conv_summary.append(f"... and {len(conversation_log.messages) - 3} more messages")
                    
                    summary = "\n".join(conv_summary)
                    
                    platform_info = f" on {conversation_log.platform}" if conversation_log.platform else ""
                    channel_info = f" in #{conversation_log.channel}" if conversation_log.channel else ""
                    
                    return f"Successfully extracted {len(conversation_log.messages)} conversation entries{platform_info}{channel_info} from {image_path}:\n\n{summary}"
                
            except Exception as e:
                log_error(f"Error analyzing conversation image: {str(e)}")
                return f"Error analyzing conversation image: {str(e)}"
    
    async def run(self, prompt: str, deps: Optional[Any] = None, **kwargs) -> Any:
        """Run the filesystem agent.
        
        Args:
            prompt: The user prompt
            deps: Optional dependencies (if not provided, will create default)
            **kwargs: Additional arguments
            
        Returns:
            The agent's response
        """
        if deps is None:
            deps = FilesystemAgentDeps(
                chromadb_client=self.chromadb_client
            )
        
        return await super().run(prompt, deps=deps, **kwargs)