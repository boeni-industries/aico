"""
Simple in-memory cache for agency endpoints.

Provides TTL-based caching to reduce database load for frequently accessed data.
"""

from datetime import datetime, UTC, timedelta
from typing import Dict, Any, Optional, Tuple, Callable
from functools import wraps
import asyncio

from aico.core.logging import get_logger

logger = get_logger("backend.api.agency.cache")


class AgencyCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str, ttl_seconds: int = 30) -> Optional[Any]:
        """Get cached value if not expired."""
        async with self._lock:
            if key in self._cache:
                value, cached_at = self._cache[key]
                age = (datetime.now(UTC) - cached_at).total_seconds()
                
                if age < ttl_seconds:
                    logger.info(f"[AGENCY_CACHE] Cache HIT for {key} (age: {age:.1f}s)")
                    return value
                else:
                    logger.info(f"[AGENCY_CACHE] Cache EXPIRED for {key} (age: {age:.1f}s)")
                    del self._cache[key]
            else:
                logger.info(f"[AGENCY_CACHE] Cache MISS for {key}")
            
            return None
    
    async def set(self, key: str, value: Any):
        """Store value in cache."""
        async with self._lock:
            self._cache[key] = (value, datetime.now(UTC))
            logger.debug(f"[AGENCY_CACHE] Cached {key}")
    
    async def clear(self, pattern: Optional[str] = None):
        """Clear cache entries matching pattern (or all if None)."""
        async with self._lock:
            if pattern is None:
                self._cache.clear()
                logger.info("[AGENCY_CACHE] Cleared all cache entries")
            else:
                keys_to_delete = [k for k in self._cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self._cache[key]
                logger.info(f"[AGENCY_CACHE] Cleared {len(keys_to_delete)} entries matching '{pattern}'")


# Global cache instance
_agency_cache = AgencyCache()


def cached(ttl_seconds: int = 30, key_func: Optional[Callable] = None):
    """
    Decorator to cache async function results.
    
    Args:
        ttl_seconds: Time to live in seconds
        key_func: Optional function to generate cache key from args
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: use function name and first arg (usually user dict)
                user_id = args[0].get("user_uuid") if args and isinstance(args[0], dict) else "unknown"
                cache_key = f"{func.__name__}:{user_id}"
            
            # Try to get from cache
            cached_value = await _agency_cache.get(cache_key, ttl_seconds)
            if cached_value is not None:
                return cached_value
            
            # Cache miss - execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await _agency_cache.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator


def get_agency_cache() -> AgencyCache:
    """Get the global agency cache instance."""
    return _agency_cache
