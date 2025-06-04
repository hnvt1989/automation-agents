"""Performance monitoring for ChromaDB operations."""
import time
from typing import Dict, Any, Callable
from functools import wraps
from collections import defaultdict
import threading

from src.utils.logging import log_info, log_warning


class PerformanceMonitor:
    """Monitor and track performance metrics for ChromaDB operations."""
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'errors': 0
        })
        self._lock = threading.Lock()
    
    def track_operation(self, operation_name: str):
        """Decorator to track performance of an operation.
        
        Args:
            operation_name: Name of the operation to track
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                error_occurred = False
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    error_occurred = True
                    raise e
                finally:
                    elapsed_time = time.time() - start_time
                    self._record_metric(operation_name, elapsed_time, error_occurred)
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                error_occurred = False
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    error_occurred = True
                    raise e
                finally:
                    elapsed_time = time.time() - start_time
                    self._record_metric(operation_name, elapsed_time, error_occurred)
            
            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return wrapper
        
        return decorator
    
    def _record_metric(self, operation_name: str, elapsed_time: float, error_occurred: bool):
        """Record a metric for an operation.
        
        Args:
            operation_name: Name of the operation
            elapsed_time: Time taken for the operation
            error_occurred: Whether an error occurred
        """
        with self._lock:
            metric = self.metrics[operation_name]
            metric['count'] += 1
            metric['total_time'] += elapsed_time
            metric['min_time'] = min(metric['min_time'], elapsed_time)
            metric['max_time'] = max(metric['max_time'], elapsed_time)
            if error_occurred:
                metric['errors'] += 1
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all recorded metrics.
        
        Returns:
            Dictionary of metrics by operation name
        """
        with self._lock:
            # Create a copy with calculated averages
            result = {}
            for op_name, metric in self.metrics.items():
                result[op_name] = {
                    'count': metric['count'],
                    'total_time': metric['total_time'],
                    'average_time': metric['total_time'] / metric['count'] if metric['count'] > 0 else 0,
                    'min_time': metric['min_time'] if metric['min_time'] != float('inf') else 0,
                    'max_time': metric['max_time'],
                    'errors': metric['errors'],
                    'error_rate': metric['errors'] / metric['count'] if metric['count'] > 0 else 0
                }
            return result
    
    def log_metrics(self):
        """Log all metrics to the logger."""
        metrics = self.get_metrics()
        
        if not metrics:
            log_info("No performance metrics recorded")
            return
        
        log_info("=== ChromaDB Performance Metrics ===")
        for op_name, metric in metrics.items():
            log_info(f"\n{op_name}:")
            log_info(f"  Total calls: {metric['count']}")
            log_info(f"  Average time: {metric['average_time']:.3f}s")
            log_info(f"  Min time: {metric['min_time']:.3f}s")
            log_info(f"  Max time: {metric['max_time']:.3f}s")
            log_info(f"  Error rate: {metric['error_rate']:.1%}")
    
    def check_performance_thresholds(self, thresholds: Dict[str, float]):
        """Check if any operations exceed performance thresholds.
        
        Args:
            thresholds: Dictionary of operation names to time thresholds in seconds
        """
        metrics = self.get_metrics()
        
        for op_name, threshold in thresholds.items():
            if op_name in metrics:
                avg_time = metrics[op_name]['average_time']
                if avg_time > threshold:
                    log_warning(
                        f"Performance warning: {op_name} average time "
                        f"({avg_time:.3f}s) exceeds threshold ({threshold}s)"
                    )


# Global performance monitor instance
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return _performance_monitor


# Import asyncio only if needed
import asyncio