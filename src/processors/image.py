import os
import sys
import json
import asyncio
import base64
import hashlib
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
import requests
from PIL import Image
import io
import re

from src.utils.logging import log_info, log_warning, log_error

from openai import AsyncOpenAI
import chromadb

load_dotenv("local.env")

# Initialize OpenAI client
openai_api_key = os.getenv("LLM_API_KEY")
if not openai_api_key:
    log_error(
        "CRITICAL: LLM_API_KEY not found in .env file. The image processor cannot function without it for vision processing and embeddings."
    )
    openai_client = None
else:
    openai_client = AsyncOpenAI(api_key=openai_api_key)

@dataclass
class ProcessedImageChunk:
    """Represents a processed chunk of text extracted from an image."""
    image_source: str  # file path, URL, or "base64_input"
    chunk_number: int
    title: str
    summary: str
    content: str
    metadata: Dict[str, Any]
    embedding: List[float] | None

@dataclass
class ConversationMessage:
    """Represents a single message in a conversation."""
    speaker: str
    timestamp: str
    content: str
    thread_id: Optional[str] = None
    message_id: Optional[str] = None

@dataclass
class ConversationLog:
    """Represents a complete conversation log extracted from an image."""
    image_source: str
    platform: str  # 'slack', 'discord', 'teams', 'generic', etc.
    channel: Optional[str] = None
    participants: List[str] = None
    messages: List[ConversationMessage] = None
    metadata: Dict[str, Any] = None
    extracted_at: str = None

def encode_image_to_base64(image_path: str) -> str:
    """Encode an image file to base64 string."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        log_error(f"Error encoding image {image_path} to base64: {e}")
        raise

async def download_image_from_url(url: str) -> bytes:
    """Download an image from a URL and return as bytes."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        log_error(f"Error downloading image from {url}: {e}")
        raise

def validate_image(image_data: bytes) -> bool:
    """Validate that the data represents a valid image."""
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            img.verify()
        return True
    except Exception as e:
        log_error(f"Invalid image data: {e}")
        return False

async def extract_text_from_image(image_source: str, source_type: str = "file") -> str:
    """
    Extract text from an image using OpenAI's vision model.
    
    Args:
        image_source: File path, URL, or base64 string
        source_type: "file", "url", or "base64"
    """
    if not openai_client:
        log_error("OpenAI client not initialized. Cannot extract text from image.")
        return ""
    
    try:
        if source_type == "file":
            # Validate file exists and is an image
            if not os.path.exists(image_source):
                log_error(f"Image file not found: {image_source}")
                return ""
            
            # Read and validate image
            with open(image_source, "rb") as f:
                image_data = f.read()
            
            if not validate_image(image_data):
                log_error(f"Invalid image file: {image_source}")
                return ""
            
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
        elif source_type == "url":
            # Download and validate image
            image_data = await download_image_from_url(image_source)
            
            if not validate_image(image_data):
                log_error(f"Invalid image from URL: {image_source}")
                return ""
            
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
        elif source_type == "base64":
            base64_image = image_source
            
        else:
            log_error(f"Invalid source_type: {source_type}")
            return ""
        
        # Get image format for the data URL
        img_format = "jpeg"  # default
        try:
            image_data_for_format = base64.b64decode(base64_image)
            with Image.open(io.BytesIO(image_data_for_format)) as img:
                img_format = img.format.lower() if img.format else "jpeg"
        except:
            pass  # Keep default format
        
        vision_model = os.getenv("VISION_LLM_MODEL", "gpt-4o")
        
        response = await openai_client.chat.completions.create(
            model=vision_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that extracts text from images for document processing purposes. Please be comprehensive and accurate in your text extraction."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please extract all text content from this image. Be comprehensive and preserve the structure and formatting as much as possible. If there are tables, lists, or structured content, maintain that structure. Return only the extracted text content."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{img_format};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4000
        )
        
        extracted_text = response.choices[0].message.content.strip()
        log_info(f"Successfully extracted {len(extracted_text)} characters of text from image.")
        return extracted_text
        
    except Exception as e:
        log_error(f"Error extracting text from image {image_source}: {e}")
        return ""

