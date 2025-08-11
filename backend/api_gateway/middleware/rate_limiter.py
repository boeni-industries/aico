"""
Rate Limiter Middleware for AICO API Gateway

Implements token bucket algorithm for request throttling with:
- Per-client rate limiting
- Configurable limits and windows
- Burst handling
- Memory-efficient implementation
"""

import asyncio
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
import sys
from pathlib import Path

# Shared modules now installed via UV editable install

from aico.core.logging import get_logger


@dataclass
class TokenBucket:
    """Token bucket for rate limiting"""
    capacity: int
    tokens: float
    refill_rate: float
    last_refill: float
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket"""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        """Refill tokens based on time elapsed"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on refill rate
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now


class RateLimiter:
    """
    Rate limiter using token bucket algorithm
    
    Provides:
    - Per-client rate limiting
    - Configurable limits and windows
    - Burst handling
    - Memory-efficient token bucket implementation
    - Automatic cleanup of inactive buckets
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("api_gateway", "rate_limiter")
        
        # Configuration - convert per-minute to per-second
        requests_per_minute = config.get("default_requests_per_minute", 100)
        self.requests_per_second = requests_per_minute / 60.0
        self.burst_size = config.get("burst_size", 20)
        self.cleanup_interval = config.get("cleanup_interval_minutes", 5) * 60  # Convert to seconds
        
        # Token buckets per client
        self.buckets: Dict[str, TokenBucket] = {}
        
        # Cleanup task
        # Cleanup task will be started lazily when first needed
        self.cleanup_task = None
        
        self.logger.info("Rate limiter initialized", extra={
            "requests_per_second": self.requests_per_second,
            "burst_size": self.burst_size
        })
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def check_rate_limit(self, client_id: str, tokens: int = 1) -> bool:
        """
        Check if request is within rate limit
        
        Args:
            client_id: Client identifier
            tokens: Number of tokens to consume (default 1)
            
        Returns:
            True if request allowed, False if rate limited
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        try:
            # Start cleanup task lazily if not already running
            if self.cleanup_task is None:
                self._start_cleanup_task()
            
            # Get or create bucket for client
            bucket = self._get_bucket(client_id)
            
            # Try to consume tokens
            if bucket.consume(tokens):
                return True
            else:
                self.logger.warning(f"Rate limit exceeded for client: {client_id}")
                raise RateLimitExceeded(f"Rate limit exceeded for client {client_id}")
                
        except RateLimitExceeded:
            raise
        except Exception as e:
            self.logger.error(f"Rate limit check error: {e}")
            # On error, allow request (fail open)
            return True
    
    def _get_bucket(self, client_id: str) -> TokenBucket:
        """Get or create token bucket for client"""
        if client_id not in self.buckets:
            self.buckets[client_id] = TokenBucket(
                capacity=self.burst_size,
                tokens=self.burst_size,  # Start with full bucket
                refill_rate=self.requests_per_second,
                last_refill=time.time()
            )
        
        return self.buckets[client_id]
    
    async def _cleanup_loop(self):
        """Background cleanup of inactive buckets"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_inactive_buckets()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")
    
    async def _cleanup_inactive_buckets(self):
        """Remove inactive token buckets to save memory"""
        now = time.time()
        inactive_threshold = now - (self.cleanup_interval * 2)
        
        inactive_clients = [
            client_id for client_id, bucket in self.buckets.items()
            if bucket.last_refill < inactive_threshold
        ]
        
        for client_id in inactive_clients:
            del self.buckets[client_id]
        
        if inactive_clients:
            self.logger.debug(f"Cleaned up {len(inactive_clients)} inactive rate limit buckets")
    
    def get_client_status(self, client_id: str) -> Dict[str, Any]:
        """Get rate limit status for client"""
        bucket = self.buckets.get(client_id)
        if not bucket:
            return {
                "client_id": client_id,
                "tokens_available": self.burst_size,
                "capacity": self.burst_size,
                "refill_rate": self.requests_per_second
            }
        
        bucket._refill()  # Update tokens before reporting
        
        return {
            "client_id": client_id,
            "tokens_available": int(bucket.tokens),
            "capacity": bucket.capacity,
            "refill_rate": bucket.refill_rate,
            "last_refill": bucket.last_refill
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        return {
            "active_clients": len(self.buckets),
            "requests_per_second": self.requests_per_second,
            "burst_size": self.burst_size,
            "cleanup_interval": self.cleanup_interval
        }
    
    async def shutdown(self):
        """Shutdown rate limiter"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.buckets.clear()
        self.logger.info("Rate limiter shutdown")


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass
