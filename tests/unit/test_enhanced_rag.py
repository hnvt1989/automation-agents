"""Tests for enhanced RAG queries and context ranking."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any, Tuple
import asyncio

from src.agents.task_brainstorm import (
    extract_key_terms,
    generate_search_queries,
    deduplicate_contexts,
    calculate_relevance_score,
    rank_contexts_by_relevance,
    get_enhanced_rag_context
)


class TestEnhancedRAGQueries:
    """Test multiple search strategies for RAG queries."""
    
    def test_extract_key_terms(self):
        """Test extracting key terms from task title."""
        test_cases = [
            {
                'title': 'Explore weekly Automated Test coverage Sync to TestRail',
                'expected': ['explore', 'weekly', 'automated', 'test', 'coverage', 'sync', 'testrail']
            },
            {
                'title': 'Implement API integration with GitHub',
                'expected': ['implement', 'api', 'integration', 'github']
            },
            {
                'title': 'Fix the bug in user authentication',
                'expected': ['fix', 'bug', 'user', 'authentication']
            }
        ]
        
        for case in test_cases:
            result = extract_key_terms(case['title'])
            assert set(result) == set(case['expected'])
    
    def test_generate_search_queries(self):
        """Test generating multiple search queries from task info."""
        task_info = {
            'basic_task': {
                'id': '111025',
                'title': 'Explore weekly Automated Test coverage Sync to TestRail',
                'tags': ['testing', 'integration'],
                'priority': 'high'
            },
            'task_detail': {
                'objective': 'Integrate test coverage reports with TestRail',
                'tasks': [
                    'Research TestRail API',
                    'Build sync mechanism',
                    'Schedule weekly runs'
                ]
            }
        }
        
        queries = generate_search_queries(task_info)
        
        # Should have multiple query types
        assert len(queries) >= 4
        
        # Check for different query strategies
        assert task_info['basic_task']['title'] in queries  # Direct title
        assert any('testing integration' in q.lower() for q in queries)  # Tags + title
        assert any('testrail' in q.lower() and 'sync' in q.lower() for q in queries)  # Key terms
        assert any('integrate test coverage' in q.lower() for q in queries)  # From objective
    
    @pytest.mark.asyncio
    async def test_enhanced_rag_context_retrieval(self):
        """Test the full enhanced RAG context retrieval."""
        # Mock RAG agent
        mock_rag_agent = AsyncMock()
        
        # Mock search results with scores
        mock_results = [
            {
                'content': 'TestRail API documentation for test management',
                'metadata': {'source': 'api_docs.md'},
                'score': 0.95
            },
            {
                'content': 'Weekly automation scheduling best practices',
                'metadata': {'source': 'automation_guide.md'},
                'score': 0.85
            },
            {
                'content': 'Test coverage reporting formats and standards',
                'metadata': {'source': 'testing_standards.md'},
                'score': 0.90
            }
        ]
        
        mock_rag_agent.search_with_scores = AsyncMock(return_value=mock_results)
        
        task_info = {
            'basic_task': {
                'id': '111025',
                'title': 'Explore weekly Automated Test coverage Sync to TestRail',
                'tags': ['testing']
            }
        }
        
        with patch('src.agents.task_brainstorm.RAGAgent', return_value=mock_rag_agent):
            contexts = await get_enhanced_rag_context(task_info, max_contexts=3)
        
        # Should have retrieved contexts
        assert len(contexts) > 0
        assert len(contexts) <= 3
        
        # Should be ranked by relevance
        assert all(contexts[i]['score'] >= contexts[i+1]['score'] 
                  for i in range(len(contexts)-1))


class TestContextRanking:
    """Test context ranking and relevance scoring."""
    
    def test_calculate_relevance_score(self):
        """Test relevance score calculation."""
        task_info = {
            'basic_task': {
                'title': 'Implement API integration with GitHub',
                'tags': ['api', 'github']
            }
        }
        
        test_contexts = [
            {
                'content': 'GitHub API authentication and rate limiting guide',
                'expected_score_range': (0.7, 1.0)  # High relevance
            },
            {
                'content': 'General API design principles and best practices',
                'expected_score_range': (0.4, 0.7)  # Medium relevance
            },
            {
                'content': 'Database optimization techniques for large datasets',
                'expected_score_range': (0.0, 0.3)  # Low relevance
            }
        ]
        
        for context in test_contexts:
            score = calculate_relevance_score(
                context['content'],
                task_info
            )
            min_score, max_score = context['expected_score_range']
            assert min_score <= score <= max_score, \
                f"Score {score} not in range {context['expected_score_range']} for: {context['content'][:50]}..."
    
    def test_deduplicate_contexts(self):
        """Test deduplication of similar contexts."""
        contexts = [
            {
                'content': 'TestRail API documentation for test case management',
                'score': 0.9,
                'metadata': {'source': 'doc1.md'}
            },
            {
                'content': 'TestRail API documentation for test case management system',  # Very similar
                'score': 0.85,
                'metadata': {'source': 'doc2.md'}
            },
            {
                'content': 'Weekly scheduling patterns for CI/CD pipelines',
                'score': 0.8,
                'metadata': {'source': 'doc3.md'}
            },
            {
                'content': 'Weekly scheduling patterns for continuous integration',  # Similar
                'score': 0.75,
                'metadata': {'source': 'doc4.md'}
            },
            {
                'content': 'Authentication best practices for REST APIs',
                'score': 0.7,
                'metadata': {'source': 'doc5.md'}
            }
        ]
        
        # Deduplicate with similarity threshold
        unique_contexts = deduplicate_contexts(contexts, similarity_threshold=0.7)
        
        # Should have removed similar contexts
        assert len(unique_contexts) < len(contexts)
        assert len(unique_contexts) == 3  # Should keep 3 unique contexts
        
        # Should keep highest scoring versions
        assert any('TestRail API documentation' in ctx['content'] for ctx in unique_contexts)
        assert any('Weekly scheduling' in ctx['content'] for ctx in unique_contexts)
        assert any('Authentication best practices' in ctx['content'] for ctx in unique_contexts)
    
    def test_rank_contexts_by_relevance(self):
        """Test ranking contexts by multiple factors."""
        task_info = {
            'basic_task': {
                'title': 'Implement GitHub API integration',
                'tags': ['api', 'github', 'integration']
            },
            'task_detail': {
                'objective': 'Create a robust GitHub API client'
            }
        }
        
        contexts = [
            {
                'content': 'Database connection pooling strategies',
                'score': 0.9,  # High score but low relevance
                'metadata': {'source': 'db_guide.md'}
            },
            {
                'content': 'GitHub API rate limiting and authentication',
                'score': 0.7,  # Lower score but high relevance
                'metadata': {'source': 'github_api.md'}
            },
            {
                'content': 'REST API integration patterns and best practices',
                'score': 0.8,  # Medium score and relevance
                'metadata': {'source': 'api_patterns.md'}
            }
        ]
        
        # Rank by relevance (not just score)
        ranked = rank_contexts_by_relevance(contexts, task_info)
        
        # GitHub-specific content should rank highest despite lower initial score
        assert 'GitHub API' in ranked[0]['content']
        # API patterns should be second
        assert 'REST API' in ranked[1]['content']
        # Database content should be last despite high score
        assert 'Database' in ranked[2]['content']
    
    @pytest.mark.asyncio
    async def test_multiple_search_strategies(self):
        """Test that multiple search strategies produce different results."""
        mock_rag_agent = AsyncMock()
        
        # Track queries made
        queries_made = []
        
        async def mock_search(query, n_results=5):
            queries_made.append(query)
            # Return different results for different query types
            if 'tags:' in query.lower():
                return [{'content': f'Result for tag query: {query}', 'score': 0.8}]
            elif len(query.split()) <= 3:  # Key terms query
                return [{'content': f'Result for key terms: {query}', 'score': 0.7}]
            else:  # Full title or semantic query
                return [{'content': f'Result for full query: {query}', 'score': 0.9}]
        
        mock_rag_agent.search_with_scores = mock_search
        
        task_info = {
            'basic_task': {
                'title': 'Build automated testing framework',
                'tags': ['testing', 'automation']
            }
        }
        
        with patch('src.agents.task_brainstorm.RAGAgent', return_value=mock_rag_agent):
            contexts = await get_enhanced_rag_context(task_info)
        
        # Should have made multiple different queries
        assert len(queries_made) >= 3
        assert len(set(queries_made)) >= 3  # Different queries
        
        # Check different query types were used
        assert any('testing automation' in q.lower() for q in queries_made)  # Tag-based
        assert any(len(q.split()) <= 3 for q in queries_made)  # Key terms
        assert task_info['basic_task']['title'] in queries_made  # Direct title


class TestRAGIntegration:
    """Test integration of enhanced RAG with brainstorming."""
    
    @pytest.mark.asyncio
    async def test_brainstorm_with_enhanced_rag(self):
        """Test that brainstorming uses enhanced RAG context."""
        from src.agents.task_brainstorm import generate_brainstorm_content
        
        # Mock enhanced RAG function
        mock_contexts = [
            {
                'content': 'Highly relevant API documentation',
                'score': 0.95,
                'metadata': {'source': 'api.md'}
            },
            {
                'content': 'Best practices for integration',
                'score': 0.85,
                'metadata': {'source': 'guide.md'}
            }
        ]
        
        task_info = {
            'basic_task': {
                'id': 'TEST-1',
                'title': 'Test Task',
                'status': 'pending'
            }
        }
        
        with patch('src.agents.task_brainstorm.get_enhanced_rag_context', 
                  return_value=mock_contexts) as mock_get_context:
            with patch('src.agents.task_brainstorm.Agent') as mock_agent:
                # Mock LLM response
                mock_llm_response = Mock()
                mock_llm_response.data = {
                    'overview': 'Test overview',
                    'considerations': ['Consider 1'],
                    'approaches': ['Approach 1'],
                    'risks': ['Risk 1'],
                    'recommendations': ['Recommendation 1']
                }
                
                mock_agent_instance = Mock()
                mock_agent_instance.run = AsyncMock(return_value=mock_llm_response)
                mock_agent.return_value = mock_agent_instance
                
                # Generate brainstorm
                result = await generate_brainstorm_content(task_info)
                
                # Should have called enhanced RAG
                mock_get_context.assert_called_once()
                
                # Should include RAG context in result
                assert result is not None
                assert len(result.rag_context) > 0
                assert any('API documentation' in ctx for ctx in result.rag_context)