def chunk_text(text: str, chunk_size: int = 5000) -> List[str]:
    """
    Split text into chunks with smart boundary detection.
    This is the same function as in crawler.py for consistency.
    """
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        if end >= text_length:
            current_chunk_content = text[start:].strip()
            if current_chunk_content: 
                chunks.append(current_chunk_content)
            break
        
        chunk_segment = text[start:end]
        
        # Try to break at paragraph boundaries
        last_paragraph_break = chunk_segment.rfind('\n\n')
        if last_paragraph_break > chunk_size * 0.3: 
            end = start + last_paragraph_break + 2 
        elif '. ' in chunk_segment:
            # Try to break at sentence boundaries
            last_sentence_break = chunk_segment.rfind('. ')
            if last_sentence_break > chunk_size * 0.3:
                end = start + last_sentence_break + 1 
        
        current_chunk_content = text[start:end].strip()
        if current_chunk_content: 
            chunks.append(current_chunk_content)
        
        start = max(start + 1, end) 
    
    return chunks

async def _generate_image_chunk_context(whole_document_text: str, original_chunk_content: str, image_source: str) -> str:
    """Generate situating context for an image text chunk using an LLM."""
    if not openai_client:
        log_error(f"OpenAI client not initialized. Cannot generate context for chunk from {image_source}.")
        return ""
    
    # Limit the size to avoid excessive token usage
    max_doc_len_for_context = 10000 
    max_chunk_len_for_context = 2000

    truncated_whole_document = whole_document_text
    if len(whole_document_text) > max_doc_len_for_context:
        truncated_whole_document = whole_document_text[:max_doc_len_for_context//2] + "\n... (document truncated for context generation) ...\n" + whole_document_text[-max_doc_len_for_context//2:]
    
    truncated_chunk_content = original_chunk_content
    if len(original_chunk_content) > max_chunk_len_for_context:
        truncated_chunk_content = original_chunk_content[:max_chunk_len_for_context//2] + "... (chunk truncated for context generation) ..." + original_chunk_content[-max_chunk_len_for_context//2:]

    prompt = f"""<document_extracted_from_image>
{truncated_whole_document}
</document_extracted_from_image>

Here is a specific chunk from the image text above:
<chunk>
{truncated_chunk_content}
</chunk>

Please provide a short, succinct context (1-2 sentences) that situates this chunk within the overall extracted text from the image. This context will be prepended to the chunk to improve search retrieval. Focus on the main topic of the chunk and its relation to the broader document theme. Answer ONLY with the succinct context itself and nothing else."""
    
    llm_model = os.getenv("CONTEXT_LLM_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini"))

    try:
        response = await openai_client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        context_prefix = response.choices[0].message.content.strip()
        
        # Basic filter for common refusal or non-contextual phrases
        if not context_prefix or "cannot provide context" in context_prefix.lower() or "unable to fulfill" in context_prefix.lower():
            log_warning(f"LLM returned non-contextual response for chunk from {image_source}. Using empty context.")
            return ""
        return context_prefix
    except Exception as e:
        log_error(f"Error generating image chunk context for {image_source} with model {llm_model}: {e}")
        return ""

async def get_title_and_summary(chunk: str, image_source: str) -> Dict[str, str]:
    """Generate title and summary for an image text chunk."""
    if not openai_client:
        log_error(f"OpenAI client not initialized. Cannot get title/summary for chunk from {image_source}.")
        return {"title": "OpenAI client error", "summary": "OpenAI client error"}
    
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    system_prompt = """You are an AI that extracts titles and summaries from text chunks extracted from images.
    Return a JSON object with 'title' and 'summary' keys.
    For the title: If this seems like the start of a document, extract its title. If it's a middle chunk, derive a descriptive title for this specific chunk.
    For the summary: Create a concise summary of the main points in this chunk.
    Keep both title and summary concise but informative."""
    
    try:
        content_for_prompt = chunk
        if len(chunk) > 3000: 
            content_for_prompt = chunk[:1500] + "... (content truncated for title/summary) ..." + chunk[-1500:]
        
        response = await openai_client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Image source: {image_source}\n\nExtracted text content:\n{content_for_prompt}"}
            ],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return {"title": result.get("title", "N/A"), "summary": result.get("summary", "N/A")}
    except Exception as e:
        log_error(f"Error getting title and summary for chunk from {image_source} with model {llm_model}: {e}")
        return {"title": "Error processing title", "summary": "Error processing summary"}

