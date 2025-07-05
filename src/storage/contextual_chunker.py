"""Contextual chunking functionality for improved RAG retrieval."""
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from dataclasses import dataclass
import hashlib
from datetime import datetime

from src.utils.logging import log_info, log_warning, log_error
from src.core.config import get_settings
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider


@dataclass
class ChunkContext:
    """Container for chunk with contextual information."""
    original_text: str
    contextual_text: str
    metadata: Dict[str, Any]
    chunk_index: int
    total_chunks: int


class ContextualChunker:
    """Handles creation of contextual chunks for improved retrieval."""
    
    def __init__(self, llm_model: Optional[OpenAIModel] = None):
        """Initialize contextual chunker.
        
        Args:
            llm_model: Optional LLM model for context generation
        """
        self.settings = get_settings()
        self._context_cache = {}  # Simple in-memory cache
        
        # Initialize LLM for context generation if not provided
        if llm_model:
            self.llm_model = llm_model
        else:
            try:
                provider = OpenAIProvider(
                    base_url=self.settings.base_url,
                    api_key=self.settings.llm_api_key
                )
                self.llm_model = OpenAIModel(
                    self.settings.context_generation_model or 'gpt-4o-mini',
                    provider=provider
                )
            except Exception as e:
                log_warning(f"Failed to initialize LLM for context generation: {str(e)}")
                self.llm_model = None
    
    def create_contextual_chunks(
        self,
        content: str,
        chunk_size: int,
        chunk_overlap: int,
        context_info: Dict[str, Any],
        use_llm_context: bool = False
    ) -> List[ChunkContext]:
        """Create chunks with contextual information.
        
        Args:
            content: Content to chunk
            chunk_size: Size of each chunk
            chunk_overlap: Overlap between chunks
            context_info: Information about the document
            use_llm_context: Whether to use LLM for context generation
            
        Returns:
            List of contextual chunks
        """
        # First, create basic chunks
        basic_chunks = self._split_into_chunks(content, chunk_size, chunk_overlap)
        
        # Add context to each chunk
        contextual_chunks = []
        for i, chunk_text in enumerate(basic_chunks):
            if use_llm_context and self.llm_model:
                contextual_text = self._generate_llm_context(
                    chunk_text, context_info, i, len(basic_chunks)
                )
            else:
                contextual_text = self._generate_template_context(
                    chunk_text, context_info, i, len(basic_chunks)
                )
            
            chunk_context = ChunkContext(
                original_text=chunk_text,
                contextual_text=contextual_text,
                metadata=self._create_chunk_metadata(context_info, i, len(basic_chunks)),
                chunk_index=i,
                total_chunks=len(basic_chunks)
            )
            contextual_chunks.append(chunk_context)
        
        return contextual_chunks
    
    def _split_into_chunks(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int
    ) -> List[str]:
        """Split text into chunks with overlap."""
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                sentence_ends = ['. ', '.\n', '! ', '!\n', '? ', '?\n']
                best_break = -1
                
                for ending in sentence_ends:
                    pos = chunk.rfind(ending)
                    if pos > best_break and pos > chunk_size // 2:
                        best_break = pos + len(ending) - 1
                
                # If found a good break point, use it
                if best_break > 0:
                    chunk = chunk[:best_break + 1]
                    end = start + best_break + 1
                else:
                    # Try to break at paragraph
                    newline_pos = chunk.rfind('\n\n')
                    if newline_pos > chunk_size // 2:
                        chunk = chunk[:newline_pos]
                        end = start + newline_pos
                    else:
                        # Last resort: break at any newline
                        newline_pos = chunk.rfind('\n')
                        if newline_pos > chunk_size // 2:
                            chunk = chunk[:newline_pos]
                            end = start + newline_pos
            
            chunks.append(chunk.strip())
            start = end - chunk_overlap
        
        return chunks
    
    def _generate_template_context(
        self,
        chunk_text: str,
        context_info: Dict[str, Any],
        chunk_index: int,
        total_chunks: int
    ) -> str:
        """Generate context using template."""
        # Build context based on source type
        source_type = context_info.get('source_type', 'document')
        
        if source_type == 'website':
            context = self._build_website_context(chunk_text, context_info, chunk_index, total_chunks)
        elif source_type == 'conversation':
            context = self._build_conversation_context(chunk_text, context_info, chunk_index, total_chunks)
        elif source_type == 'knowledge_base':
            context = self._build_knowledge_base_context(chunk_text, context_info, chunk_index, total_chunks)
        else:
            context = self._build_generic_context(chunk_text, context_info, chunk_index, total_chunks)
        
        return context
    
    def _build_website_context(
        self,
        chunk_text: str,
        context_info: Dict[str, Any],
        chunk_index: int,
        total_chunks: int
    ) -> str:
        """Build context for website chunks."""
        url = context_info.get('url', 'unknown')
        title = context_info.get('title', 'Untitled')
        domain = context_info.get('domain', 'website')
        
        context_parts = [
            f"This chunk is from a web page titled '{title}' at {url}.",
            f"This is part {chunk_index + 1} of {total_chunks} from this page."
        ]
        
        # Add section information if available
        if 'section' in context_info:
            context_parts.append(f"Section: {context_info['section']}.")
        
        # Add summary if available
        if 'summary' in context_info:
            context_parts.append(f"Page summary: {context_info['summary']}")
        
        context_parts.append(f"\nContent: {chunk_text}")
        
        return " ".join(context_parts)
    
    def _build_conversation_context(
        self,
        chunk_text: str,
        context_info: Dict[str, Any],
        chunk_index: int,
        total_chunks: int
    ) -> str:
        """Build context for conversation chunks."""
        conversation_id = context_info.get('conversation_id', 'unknown')
        platform = context_info.get('platform', 'chat')
        topic = context_info.get('topic', 'general discussion')
        participants = context_info.get('participants', [])
        
        context_parts = [
            f"This chunk is from a {platform} conversation (ID: {conversation_id}) about {topic}."
        ]
        
        if participants:
            context_parts.append(f"Participants: {', '.join(participants)}.")
        
        if 'timestamp' in context_info:
            context_parts.append(f"Time: {context_info['timestamp']}.")
        
        context_parts.append(f"Part {chunk_index + 1} of {total_chunks}.")
        context_parts.append(f"\nConversation excerpt: {chunk_text}")
        
        return " ".join(context_parts)
    
    def _build_knowledge_base_context(
        self,
        chunk_text: str,
        context_info: Dict[str, Any],
        chunk_index: int,
        total_chunks: int
    ) -> str:
        """Build context for knowledge base chunks."""
        filename = context_info.get('filename', 'document')
        category = context_info.get('category', 'general')
        doc_type = context_info.get('document_type', 'text')
        
        context_parts = [
            f"This chunk is from {filename} in the {category} category.",
            f"Document type: {doc_type}."
        ]
        
        # Add document summary if available
        if 'document_summary' in context_info:
            context_parts.append(f"Document summary: {context_info['document_summary']}")
        
        # Add section/chapter info
        if 'section' in context_info:
            context_parts.append(f"Section: {context_info['section']}.")
        elif 'chapter' in context_info:
            context_parts.append(f"Chapter: {context_info['chapter']}.")
        
        context_parts.append(f"Part {chunk_index + 1} of {total_chunks}.")
        context_parts.append(f"\nContent: {chunk_text}")
        
        return " ".join(context_parts)
    
    def _build_generic_context(
        self,
        chunk_text: str,
        context_info: Dict[str, Any],
        chunk_index: int,
        total_chunks: int
    ) -> str:
        """Build generic context for any document."""
        source = context_info.get('source', 'document')
        title = context_info.get('title', '')
        
        context_parts = [f"This chunk is from {source}"]
        
        if title:
            context_parts[0] += f" titled '{title}'"
        
        context_parts[0] += "."
        
        # Add any additional metadata
        for key, value in context_info.items():
            if key not in ['source', 'title', 'source_type'] and value:
                context_parts.append(f"{key.replace('_', ' ').title()}: {value}.")
        
        context_parts.append(f"Part {chunk_index + 1} of {total_chunks}.")
        context_parts.append(f"\nContent: {chunk_text}")
        
        return " ".join(context_parts)
    
    def _generate_llm_context(
        self,
        chunk_text: str,
        context_info: Dict[str, Any],
        chunk_index: int,
        total_chunks: int
    ) -> str:
        """Generate context using LLM."""
        # Check cache first
        cache_key = self._get_cache_key(chunk_text, context_info)
        if cache_key in self._context_cache:
            log_info("Using cached context")
            return self._context_cache[cache_key]
        
        # Generate prompt for LLM
        prompt = self._create_llm_prompt(chunk_text, context_info, chunk_index, total_chunks)
        
        try:
            # Check if we're already in an async context
            try:
                # Try to get the current event loop
                loop = asyncio.get_running_loop()
                # If we're in an async context, we can't use run_until_complete
                # Fall back to template generation for now
                log_warning("Already in async context, using template instead of LLM")
                return self._generate_template_context(chunk_text, context_info, chunk_index, total_chunks)
            except RuntimeError:
                # No event loop running, we can create one
                async def get_context():
                    response = await self.llm_model.acomplete(prompt)
                    return response.text
                
                context = asyncio.run(get_context())
                
                # Combine LLM context with chunk
                full_context = f"{context}\n\nChunk content: {chunk_text}"
                
                # Cache the result
                self._context_cache[cache_key] = full_context
                
                return full_context
            
        except Exception as e:
            log_warning(f"Failed to generate LLM context: {str(e)}. Using template instead.")
            return self._generate_template_context(chunk_text, context_info, chunk_index, total_chunks)
    
    def _create_llm_prompt(
        self,
        chunk_text: str,
        context_info: Dict[str, Any],
        chunk_index: int,
        total_chunks: int
    ) -> str:
        """Create prompt for LLM context generation."""
        prompt = f"""Generate a brief contextual description for this text chunk.

Document Information:
{self._format_context_info(context_info)}

Chunk Position: {chunk_index + 1} of {total_chunks}

Chunk Text:
{chunk_text[:500]}...

Provide a 1-2 sentence context that explains what this chunk is about and where it comes from. 
Focus on the key topic and source. Be concise and factual."""
        
        return prompt
    
    def _format_context_info(self, context_info: Dict[str, Any]) -> str:
        """Format context info for prompt."""
        lines = []
        for key, value in context_info.items():
            if value and key != 'source_type':
                formatted_key = key.replace('_', ' ').title()
                lines.append(f"- {formatted_key}: {value}")
        return '\n'.join(lines)
    
    def _create_chunk_metadata(
        self,
        context_info: Dict[str, Any],
        chunk_index: int,
        total_chunks: int
    ) -> Dict[str, Any]:
        """Create metadata for a chunk."""
        metadata = context_info.copy()
        metadata.update({
            'chunk_index': chunk_index,
            'total_chunks': total_chunks,
            'has_context': True,
            'indexed_at': datetime.utcnow().isoformat()
        })
        return metadata
    
    def _get_cache_key(self, chunk_text: str, context_info: Dict[str, Any]) -> str:
        """Generate cache key for context."""
        # Create a stable hash from chunk and context
        content = f"{chunk_text}{str(sorted(context_info.items()))}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear the context cache."""
        self._context_cache.clear()
        log_info("Context cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'size': len(self._context_cache),
            'memory_bytes': sum(len(v.encode()) for v in self._context_cache.values())
        }