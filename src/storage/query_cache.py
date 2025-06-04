"""Query caching for ChromaDB operations."""
import hashlib
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from collections import OrderedDict
import threading

from src.utils.logging import log_info, log_debug


class QueryCache:
    """LRU cache for ChromaDB query results."""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        """Initialize query cache.
        
        Args:
            max_size: Maximum number of cached queries
            ttl_seconds: Time-to-live for cached results in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
    
    def _generate_cache_key(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int,
        where: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a cache key for a query.
        
        Args:
            collection_name: Name of the collection
            query_texts: Query texts
            n_results: Number of results
            where: Metadata filter
            
        Returns:
            Cache key string
        """
        # Create a deterministic string representation
        key_data = {
            'collection': collection_name,
            'queries': sorted(query_texts),  # Sort for consistency
            'n_results': n_results,
            'where': where or {}
        }
        
        # Convert to JSON and hash
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int,
        where: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Get cached query results.
        
        Args:
            collection_name: Name of the collection
            query_texts: Query texts
            n_results: Number of results
            where: Metadata filter
            
        Returns:
            Cached results or None if not found/expired
        """
        cache_key = self._generate_cache_key(collection_name, query_texts, n_results, where)
        
        with self._lock:
            if cache_key in self.cache:
                result, timestamp = self.cache[cache_key]
                
                # Check if expired
                if time.time() - timestamp > self.ttl_seconds:
                    del self.cache[cache_key]
                    self._stats['misses'] += 1
                    log_debug(f"Cache miss (expired): {cache_key[:8]}...")
                    return None
                
                # Move to end (most recently used)
                self.cache.move_to_end(cache_key)
                self._stats['hits'] += 1
                log_debug(f"Cache hit: {cache_key[:8]}...")
                return result
            
            self._stats['misses'] += 1
            log_debug(f"Cache miss: {cache_key[:8]}...")
            return None
    
    def put(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int,
        results: Any,
        where: Optional[Dict[str, Any]] = None
    ):
        """Store query results in cache.
        
        Args:
            collection_name: Name of the collection
            query_texts: Query texts
            n_results: Number of results
            results: Query results to cache
            where: Metadata filter
        """
        cache_key = self._generate_cache_key(collection_name, query_texts, n_results, where)
        
        with self._lock:
            # Remove oldest item if at capacity
            if len(self.cache) >= self.max_size and cache_key not in self.cache:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self._stats['evictions'] += 1
                log_debug(f"Evicted oldest cache entry: {oldest_key[:8]}...")
            
            # Store with timestamp
            self.cache[cache_key] = (results, time.time())
            log_debug(f"Cached query: {cache_key[:8]}...")
    
    def clear(self):
        """Clear all cached queries."""
        with self._lock:
            self.cache.clear()
            log_info("Query cache cleared")
    
    def invalidate_collection(self, collection_name: str):
        """Invalidate all cached queries for a specific collection.
        
        Args:
            collection_name: Name of the collection to invalidate
        """
        with self._lock:
            keys_to_remove = []
            for key in self.cache:
                # Since we hash the keys, we can't directly check collection name
                # In a production system, we'd maintain a reverse index
                # For now, we'll clear all cache when a collection is modified
                keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.cache[key]
            
            if keys_to_remove:
                log_info(f"Invalidated {len(keys_to_remove)} cached queries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary of cache statistics
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'hit_rate': hit_rate,
                'total_requests': total_requests
            }
    
    def log_stats(self):
        """Log cache statistics."""
        stats = self.get_stats()
        log_info(
            f"Query Cache Stats - Size: {stats['size']}/{stats['max_size']}, "
            f"Hit Rate: {stats['hit_rate']:.1%}, "
            f"Total Requests: {stats['total_requests']}"
        )