async def get_embedding(text: str, model: str = "text-embedding-3-small") -> List[float] | None:
    """Generate embedding for text."""
    if not openai_client:
        log_error(f"OpenAI client not initialized. Cannot get embedding for text (first 50 chars: '{text[:50]}...').")
        return None
    
    try:
        response = await openai_client.embeddings.create(
            model=model,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        log_error(f"Error getting embedding for text (first 50 chars: '{text[:50]}...'): {e}")
        return None

async def process_image_chunk(original_chunk_content: str, chunk_idx: int, image_source: str, whole_image_text: str) -> ProcessedImageChunk | None:
    """Process a chunk of text extracted from an image."""
    # 1. Generate title and summary from the original chunk content
    title_summary = await get_title_and_summary(original_chunk_content, image_source)

    # 2. Generate situating context based on whole image text and original chunk
    context_prefix = await _generate_image_chunk_context(whole_image_text, original_chunk_content, image_source)
    
    # 3. Prepend context to the original chunk content
    if context_prefix:
        contextualized_content = f"{context_prefix}\n\n{original_chunk_content}"
    else:
        contextualized_content = original_chunk_content
    
    # 4. Get embedding for the contextualized content
    embedding_vector = await get_embedding(contextualized_content)
    
    # Base metadata for the chunk
    metadata = {
        "source_type": "image_text_extraction",
        "image_source": image_source,
        "original_content_length": len(original_chunk_content),
        "contextualized_content_length": len(contextualized_content),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "context_prefix_length": len(context_prefix)
    }
    
    # Add file-specific metadata if it's a file path
    if os.path.exists(image_source):
        try:
            file_path = Path(image_source)
            metadata.update({
                "file_name": file_path.name,
                "file_extension": file_path.suffix,
                "file_size": file_path.stat().st_size,
                "file_modified": datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc).isoformat()
            })
        except Exception as e:
            log_warning(f"Could not get file metadata for {image_source}: {e}")
    
    return ProcessedImageChunk(
        image_source=image_source,
        chunk_number=chunk_idx,
        title=title_summary['title'],
        summary=title_summary['summary'],
        content=contextualized_content,
        metadata=metadata,
        embedding=embedding_vector
    )

async def add_image_chunk_to_collection(chunk: ProcessedImageChunk, chroma_collection: chromadb.api.models.Collection.Collection):
    """Add a processed image chunk to the provided ChromaDB collection."""
    if not chroma_collection:
        log_error(f"ChromaDB collection not provided. Cannot add chunk for {chunk.image_source}.")
        return None
    
    if chunk.embedding is None:
        log_warning(f"Skipping chunk {chunk.chunk_number} from {chunk.image_source} due to missing embedding.")
        return None

    chroma_metadata = {
        "source_type": "image_text_contextualized",
        "image_source": chunk.image_source,
        "title": chunk.title or "N/A",
        "summary": chunk.summary or "N/A",
        "image_chunk_number": chunk.chunk_number,
        "processed_at": chunk.metadata.get("processed_at", datetime.now(timezone.utc).isoformat()),
        "content_length": len(chunk.content),
        "original_content_length": chunk.metadata.get("original_content_length", 0),
        "context_prefix_length": chunk.metadata.get("context_prefix_length", 0)
    }
    
    # Add other metadata
    for key, value in chunk.metadata.items():
        if key not in chroma_metadata and isinstance(value, (str, int, float, bool)):
            chroma_metadata[key] = value
    
    # Create unique document ID
    content_hash_short = hashlib.md5(chunk.content.encode('utf-8')).hexdigest()[:8]
    source_hash = hashlib.md5(chunk.image_source.encode('utf-8')).hexdigest()[:8]
    doc_id = f"img_txt::{source_hash}::num_{chunk.chunk_number}::hash_{content_hash_short}"

    try:
        chroma_collection.add(
            ids=[doc_id],
            embeddings=[chunk.embedding],
            documents=[chunk.content],
            metadatas=[chroma_metadata]
        )
        log_info(f"Added image text chunk ID {doc_id} (Source: {chunk.image_source}, Chunk: {chunk.chunk_number}) to ChromaDB collection '{chroma_collection.name}'.")
        return doc_id
    except chromadb.errors.IDAlreadyExistsError:
        log_warning(f"Image text chunk ID {doc_id} already exists in ChromaDB for {chunk.image_source}. Skipping.")
        return doc_id
    except Exception as e:
        log_error(f"Error adding image text chunk ID {doc_id} for {chunk.image_source} to ChromaDB: {e}")
        return None

