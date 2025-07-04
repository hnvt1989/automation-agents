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
    reactions: Optional[List[Dict[str, Any]]] = None

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
    
    @property
    def message_count(self) -> int:
        """Return the number of messages in this conversation."""
        return len(self.messages) if self.messages else 0
    
    def to_json(self) -> str:
        """Export conversation to JSON format."""
        import json
        data = {
            "platform": self.platform,
            "channel": self.channel,
            "participants": self.participants or [],
            "messages": [
                {
                    "speaker": msg.speaker,
                    "timestamp": msg.timestamp,
                    "content": msg.content,
                    "message_id": msg.message_id,
                    "reactions": msg.reactions or []
                } for msg in (self.messages or [])
            ],
            "metadata": self.metadata or {},
            "extracted_at": self.extracted_at,
            "image_source": self.image_source
        }
        return json.dumps(data, indent=2)
    
    def to_text(self) -> str:
        """Export conversation to plain text format."""
        lines = [f"Conversation on {self.platform}"]
        if self.channel:
            lines.append(f"Channel: #{self.channel}")
        if self.participants:
            lines.append(f"Participants: {', '.join(self.participants)}")
        lines.append("")
        
        for msg in (self.messages or []):
            timestamp_str = f" ({msg.timestamp})" if msg.timestamp else ""
            lines.append(f"{msg.speaker}{timestamp_str}: {msg.content}")
        
        return "\n".join(lines)
    
    def to_markdown(self) -> str:
        """Export conversation to markdown format."""
        lines = [f"# Conversation on {self.platform}"]
        if self.channel:
            lines.append(f"**Channel:** #{self.channel}")
        if self.participants:
            lines.append(f"**Participants:** {', '.join(self.participants)}")
        lines.append("")
        
        for msg in (self.messages or []):
            timestamp_str = f" *({msg.timestamp})*" if msg.timestamp else ""
            lines.append(f"**{msg.speaker}**{timestamp_str}: {msg.content}")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        return {
            "message_count": self.message_count,
            "participant_count": len(self.participants) if self.participants else 0,
            "time_span": self._calculate_time_span(),
            "platform": self.platform,
            "channel": self.channel
        }
    
    def _calculate_time_span(self) -> str:
        """Calculate time span of conversation."""
        if not self.messages or len(self.messages) < 2:
            return "N/A"
        
        timestamps = [msg.timestamp for msg in self.messages if msg.timestamp]
        if len(timestamps) < 2:
            return "N/A"
        
        return f"From {timestamps[0]} to {timestamps[-1]}"
    
    def detect_threads(self) -> List[Dict[str, Any]]:
        """Detect conversation threads."""
        # Simple implementation - could be enhanced
        threads = [{"id": "main", "messages": self.messages or []}]
        return threads
    
    def extract_topics(self) -> List[str]:
        """Extract topics from conversation."""
        # Simple keyword-based implementation
        topics = []
        all_content = " ".join([msg.content for msg in (self.messages or [])])
        
        # Simple topic extraction based on keywords
        keywords = ["meeting", "project", "code", "review", "demo", "planning", "bug", "feature"]
        for keyword in keywords:
            if keyword.lower() in all_content.lower():
                topics.append(keyword)
        
        return topics
    
    def anonymize(self) -> 'ConversationLog':
        """Return anonymized version of conversation."""
        anonymized_messages = []
        participant_map = {}
        
        for i, participant in enumerate(self.participants or []):
            participant_map[participant] = f"User_{i+1}"
        
        for msg in (self.messages or []):
            anonymized_msg = ConversationMessage(
                speaker=participant_map.get(msg.speaker, "Anonymous"),
                timestamp=msg.timestamp,
                content=msg.content,  # Could sanitize content further
                message_id=msg.message_id,
                reactions=msg.reactions
            )
            anonymized_messages.append(anonymized_msg)
        
        return ConversationLog(
            image_source=self.image_source,
            platform=self.platform,
            channel=self.channel,
            participants=list(participant_map.values()),
            messages=anonymized_messages,
            metadata=self.metadata,
            extracted_at=self.extracted_at
        )
    
    def sanitize_content(self) -> 'ConversationLog':
        """Return sanitized version of conversation."""
        # Simple implementation - could be enhanced with more sophisticated sanitization
        sanitized_messages = []
        
        for msg in (self.messages or []):
            sanitized_msg = ConversationMessage(
                speaker=msg.speaker,
                timestamp=msg.timestamp,
                content=msg.content,  # Could add PII removal here
                message_id=msg.message_id,
                reactions=msg.reactions
            )
            sanitized_messages.append(sanitized_msg)
        
        return ConversationLog(
            image_source=self.image_source,
            platform=self.platform,
            channel=self.channel,
            participants=self.participants,
            messages=sanitized_messages,
            metadata=self.metadata,
            extracted_at=self.extracted_at
        )
    
    def get_new_messages_since(self, other_conversation: 'ConversationLog') -> List[ConversationMessage]:
        """Get new messages since another conversation."""
        if not other_conversation or not other_conversation.messages:
            return self.messages or []
        
        other_content_set = {msg.content for msg in other_conversation.messages}
        new_messages = [msg for msg in (self.messages or []) if msg.content not in other_content_set]
        
        return new_messages
    
    def generate_summary(self) -> str:
        """Generate a summary of the conversation."""
        if not self.messages:
            return "Empty conversation"
        
        participants_str = ", ".join(self.participants or [])
        return f"Conversation between {participants_str} on {self.platform} with {len(self.messages)} messages."
    
    def extract_key_points(self) -> List[str]:
        """Extract key points from the conversation."""
        key_points = []
        
        # Simple keyword-based key point extraction
        for msg in (self.messages or []):
            content = msg.content.lower()
            if any(keyword in content for keyword in ["important", "key", "note", "remember", "action", "todo", "decision"]):
                key_points.append(f"{msg.speaker}: {msg.content[:100]}...")
        
        return key_points

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
                
            # Parse reactions from message content
            reactions = []
            reaction_patterns = [
                r'(👍|💯|✅|⚡|❤️|😄|😊|🎉|🔥|👏)\s*(\d+)',
                r':\w+:\s*(\d+)'
            ]
            
            for pattern in reaction_patterns:
                matches = re.findall(pattern, message_content)
                for match in matches:
                    if len(match) == 2:
                        emoji, count = match
                        reactions.append({"emoji": emoji, "count": int(count)})
                    elif len(match) == 1 and match[0].isdigit():
                        # Handle cases where emoji is captured separately
                        reactions.append({"emoji": "👍", "count": int(match[0])})
            
            message = ConversationMessage(
                speaker=msg_data.get("speaker", "Unknown"),
                timestamp=msg_data.get("timestamp"),
                content=message_content,
                reactions=reactions if reactions else None
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
                "parsed_at": datetime.now(timezone.utc).isoformat(),
                "message_count": len(messages)
            },
            extracted_at=datetime.now(timezone.utc).isoformat()
        )
        
        log_info(f"Successfully parsed conversation from {image_source}: {len(messages)} messages from {len(conversation_log.participants)} participants")
        return conversation_log
        
    except Exception as e:
        log_error(f"Error parsing conversation from {image_source}: {e}")
        return None