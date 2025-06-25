"""Advanced reranking module for RAG results."""

import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from datetime import datetime
import asyncio

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    CrossEncoder = None

import openai

from src.utils.logging import log_info, log_error, log_warning
from src.core.config import get_settings


@dataclass
class RerankResult:
    """Container for reranked search result."""
    content: str
    original_score: float
    rerank_score: float
    combined_score: float
    metadata: Dict[str, Any]
    relevance_explanation: Optional[str] = None


class ResultReranker:
    """Handles advanced reranking of search results."""
    
    def __init__(self, use_cross_encoder: bool = True, use_llm_rerank: bool = False):
        """Initialize the reranker.
        
        Args:
            use_cross_encoder: Whether to use cross-encoder for reranking
            use_llm_rerank: Whether to use LLM for reranking
        """
        self.settings = get_settings()
        self.use_cross_encoder = use_cross_encoder
        self.use_llm_rerank = use_llm_rerank
        
        # Initialize cross-encoder if requested
        self.cross_encoder = None
        if use_cross_encoder and CROSS_ENCODER_AVAILABLE:
            try:
                # Use a lightweight cross-encoder model
                self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
                log_info("Cross-encoder initialized for reranking")
            except Exception as e:
                log_warning(f"Failed to initialize cross-encoder: {str(e)}")
                self.use_cross_encoder = False
        elif use_cross_encoder and not CROSS_ENCODER_AVAILABLE:
            log_warning("Cross-encoder requested but sentence-transformers not installed. Install with: pip install sentence-transformers torch")
            self.use_cross_encoder = False
        
        # Initialize OpenAI client for LLM reranking
        if use_llm_rerank:
            openai.api_key = self.settings.openai_api_key or self.settings.llm_api_key
    
    async def rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None
    ) -> List[RerankResult]:
        """Rerank search results based on relevance to query.
        
        Args:
            query: The search query
            results: List of search results with content and metadata
            context: Optional context for task-specific reranking
            top_k: Number of top results to return
            
        Returns:
            List of reranked results
        """
        if not results:
            return []
        
        log_info(f"Reranking {len(results)} results for query: {query[:50]}...")
        
        # Step 1: Cross-encoder reranking
        if self.use_cross_encoder and self.cross_encoder:
            cross_encoder_scores = self._get_cross_encoder_scores(query, results)
        else:
            cross_encoder_scores = [0.5] * len(results)
        
        # Step 2: Metadata-based scoring
        metadata_scores = self._get_metadata_scores(results, context)
        
        # Step 3: LLM-based reranking (if enabled and for top results only)
        llm_scores = [0.5] * len(results)
        if self.use_llm_rerank and len(results) <= 10:
            llm_scores = await self._get_llm_scores(query, results, context)
        
        # Step 4: Combine scores
        reranked_results = []
        for i, result in enumerate(results):
            original_score = result.get('score', 0.5)
            
            # Weighted combination of scores
            combined_score = (
                original_score * 0.3 +  # Original retrieval score
                cross_encoder_scores[i] * 0.4 +  # Cross-encoder score
                metadata_scores[i] * 0.2 +  # Metadata-based score
                llm_scores[i] * 0.1  # LLM reranking score
            )
            
            rerank_result = RerankResult(
                content=result.get('content', ''),
                original_score=original_score,
                rerank_score=cross_encoder_scores[i],
                combined_score=combined_score,
                metadata=result.get('metadata', {}),
                relevance_explanation=result.get('relevance_explanation')
            )
            reranked_results.append(rerank_result)
        
        # Sort by combined score
        reranked_results.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Return top_k if specified
        if top_k:
            reranked_results = reranked_results[:top_k]
        
        log_info(f"Reranking complete. Top result score: {reranked_results[0].combined_score:.3f}")
        
        return reranked_results
    
    def _get_cross_encoder_scores(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> List[float]:
        """Get cross-encoder scores for query-document pairs."""
        if not self.cross_encoder:
            return [0.5] * len(results)
        
        try:
            # Prepare query-document pairs
            pairs = [[query, result.get('content', '')] for result in results]
            
            # Get scores from cross-encoder
            scores = self.cross_encoder.predict(pairs)
            
            # Normalize scores to [0, 1]
            min_score = min(scores)
            max_score = max(scores)
            if max_score > min_score:
                normalized_scores = [(s - min_score) / (max_score - min_score) for s in scores]
            else:
                normalized_scores = [0.5] * len(scores)
            
            return normalized_scores
            
        except Exception as e:
            log_error(f"Cross-encoder scoring failed: {str(e)}")
            return [0.5] * len(results)
    
    def _get_metadata_scores(
        self,
        results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[float]:
        """Calculate scores based on metadata and context."""
        scores = []
        
        for result in results:
            score = 0.5  # Base score
            metadata = result.get('metadata', {})
            
            # Boost for recency
            if 'created_at' in metadata or 'indexed_at' in metadata:
                date_str = metadata.get('created_at') or metadata.get('indexed_at')
                try:
                    # Parse date and calculate recency score
                    doc_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    days_old = (datetime.now() - doc_date.replace(tzinfo=None)).days
                    recency_score = max(0, 1 - (days_old / 365))  # Decay over a year
                    score += recency_score * 0.2
                except:
                    pass
            
            # Boost for source type preferences
            source_type = metadata.get('source_type', '')
            if context and 'preferred_sources' in context:
                if source_type in context['preferred_sources']:
                    score += 0.3
            
            # Boost for specific collections
            collection = metadata.get('collection', '')
            if context and 'preferred_collections' in context:
                if collection in context['preferred_collections']:
                    score += 0.2
            
            # Boost for high-quality sources
            if metadata.get('is_verified') or metadata.get('is_official'):
                score += 0.2
            
            # Boost for documents with summaries or descriptions
            if metadata.get('summary') or metadata.get('description'):
                score += 0.1
            
            # Cap at 1.0
            scores.append(min(1.0, score))
        
        return scores
    
    async def _get_llm_scores(
        self,
        query: str,
        results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[float]:
        """Get LLM-based relevance scores."""
        if not self.use_llm_rerank:
            return [0.5] * len(results)
        
        try:
            # Prepare prompt for batch scoring
            prompt = self._create_llm_rerank_prompt(query, results, context)
            
            response = await openai.ChatCompletion.acreate(
                model=self.settings.context_generation_model or "gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a relevance scoring expert. Score each document's relevance to the query on a scale of 0-10."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1
            )
            
            # Parse scores from response
            scores_text = response.choices[0].message.content
            scores = self._parse_llm_scores(scores_text, len(results))
            
            # Normalize to [0, 1]
            normalized_scores = [s / 10.0 for s in scores]
            
            return normalized_scores
            
        except Exception as e:
            log_error(f"LLM reranking failed: {str(e)}")
            return [0.5] * len(results)
    
    def _create_llm_rerank_prompt(
        self,
        query: str,
        results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create prompt for LLM reranking."""
        prompt_parts = [f"Query: {query}\n"]
        
        if context:
            prompt_parts.append(f"Context: {context.get('task_description', 'General search')}\n")
        
        prompt_parts.append("Documents to score:\n")
        
        for i, result in enumerate(results):
            content = result.get('content', '')[:500]  # Limit content length
            metadata = result.get('metadata', {})
            
            prompt_parts.append(f"\nDocument {i+1}:")
            if 'source' in metadata:
                prompt_parts.append(f"Source: {metadata['source']}")
            prompt_parts.append(f"Content: {content}...")
        
        prompt_parts.append("\nProvide relevance scores (0-10) for each document in the format:")
        prompt_parts.append("Document 1: [score]")
        prompt_parts.append("Document 2: [score]")
        prompt_parts.append("...")
        
        return "\n".join(prompt_parts)
    
    def _parse_llm_scores(self, scores_text: str, expected_count: int) -> List[float]:
        """Parse scores from LLM response."""
        scores = []
        
        try:
            lines = scores_text.strip().split('\n')
            for line in lines:
                if 'Document' in line and ':' in line:
                    score_part = line.split(':')[-1].strip()
                    # Extract numeric score
                    score = float(''.join(c for c in score_part if c.isdigit() or c == '.'))
                    scores.append(min(10, max(0, score)))  # Clamp to [0, 10]
        except:
            log_warning("Failed to parse LLM scores, using defaults")
        
        # Ensure we have the right number of scores
        while len(scores) < expected_count:
            scores.append(5.0)  # Default middle score
        
        return scores[:expected_count]
    
    def reciprocal_rank_fusion(
        self,
        result_lists: List[List[Dict[str, Any]]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """Fuse multiple result lists using Reciprocal Rank Fusion.
        
        Args:
            result_lists: List of result lists from different retrievers
            k: Parameter for RRF (default 60)
            
        Returns:
            Fused and reranked results
        """
        # Calculate RRF scores
        doc_scores = {}
        
        for result_list in result_lists:
            for rank, result in enumerate(result_list):
                # Use content as document identifier
                doc_id = result.get('content', '')[:100]  # First 100 chars as ID
                
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        'score': 0,
                        'result': result
                    }
                
                # Add RRF score
                doc_scores[doc_id]['score'] += 1 / (k + rank + 1)
        
        # Sort by RRF score
        sorted_results = sorted(
            doc_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        # Extract results with RRF scores
        fused_results = []
        for item in sorted_results:
            result = item['result'].copy()
            result['rrf_score'] = item['score']
            fused_results.append(result)
        
        return fused_results