async def process_image_and_index(image_source: str, source_type: str, chroma_collection: chromadb.api.models.Collection.Collection):
    """
    Process a single image: extract text, chunk it, and index into ChromaDB.
    
    Args:
        image_source: File path, URL, or base64 string
        source_type: "file", "url", or "base64"
        chroma_collection: ChromaDB collection to store the results
    """
    log_info(f"Starting image processing for: {image_source} (type: {source_type})")
    
    # Extract text from image
    extracted_text = await extract_text_from_image(image_source, source_type)
    
    if not extracted_text.strip():
        log_warning(f"No text extracted from image: {image_source}. Skipping further processing.")
        return
    
    log_info(f"Successfully extracted {len(extracted_text)} characters from {image_source}")
    
    # Split into chunks
    text_chunks = chunk_text(extracted_text)
    log_info(f"Split extracted text from {image_source} into {len(text_chunks)} chunks.")
    
    # Process each chunk
    for i, original_chunk_str in enumerate(text_chunks):
        if not original_chunk_str.strip():
            log_warning(f"Skipping empty chunk {i} from {image_source} after chunking.")
            continue
        
        # Process the chunk
        processed_chunk_object = await process_image_chunk(original_chunk_str, i, image_source, extracted_text)
        
        if processed_chunk_object:
            if chroma_collection:
                await add_image_chunk_to_collection(processed_chunk_object, chroma_collection)
            else:
                log_error(f"ChromaDB collection not provided. Cannot store chunk {i} from {image_source}.")
        else:
            log_error(f"Failed to process chunk {i} from {image_source}. It will not be stored.")

async def run_image_processor(image_sources: List[Dict[str, str]], 
                             chroma_collection: chromadb.api.models.Collection.Collection,
                             max_concurrent_processing: int = 3):
    """
    Main function to run the image processor, storing results in the provided ChromaDB Collection.
    
    Args:
        image_sources: List of dicts with 'source' and 'type' keys
                      e.g., [{'source': '/path/to/image.jpg', 'type': 'file'},
                             {'source': 'https://example.com/image.png', 'type': 'url'}]
        chroma_collection: ChromaDB collection to store the results
        max_concurrent_processing: Maximum number of concurrent image processing tasks
    """
    if not chroma_collection:
        log_error("CRITICAL: ChromaDB collection was not provided to run_image_processor. Processed data will NOT be stored.")
        return
    
    if not image_sources:
        log_warning("No image sources provided. Exiting image processor.")
        return
    
    # Validate image sources
    valid_sources = []
    for source_info in image_sources:
        if not isinstance(source_info, dict) or 'source' not in source_info or 'type' not in source_info:
            log_warning(f"Invalid source info format: {source_info}. Skipping.")
            continue
        
        source = source_info['source']
        source_type = source_info['type']
        
        if source_type not in ['file', 'url', 'base64']:
            log_warning(f"Invalid source type '{source_type}' for {source}. Skipping.")
            continue
        
        if source_type == 'file' and not os.path.exists(source):
            log_warning(f"File not found: {source}. Skipping.")
            continue
        
        valid_sources.append(source_info)
    
    if not valid_sources:
        log_warning("No valid image sources after filtering. Exiting.")
        return
    
    log_info(f"Total valid image sources to process: {len(valid_sources)}")
    
    # Process images with concurrency control
    semaphore = asyncio.Semaphore(max_concurrent_processing)
    processing_tasks = []
    
    async def process_with_semaphore(source_info: Dict[str, str]):
        async with semaphore:
            await process_image_and_index(
                source_info['source'], 
                source_info['type'], 
                chroma_collection
            )
    
    for source_info in valid_sources:
        processing_tasks.append(process_with_semaphore(source_info))
    
    if processing_tasks:
        await asyncio.gather(*processing_tasks)
    
    log_info("Image processor run finished.")

async def parse_conversation_from_text(extracted_text: str, image_source: str) -> ConversationLog | None:
    """
    Parse conversation structure from extracted text using an LLM.
    
    Args:
        extracted_text: Raw text extracted from the image
        image_source: Source of the image for metadata
        
    Returns:
        ConversationLog object or None if parsing fails
    """
    if not openai_client:
        log_error("OpenAI client not initialized. Cannot parse conversation.")
        return None
    
    if not extracted_text.strip():
        log_warning("No text provided for conversation parsing.")
        return None
    
    # System prompt for conversation parsing
    system_prompt = """You are an expert at parsing conversation logs from various chat platforms (Slack, Discord, Teams, etc.).

Given extracted text from an image, parse it into a structured conversation format. Return a JSON object with:
{
  "platform": "slack|discord|teams|generic", 
  "channel": "channel name if visible",
  "participants": ["list", "of", "unique", "speakers"],
  "messages": [
    {
      "speaker": "username or display name",
      "timestamp": "time if available, or null",
      "content": "message content"
    }
  ]
}

Guidelines:
- Identify the platform based on visual cues (formatting, emoji usage, etc.)
- Extract speaker names consistently (remove platform indicators like "(PST)")
- Parse timestamps in a consistent format when available
- EXCLUDE all reaction lines (like "Reactions: 👍") from the message content
- ONLY include messages that have actual text content - exclude empty messages or speaker-only lines
- If a speaker appears but has no message content, do not include that entry
- Clean message content should not contain any reaction information
- If it's not a conversation, return {"platform": "none", "messages": []}
"""

    user_prompt = f"""Parse this text extracted from a chat/conversation image:

{extracted_text}

Return the structured conversation data as JSON."""

    try:
        llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        response = await openai_client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        parsed_data = json.loads(response.choices[0].message.content)
        
        # Check if it's actually a conversation
        if parsed_data.get("platform") == "none" or not parsed_data.get("messages"):
            log_info(f"Text from {image_source} does not appear to be a conversation.")
            return None
        
        # Create ConversationMessage objects
        messages = []
        for msg_data in parsed_data.get("messages", []):
            message_content = msg_data.get("content", "").strip()
            
            # Skip messages with empty content
            if not message_content:
                log_info(f"Skipping empty message from speaker: {msg_data.get('speaker', 'Unknown')}")
                continue
                
            message = ConversationMessage(
                speaker=msg_data.get("speaker", "Unknown"),
                timestamp=msg_data.get("timestamp", ""),
                content=message_content,
                thread_id=None,  # Could be enhanced later
                message_id=None  # Could be enhanced later
            )
            messages.append(message)
        
        # Create ConversationLog
        conversation_log = ConversationLog(
            image_source=image_source,
            platform=parsed_data.get("platform", "generic"),
            channel=parsed_data.get("channel"),
            participants=parsed_data.get("participants", []),
            messages=messages,
            metadata={
                "extracted_text_length": len(extracted_text),
                "message_count": len(messages),
                "platform_detected": parsed_data.get("platform", "generic")
            },
            extracted_at=datetime.now(timezone.utc).isoformat()
        )
        
        log_info(f"Successfully parsed conversation from {image_source}: {len(messages)} messages, platform: {conversation_log.platform}")
        return conversation_log
        
    except json.JSONDecodeError as e:
        log_error(f"Failed to parse JSON response for conversation from {image_source}: {e}")
        return None
    except Exception as e:
        log_error(f"Error parsing conversation from {image_source}: {e}")
        return None

