"""Enhanced RAG functionality with multiple search strategies and context ranking."""
from typing import List, Dict, Any, Tuple, Optional
import re
from difflib import SequenceMatcher
import asyncio
from collections import defaultdict

from src.utils.logging import log_info, log_warning, log_error


def extract_key_terms(text: str) -> List[str]:
    """Extract key terms from text, removing stop words and common words."""
    # Convert to lowercase and split
    words = text.lower().split()
    
    # Common stop words to filter out
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'must', 'can', 'shall'
    }
    
    # Extract meaningful terms
    key_terms = []
    for word in words:
        # Remove punctuation
        word = re.sub(r'[^\w\s]', '', word)
        
        # Skip if empty, too short, or stop word
        if word and len(word) > 2 and word not in stop_words:
            key_terms.append(word)
    
    return key_terms


def generate_search_queries(task_info: Dict[str, Any]) -> List[str]:
    """Generate multiple search queries using different strategies."""
    queries = []
    basic_task = task_info.get('basic_task', {})
    task_detail = task_info.get('task_detail', {})
    
    # Strategy 1: Direct title search
    title = basic_task.get('title', '')
    if title:
        queries.append(title)
    
    # Strategy 2: Tags + title combination
    tags = basic_task.get('tags', [])
    if tags and title:
        tag_string = ' '.join(tags)
        queries.append(f"{tag_string} {title}")
    
    # Strategy 3: Key terms only
    if title:
        key_terms = extract_key_terms(title)
        if key_terms:
            queries.append(' '.join(key_terms[:5]))  # Limit to top 5 terms
    
    # Strategy 4: Objective-based search
    objective = task_detail.get('objective', '')
    if objective:
        queries.append(objective)
    
    # Strategy 5: Subtasks search (limited)
    subtasks = task_detail.get('tasks', [])
    for subtask in subtasks[:2]:  # Only first 2 subtasks
        if subtask:
            queries.append(subtask)
    
    # Strategy 6: Combined key concepts
    if title and objective:
        title_terms = extract_key_terms(title)[:3]
        obj_terms = extract_key_terms(objective)[:2]
        combined = title_terms + obj_terms
        if combined:
            queries.append(' '.join(combined))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        if q and q not in seen:
            seen.add(q)
            unique_queries.append(q)
    
    return unique_queries


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts using sequence matching."""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def deduplicate_contexts(contexts: List[Dict[str, Any]], 
                        similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
    """Remove duplicate contexts based on content similarity."""
    if not contexts:
        return []
    
    # Sort by score descending (keep highest scoring versions)
    sorted_contexts = sorted(contexts, key=lambda x: x.get('score', 0), reverse=True)
    
    unique_contexts = []
    for context in sorted_contexts:
        # Check if similar to any already selected context
        is_duplicate = False
        for unique_ctx in unique_contexts:
            similarity = calculate_similarity(
                context.get('content', ''),
                unique_ctx.get('content', '')
            )
            if similarity >= similarity_threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_contexts.append(context)
    
    return unique_contexts


def calculate_relevance_score(content: str, task_info: Dict[str, Any]) -> float:
    """Calculate relevance score of content to task."""
    score = 0.0
    content_lower = content.lower()
    
    basic_task = task_info.get('basic_task', {})
    task_detail = task_info.get('task_detail', {})
    
    # Extract all relevant terms from task
    title = basic_task.get('title', '').lower()
    tags = [t.lower() for t in basic_task.get('tags', [])]
    objective = task_detail.get('objective', '').lower()
    
    # Title terms matching (highest weight)
    title_terms = extract_key_terms(title)
    title_matches = sum(1 for term in title_terms if term in content_lower)
    if title_terms:
        # Give partial credit for partial matches
        match_ratio = title_matches / len(title_terms)
        score += match_ratio * 0.5
    
    # Tag matching (important for categorization)
    tag_matches = sum(1 for tag in tags if tag in content_lower)
    if tags:
        score += (tag_matches / len(tags)) * 0.4
    
    # Objective matching
    if objective:
        obj_terms = extract_key_terms(objective)
        obj_matches = sum(1 for term in obj_terms if term in content_lower)
        if obj_terms:
            score += (obj_matches / len(obj_terms)) * 0.3
    
    # Bonus for exact phrase matches
    if title and title in content_lower:
        score += 0.2
    
    # Check for related terms (synonyms/related concepts)
    related_terms = {
        'api': ['interface', 'endpoint', 'rest', 'restful'],
        'github': ['git', 'repository', 'repo'],
        'integration': ['integrate', 'connect', 'sync'],
        'authentication': ['auth', 'oauth', 'token'],
        'database': ['db', 'sql', 'storage']
    }
    
    # Check for related terms
    for term in title_terms + tags:
        if term in related_terms:
            for related in related_terms[term]:
                if related in content_lower:
                    score += 0.05
    
    # Partial credit for general relevance
    # If content mentions key domain terms but not specific ones
    general_terms = ['design', 'principles', 'best practices', 'guide', 'documentation']
    if any(term in content_lower for term in general_terms):
        # Check if at least one task term is present
        if any(term in content_lower for term in title_terms + tags):
            score += 0.15
    
    return min(1.0, score)  # Cap at 1.0


def rank_contexts_by_relevance(contexts: List[Dict[str, Any]], 
                              task_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Rank contexts by relevance to task, not just by retrieval score."""
    ranked_contexts = []
    
    for context in contexts:
        # Calculate task-specific relevance
        relevance_score = calculate_relevance_score(
            context.get('content', ''),
            task_info
        )
        
        # Combine with retrieval score (if available)
        retrieval_score = context.get('score', 0.5)
        
        # Weighted combination: relevance matters more than retrieval score
        combined_score = (relevance_score * 0.7) + (retrieval_score * 0.3)
        
        # Add combined score to context
        ranked_context = context.copy()
        ranked_context['relevance_score'] = relevance_score
        ranked_context['combined_score'] = combined_score
        ranked_contexts.append(ranked_context)
    
    # Sort by combined score
    ranked_contexts.sort(key=lambda x: x['combined_score'], reverse=True)
    
    return ranked_contexts


