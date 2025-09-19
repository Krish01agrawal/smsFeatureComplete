"""
Cache Manager for SMS Transaction Analysis
Provides high-performance caching for 10,000+ users with Redis and in-memory fallback.
"""

import time
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Union
from functools import wraps
import threading
from collections import OrderedDict

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available, using in-memory cache only")

try:
    from .config import get_config
except ImportError:
    from config import get_config

logger = logging.getLogger(__name__)

class CacheManager:
    """High-performance cache manager with Redis and in-memory fallback."""
    
    def __init__(self):
        """Initialize cache manager."""
        self.redis_client = None
        self.memory_cache = OrderedDict()
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        self.lock = threading.Lock()
        
        # Configuration
        self.cache_enabled = get_config('caching.enabled', True)
        self.default_ttl = get_config('caching.default_ttl', 3600)
        self.max_memory_size = get_config('performance_limits.memory_limit_mb', 2048) * 1024 * 1024  # Convert to bytes
        
        # Initialize Redis if available
        if self.cache_enabled and REDIS_AVAILABLE:
            self._init_redis()
        
        logger.info("Cache Manager initialized")
    
    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            redis_host = get_config('caching.redis_host', 'localhost')
            redis_port = get_config('caching.redis_port', 6379)
            redis_db = get_config('caching.redis_db', 0)
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis cache connected: {redis_host}:{redis_port}")
            
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, using in-memory cache only")
            self.redis_client = None
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments."""
        # Create a string representation of arguments
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            key_parts.append(str(arg))
        
        # Add keyword arguments (sorted for consistency)
        for key in sorted(kwargs.keys()):
            key_parts.append(f"{key}:{kwargs[key]}")
        
        # Join and hash for consistent key length
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        if not self.cache_enabled:
            return default
        
        # Try Redis first
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value is not None:
                    self.cache_stats['hits'] += 1
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
        
        # Fallback to memory cache
        with self.lock:
            if key in self.memory_cache:
                item = self.memory_cache[key]
                if time.time() < item['expiry']:
                    self.cache_stats['hits'] += 1
                    # Move to end (LRU)
                    self.memory_cache.move_to_end(key)
                    return item['value']
                else:
                    # Expired, remove
                    del self.memory_cache[key]
        
        self.cache_stats['misses'] += 1
        return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.cache_enabled:
            return False
        
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        
        # Try Redis first
        if self.redis_client:
            try:
                serialized_value = json.dumps(value)
                self.redis_client.setex(key, ttl, serialized_value)
                self.cache_stats['sets'] += 1
                return True
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
        
        # Fallback to memory cache
        with self.lock:
            # Check memory limit
            if self._get_memory_usage() > self.max_memory_size:
                self._evict_oldest()
            
            # Add to memory cache
            self.memory_cache[key] = {
                'value': value,
                'expiry': expiry,
                'size': self._estimate_size(value)
            }
            
            # Move to end (LRU)
            self.memory_cache.move_to_end(key)
            
            self.cache_stats['sets'] += 1
            return True
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.cache_enabled:
            return False
        
        success = False
        
        # Try Redis first
        if self.redis_client:
            try:
                result = self.redis_client.delete(key)
                if result > 0:
                    success = True
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
        
        # Remove from memory cache
        with self.lock:
            if key in self.memory_cache:
                del self.memory_cache[key]
                success = True
        
        if success:
            self.cache_stats['deletes'] += 1
        
        return success
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.cache_enabled:
            return False
        
        # Check Redis first
        if self.redis_client:
            try:
                return bool(self.redis_client.exists(key))
            except Exception as e:
                logger.warning(f"Redis exists check failed: {e}")
        
        # Check memory cache
        with self.lock:
            if key in self.memory_cache:
                item = self.memory_cache[key]
                if time.time() < item['expiry']:
                    return True
                else:
                    # Expired, remove
                    del self.memory_cache[key]
        
        return False
    
    def clear(self, pattern: str = None) -> int:
        """
        Clear cache entries.
        
        Args:
            pattern: Optional pattern to match keys (Redis only)
            
        Returns:
            Number of keys cleared
        """
        if not self.cache_enabled:
            return 0
        
        cleared_count = 0
        
        # Clear Redis cache
        if self.redis_client:
            try:
                if pattern:
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        cleared_count += self.redis_client.delete(*keys)
                else:
                    self.redis_client.flushdb()
                    cleared_count = -1  # Indicates all cleared
            except Exception as e:
                logger.warning(f"Redis clear failed: {e}")
        
        # Clear memory cache
        with self.lock:
            if pattern:
                # Pattern matching for memory cache (simple contains)
                keys_to_remove = [key for key in self.memory_cache.keys() if pattern in key]
                for key in keys_to_remove:
                    del self.memory_cache[key]
                    cleared_count += 1
            else:
                cleared_count += len(self.memory_cache)
                self.memory_cache.clear()
        
        return cleared_count
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage of cache."""
        total_size = 0
        for item in self.memory_cache.values():
            total_size += item['size']
        return total_size
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of a value."""
        try:
            return len(json.dumps(value).encode())
        except:
            return 100  # Default estimate
    
    def _evict_oldest(self):
        """Evict oldest cache entries when memory limit is reached."""
        while self._get_memory_usage() > self.max_memory_size * 0.8:  # Evict until 80% of limit
            if self.memory_cache:
                # Remove oldest entry
                oldest_key = next(iter(self.memory_cache))
                del self.memory_cache[oldest_key]
                logger.debug(f"Evicted cache entry: {oldest_key}")
            else:
                break
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self.cache_stats.copy()
        
        # Add current cache info
        stats['memory_cache_size'] = len(self.memory_cache)
        stats['memory_usage_mb'] = self._get_memory_usage() / (1024 * 1024)
        stats['redis_available'] = self.redis_client is not None
        stats['cache_enabled'] = self.cache_enabled
        
        # Calculate hit rate
        total_requests = stats['hits'] + stats['misses']
        if total_requests > 0:
            stats['hit_rate'] = stats['hits'] / total_requests
        else:
            stats['hit_rate'] = 0.0
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Check cache health status."""
        health = {
            'status': 'healthy',
            'cache_enabled': self.cache_enabled,
            'redis_status': 'unavailable',
            'memory_cache_status': 'healthy'
        }
        
        # Check Redis
        if self.redis_client:
            try:
                self.redis_client.ping()
                health['redis_status'] = 'healthy'
            except Exception as e:
                health['redis_status'] = f'unhealthy: {e}'
                health['status'] = 'degraded'
        
        # Check memory cache
        try:
            memory_usage = self._get_memory_usage()
            if memory_usage > self.max_memory_size:
                health['memory_cache_status'] = 'overloaded'
                health['status'] = 'degraded'
        except Exception as e:
            health['memory_cache_status'] = f'unhealthy: {e}'
            health['status'] = 'unhealthy'
        
        return health

# Global cache instance
cache_manager = CacheManager()

# Decorator for caching function results
def cached(ttl: Optional[int] = None, key_prefix: str = None):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            prefix = key_prefix or f"{func.__module__}.{func.__name__}"
            cache_key = cache_manager._generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

# Convenience functions
def get_cached(key: str, default: Any = None) -> Any:
    """Get value from cache."""
    return cache_manager.get(key, default)

def set_cached(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set value in cache."""
    return cache_manager.set(key, value, ttl)

def delete_cached(key: str) -> bool:
    """Delete value from cache."""
    return cache_manager.delete(key)

def clear_cache(pattern: str = None) -> int:
    """Clear cache entries."""
    return cache_manager.clear(pattern)