async def process_conversation_and_index(conversation_log: ConversationLog, chroma_collection: chromadb.api.models.Collection.Collection):
    """
    Process a conversation log and index it into ChromaDB with conversation-specific metadata.
    
    Args:
        conversation_log: Parsed conversation log
        chroma_collection: ChromaDB collection to store the results
    """
    if not chroma_collection:
        log_error("ChromaDB collection not provided. Cannot store conversation log.")
        return
    
    if not conversation_log or not conversation_log.messages:
        log_warning("No valid conversation log or messages to process.")
        return
    
    log_info(f"Processing conversation from {conversation_log.image_source} with {len(conversation_log.messages)} messages")
    
    # Create different types of documents for better searchability
    documents_to_add = []
    metadatas_to_add = []
    ids_to_add = []
    
    # 1. Full conversation summary document
    conversation_summary = f"Conversation on {conversation_log.platform}"
    if conversation_log.channel:
        conversation_summary += f" in #{conversation_log.channel}"
    
    conversation_summary += f"\nParticipants: {', '.join(conversation_log.participants or [])}\n\n"
    
    for msg in conversation_log.messages:
        timestamp_str = f" ({msg.timestamp})" if msg.timestamp else ""
        conversation_summary += f"{msg.speaker}{timestamp_str}: {msg.content}\n"
        conversation_summary += "\n"
    
    # Add conversation context at the end
    conversation_summary += f"\n\nConversation context: {conversation_log.platform} conversation"
    if conversation_log.channel:
        conversation_summary += f" in #{conversation_log.channel}"
    if len(conversation_log.participants or []) > 1:
        conversation_summary += f" with {', '.join(conversation_log.participants)}"
    
    # Get embedding for full conversation
    full_embedding = await get_embedding(conversation_summary)
    if full_embedding:
        source_hash = hashlib.md5(conversation_log.image_source.encode('utf-8')).hexdigest()[:8]
        full_doc_id = f"conv_full::{source_hash}::all_messages"
        
        documents_to_add.append(conversation_summary)
        metadatas_to_add.append({
            "source_type": "conversation_full",
            "image_source": conversation_log.image_source,
            "platform": conversation_log.platform,
            "channel": conversation_log.channel or "unknown",
            "participants": json.dumps(conversation_log.participants or []),
            "message_count": len(conversation_log.messages),
            "processed_at": conversation_log.extracted_at,
            "content_type": "full_conversation"
        })
        ids_to_add.append(full_doc_id)
    
    # 2. Individual message documents for granular search
    for i, msg in enumerate(conversation_log.messages):
        message_content = f"Message from {msg.speaker}"
        if msg.timestamp:
            message_content += f" at {msg.timestamp}"
        message_content += f":\n{msg.content}"
        
        # Add conversation context
        message_content += f"\n\nConversation context: {conversation_log.platform} conversation"
        if conversation_log.channel:
            message_content += f" in #{conversation_log.channel}"
        if len(conversation_log.participants or []) > 1:
            message_content += f" with {', '.join(conversation_log.participants)}"
        
        msg_embedding = await get_embedding(message_content)
        if msg_embedding:
            msg_doc_id = f"conv_msg::{source_hash}::msg_{i}_{hashlib.md5(msg.content.encode('utf-8')).hexdigest()[:6]}"
            
            documents_to_add.append(message_content)
            metadatas_to_add.append({
                "source_type": "conversation_message",
                "image_source": conversation_log.image_source,
                "platform": conversation_log.platform,
                "channel": conversation_log.channel or "unknown",
                "speaker": msg.speaker,
                "timestamp": msg.timestamp or "",
                "message_index": i,
                "message_content": msg.content,
                "participants": json.dumps(conversation_log.participants or []),
                "processed_at": conversation_log.extracted_at,
                "content_type": "individual_message"
            })
            ids_to_add.append(msg_doc_id)
    
    # 3. Add all documents to ChromaDB
    if documents_to_add:
        try:
            # Get embeddings for all documents
            embeddings_to_add = []
            for doc in documents_to_add:
                embedding = await get_embedding(doc)
                embeddings_to_add.append(embedding)
            
            # Filter out None embeddings
            valid_data = [(doc, meta, doc_id, emb) for doc, meta, doc_id, emb in 
                         zip(documents_to_add, metadatas_to_add, ids_to_add, embeddings_to_add) 
                         if emb is not None]
            
            if valid_data:
                docs, metas, doc_ids, embeddings = zip(*valid_data)
                
                chroma_collection.add(
                    ids=list(doc_ids),
                    embeddings=list(embeddings),
                    documents=list(docs),
                    metadatas=list(metas)
                )
                
                log_info(f"Added {len(valid_data)} conversation documents to ChromaDB for {conversation_log.image_source}")
            else:
                log_warning(f"No valid embeddings generated for conversation from {conversation_log.image_source}")
                
        except chromadb.errors.IDAlreadyExistsError:
            log_warning(f"Some conversation documents already exist in ChromaDB for {conversation_log.image_source}")
        except Exception as e:
            log_error(f"Error adding conversation documents to ChromaDB for {conversation_log.image_source}: {e}") 