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
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
import sys
from pathlib import Path

import jwt
from starlette.routing import Match

from fastapi import Request, Response
from fastapi.responses import JSONResponse
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
        self.logger = get_logger("backend.api_gateway.rate_limiter")
        
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
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """FastAPI middleware dispatch method"""
        try:
            # Get client IP as identifier
            client_ip = request.client.host if request.client else "unknown"
            
            # Check rate limit
            await self.check_rate_limit(client_ip)
            
            # Call the next middleware/endpoint
            response = await call_next(request)
            
            return response
            
        except RateLimitExceeded as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=429, detail=str(e))
        except Exception as e:
            self.logger.error(f"Rate limiter middleware error: {e}", extra={
                "subsystem": "api_gateway",
                "function": "dispatch",
                "topic": "rate_limiter.middleware_error",
                "error": str(e)
            })
            # Continue processing on unexpected errors
            return await call_next(request)
    
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
                pass  # Expected during shutdown - task cancellation is intentional
        
        self.buckets.clear()
        self.logger.info("Rate limiter shutdown")


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass  # Standard exception class definition - not silencing failures


class ValkeyRateLimitExceeded(Exception):
    """Raised when Valkey-backed rate limit is exceeded"""


class ValkeyFixedWindowRateLimiterMiddleware:
    def __init__(self, config_manager, app, *, logger_name: str = "backend.api_gateway.rate_limiter.valkey"):
        self._config = config_manager
        self._fastapi_app = app
        self._logger = get_logger(logger_name)

        self._last_config_reload_ts = 0.0
        self._config_reload_interval_seconds = 1.0

        self._redis = None
        self._lua = None

    def _get_route_template(self, request: Request) -> str:
        scope = request.scope
        router = getattr(self._fastapi_app, "router", None)
        if router is None:
            return scope.get("path", "")

        for route in getattr(router, "routes", []) or []:
            try:
                match, _child_scope = route.matches(scope)
            except Exception:
                continue

            if match != Match.FULL:
                continue

            methods = getattr(route, "methods", None)
            if methods and scope.get("method") not in methods:
                continue

            path_format = getattr(route, "path_format", None)
            if path_format:
                return path_format

        return scope.get("path", "")

    def _extract_identity(self, request: Request) -> tuple[str, str, str, str]:
        tenant_id = "unknown_tenant"
        user_id = "unknown_user"
        tenant_display_name = tenant_id
        user_full_name = user_id

        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth:
            return tenant_id, user_id, tenant_display_name, user_full_name

        parts = auth.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return tenant_id, user_id, tenant_display_name, user_full_name

        token = parts[1].strip()
        if not token:
            return tenant_id, user_id, tenant_display_name, user_full_name

        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_aud": False},
            )
            if isinstance(payload, dict):
                tenant_id = payload.get("tenant_id") or tenant_id
                user_id = payload.get("user_id") or payload.get("user_uuid") or payload.get("sub") or user_id

                tenant_display_name = (
                    payload.get("tenant_display_name")
                    or payload.get("tenant_name")
                    or payload.get("tenant")
                    or payload.get("tenant_label")
                    or tenant_id
                )
                user_full_name = (
                    payload.get("user_full_name")
                    or payload.get("full_name")
                    or payload.get("name")
                    or payload.get("username")
                    or user_id
                )
        except Exception:
            return tenant_id, user_id, tenant_display_name, user_full_name

        return tenant_id, user_id, tenant_display_name, user_full_name

    def _get_settings(self) -> dict[str, Any]:
        # The gateway process keeps an in-memory config cache. If runtime overrides
        # are written to disk (runtime.yaml), we need to reload periodically to pick
        # up changes without restarting the container.
        try:
            now = time.time()
            if (
                hasattr(self._config, "reload")
                and (now - self._last_config_reload_ts) >= self._config_reload_interval_seconds
            ):
                self._config.reload()
                self._last_config_reload_ts = now
        except Exception:
            # Fail open on reload issues
            pass

        settings = self._config.get("api_gateway.rate_limiting", {})
        if not isinstance(settings, dict):
            return {}
        return settings

    def _get_valkey_url(self, settings: dict[str, Any]) -> Optional[str]:
        url = settings.get("valkey_url") or settings.get("redis_url")
        if isinstance(url, str) and url.strip():
            return url.strip()
        return None

    async def _get_redis(self):
        if self._redis is not None:
            return self._redis

        from redis.asyncio import Redis

        settings = self._get_settings()
        url = self._get_valkey_url(settings)
        if not url:
            raise RuntimeError("Valkey URL not configured")

        self._redis = Redis.from_url(url, decode_responses=True)
        return self._redis

    async def _incr_with_ttl(self, *, key: str, ttl_seconds: int) -> int:
        r = await self._get_redis()

        if self._lua is None:
            self._lua = r.register_script(
                """
                local current = redis.call('INCR', KEYS[1])
                if current == 1 then
                  redis.call('EXPIRE', KEYS[1], ARGV[1])
                end
                return current
                """
            )

        result = await self._lua(keys=[key], args=[str(int(ttl_seconds))])
        try:
            return int(result)
        except Exception:
            return int(result or 0)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = self._get_settings()
        enabled = bool(settings.get("enabled", True))
        if not enabled:
            return await call_next(request)

        # Never rate limit CORS preflight requests. They must reach CORSMiddleware
        # so the browser can validate Access-Control-Allow-* headers.
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        if not self._get_valkey_url(settings):
            return await call_next(request)

        try:
            exclude_paths = settings.get("exclude_paths")
            if exclude_paths is None:
                exclude_paths = [
                    "/api/v1/health",
                    "/api/v1/health/",
                    "/api/v1/health/live",
                    "/api/v1/health/ready",
                    "/api/v1/handshake*",
                    "/api/v1/scheduler*",
                    "/api/v1/system/overview",
                    "/api/v1/kg/stats",
                    "/api/v1/memory*",
                    "/api/v1/emotion/history*",
                    "/api/v1/system/health*",
                    "/api/v1/system/remediate*",
                    "/api/v1/system/config*",
                ]

            if isinstance(exclude_paths, list):
                path = request.url.path
                for p in exclude_paths:
                    if not isinstance(p, str):
                        continue
                    if p.endswith("*"):
                        if path.startswith(p[:-1]):
                            return await call_next(request)
                    elif path == p:
                        return await call_next(request)

            window_seconds = int(settings.get("window_seconds", 60))
            if window_seconds <= 0:
                window_seconds = 60

            default_rpm = settings.get("default_requests_per_minute")
            if default_rpm is None:
                default_rpm = settings.get("requests_per_minute")
            if default_rpm is None:
                default_rpm = 100
            limit = int(default_rpm)

            # Guardrail: extremely low defaults (e.g. 1-5 RPM) can brick browser clients
            # and make the system look "unstable". Require an explicit opt-in if someone
            # really wants to test such limits.
            allow_very_low_limits = bool(settings.get("allow_very_low_limits", False))
            min_limit = int(settings.get("min_requests_per_minute", 30))
            if not allow_very_low_limits and limit < min_limit:
                self._logger.warning(
                    "rate_limiter.guardrail Raising low RPM limit",
                    extra={
                        "subsystem": "api_gateway",
                        "function": "dispatch",
                        "topic": "rate_limiter.guardrail",
                        "configured_limit": limit,
                        "effective_limit": min_limit,
                    },
                )
                limit = min_limit
            if limit <= 0:
                return await call_next(request)

            tenant_id, user_id, tenant_display_name, user_full_name = self._extract_identity(request)
            route_template = self._get_route_template(request)
            method = request.method

            key = f"rl:{tenant_id}:{user_id}:{method}:{route_template}"
            count = await self._incr_with_ttl(key=key, ttl_seconds=window_seconds)
            if count > limit:
                raise ValkeyRateLimitExceeded(f"Rate limit exceeded ({count}/{limit})")

            return await call_next(request)

        except ValkeyRateLimitExceeded as e:
            self._logger.warning(
                "rate_limiter.rate_limited Rate limit exceeded",
                extra={
                    "subsystem": "api_gateway",
                    "function": "dispatch",
                    "topic": "rate_limiter.rate_limited",
                    "tenant_id": locals().get("tenant_id"),
                    "tenant_display_name": locals().get("tenant_display_name") or locals().get("tenant_id"),
                    "user_id": locals().get("user_id"),
                    "user_full_name": locals().get("user_full_name") or locals().get("user_id"),
                    "method": locals().get("method"),
                    "route_template": locals().get("route_template"),
                    "limit": locals().get("limit"),
                    "count": locals().get("count"),
                },
            )
            return JSONResponse(status_code=429, content={"detail": str(e)})
        except Exception as e:
            self._logger.error(
                f"Valkey rate limiting middleware error: {e!r}",
                exc_info=True,
                extra={
                    "subsystem": "api_gateway",
                    "function": "dispatch",
                    "topic": "rate_limiter.valkey_error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return await call_next(request)