async def search_with_scores(rag_agent, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """Search RAG and return results with scores."""
    try:
        # Use the RAG agent's search tool
        result = await rag_agent.run(f"search knowledge base for: {query}")
        
        # Parse results and extract scores
        contexts = []
        if hasattr(result, 'data') and result.data:
            result_text = str(result.data)
            
            # Parse the formatted results
            if "No results found" not in result_text:
                # Split by result separator
                result_blocks = result_text.split("\n---\n")
                
                for block in result_blocks:
                    if not block.strip():
                        continue
                    
                    # Extract relevance score
                    score = 0.5  # Default
                    score_match = re.search(r'relevance:\s*([0-9.]+)', block)
                    if score_match:
                        score = float(score_match.group(1))
                    
                    # Extract source
                    source = 'knowledge_base'
                    source_match = re.search(r'Source:\s*(.+?)\n', block)
                    if source_match:
                        source = source_match.group(1).strip()
                    
                    # Extract content
                    content = ''
                    content_match = re.search(r'Content:\s*(.+?)(?:\n|$)', block, re.DOTALL)
                    if content_match:
                        content = content_match.group(1).strip()
                    
                    if content:
                        contexts.append({
                            'content': content,
                            'score': score,
                            'metadata': {'source': source}
                        })
        
        return contexts
    except Exception as e:
        log_error(f"RAG search failed for query '{query}': {str(e)}")
        return []


async def get_enhanced_rag_context(task_info: Dict[str, Any], 
                                  max_contexts: int = 5,
                                  rag_agent = None) -> List[Dict[str, Any]]:
    """Get enhanced RAG context using multiple search strategies."""
    log_info("Starting enhanced RAG context retrieval")
    
    # Generate diverse search queries
    queries = generate_search_queries(task_info)
    log_info(f"Generated {len(queries)} search queries")
    
    if not rag_agent:
        # Import here to avoid circular dependencies
        from src.agents.rag import RAGAgent
        from pydantic_ai.models.openai import OpenAIModel
        from pydantic_ai.providers.openai import OpenAIProvider
        from src.core.config import get_settings
        
        try:
            settings = get_settings()
            provider = OpenAIProvider(
                base_url=settings.base_url,
                api_key=settings.llm_api_key
            )
            model = OpenAIModel('gpt-4o-mini', provider=provider)
            rag_agent = RAGAgent(model)
        except Exception as e:
            log_error(f"Failed to initialize RAG agent: {str(e)}")
            return []
    
    # Search with each query
    all_contexts = []
    for query in queries[:5]:  # Limit to prevent too many API calls
        try:
            results = await search_with_scores(rag_agent, query, n_results=3)
            all_contexts.extend(results)
        except Exception as e:
            log_warning(f"Search failed for query '{query}': {str(e)}")
            continue
    
    if not all_contexts:
        log_warning("No contexts retrieved from RAG")
        return []
    
    # Deduplicate similar contexts
    unique_contexts = deduplicate_contexts(all_contexts)
    log_info(f"Deduplicated {len(all_contexts)} contexts to {len(unique_contexts)} unique")
    
    # Rank by relevance to task
    ranked_contexts = rank_contexts_by_relevance(unique_contexts, task_info)
    
    # Return top N contexts
    top_contexts = ranked_contexts[:max_contexts]
    log_info(f"Returning top {len(top_contexts)} contexts")
    
    return top_contexts