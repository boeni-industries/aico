"""
Database Version Detection Service

Automatically detects versions of database systems with intelligent caching.
Versions are cached for 24 hours to avoid repeated queries while allowing updates.
"""

import asyncio
import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from aico.core.logging import get_logger
from aico.core.paths import AICOPaths

logger = get_logger("backend.services.version_detector")


@dataclass
class DatabaseVersion:
    """Database version information"""
    name: str
    version: str
    detected_at: str
    detection_method: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatabaseVersion":
        return cls(**data)


class VersionCache:
    """Manages version cache with TTL"""
    
    def __init__(self, cache_ttl_hours: int = 24):
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.cache_file = AICOPaths.get_data_directory() / "cache" / "database_versions.json"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    def get(self, db_name: str) -> Optional[DatabaseVersion]:
        """Get cached version if still valid"""
        try:
            if not self.cache_file.exists():
                return None
            
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            if db_name not in cache_data:
                return None
            
            db_data = cache_data[db_name]
            detected_at = datetime.fromisoformat(db_data['detected_at'])
            
            # Check if cache is still valid
            if datetime.utcnow() - detected_at > self.cache_ttl:
                logger.debug(f"Cache expired for {db_name}")
                return None
            
            logger.debug(f"Using cached version for {db_name}: {db_data['version']}")
            return DatabaseVersion.from_dict(db_data)
            
        except Exception as e:
            logger.warning(f"Failed to read cache for {db_name}: {e}")
            return None
    
    def set(self, db_version: DatabaseVersion) -> None:
        """Save version to cache"""
        try:
            # Load existing cache
            cache_data = {}
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
            
            # Update cache
            cache_data[db_version.name] = db_version.to_dict()
            
            # Write back
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.info(f"Cached version for {db_version.name}: {db_version.version}")
            
        except Exception as e:
            logger.error(f"Failed to write cache for {db_version.name}: {e}")
    
    def invalidate(self, db_name: Optional[str] = None) -> None:
        """Invalidate cache for specific database or all"""
        try:
            if db_name is None:
                # Clear entire cache
                if self.cache_file.exists():
                    self.cache_file.unlink()
                logger.info("Cleared entire version cache")
            else:
                # Remove specific entry
                if self.cache_file.exists():
                    with open(self.cache_file, 'r') as f:
                        cache_data = json.load(f)
                    
                    if db_name in cache_data:
                        del cache_data[db_name]
                        with open(self.cache_file, 'w') as f:
                            json.dump(cache_data, f, indent=2)
                        logger.info(f"Invalidated cache for {db_name}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")


class DatabaseVersionDetector:
    """Detects database versions with intelligent caching"""
    
    # Default versions as fallback
    DEFAULT_VERSIONS = {
        "PostgreSQL": "18.1",
        "vLLM": "unknown",
    }
    
    def __init__(self, cache_ttl_hours: int = 24):
        self.cache = VersionCache(cache_ttl_hours)
    
    async def get_version(self, db_name: str) -> str:
        """Get database version with caching"""
        # Check cache first
        cached = self.cache.get(db_name)
        if cached:
            return cached.version
        
        # Detect version
        version = await self._detect_version(db_name)
        
        # Cache the result
        if version:
            db_version = DatabaseVersion(
                name=db_name,
                version=version,
                detected_at=datetime.utcnow().isoformat(),
                detection_method=self._get_detection_method(db_name)
            )
            self.cache.set(db_version)
        
        return version
    
    def _get_detection_method(self, db_name: str) -> str:
        """Get detection method description"""
        methods = {
            "PostgreSQL": "docker exec + SELECT version()",
            "vLLM": "HTTP API /health or /v1/models",
        }
        return methods.get(db_name, "unknown")
    
    async def _detect_version(self, db_name: str) -> str:
        """Detect version for specific database"""
        logger.info(f"Attempting to detect version for {db_name}...")
        
        try:
            if db_name == "PostgreSQL":
                version = await self._detect_postgresql_version()
            elif db_name == "vLLM":
                version = await self._detect_vllm_version()
            else:
                logger.error(f"Unknown database: {db_name}")
                return self.DEFAULT_VERSIONS.get(db_name, "unknown")
            
            logger.info(f"Successfully detected {db_name} version: {version}")
            return version
            
        except Exception as e:
            logger.error(f"CRITICAL: Failed to detect version for {db_name}: {e}", exc_info=True)
            fallback = self.DEFAULT_VERSIONS.get(db_name, "unknown")
            logger.error(f"Using fallback version for {db_name}: {fallback}")
            return fallback
    
    async def _detect_postgresql_version(self) -> str:
        """Detect PostgreSQL version using the shared connection pool.

        This reuses the central Postgres configuration and credential resolution
        (env var + AICOKeyManager) implemented in aico.data.postgres.connection,
        instead of requiring AICO_PG_PASSWORD directly or shelling out to docker.
        """
        logger.debug("Attempting PostgreSQL version detection via asyncpg pool...")

        try:
            # Import lazily to avoid circular imports at module import time
            from aico.data.postgres.connection import get_postgres_pool

            pool = await get_postgres_pool()

            async with pool.acquire() as conn:
                # asyncpg returns a Record; SELECT version() has a single column
                row = await conn.fetchrow("SELECT version()")

            if not row:
                raise RuntimeError("SELECT version() returned no rows")

            output = row[0]
            if not isinstance(output, str):
                output = str(output)

            # Parse version from output like "PostgreSQL 18.1 on ..."
            output = output.strip()
            if "PostgreSQL" in output:
                version_part = output.split("PostgreSQL")[1].strip().split()[0]
                logger.info(f"PostgreSQL version detected successfully: {version_part}")
                return version_part

            logger.error(f"PostgreSQL version query returned unexpected format: {output}")

        except Exception as e:
            # Log full stack trace but fall back gracefully
            logger.error(f"PostgreSQL version detection failed: {e}", exc_info=True)

        # If we get here, detection failed
        fallback = self.DEFAULT_VERSIONS["PostgreSQL"]
        logger.error(f"PostgreSQL version detection FAILED - using fallback: {fallback}")
        return fallback
    
    async def _detect_vllm_version(self) -> str:
        """Detect vLLM version/reachability via OpenAI-compatible HTTP API.

        Note: vLLM's OpenAI-compatible server does not reliably expose a semantic
        server version string. We therefore treat this as a reachability check
        and return "unknown" (but cache it) when the endpoint is reachable.
        """
        logger.debug("Attempting vLLM reachability check via HTTP API...")

        # Import lazily to avoid hard dependency at module import time
        try:
            from aico.core.config import ConfigurationManager
            config = ConfigurationManager()
            vllm_cfg = config.get("llm.vllm", {})
        except Exception as e:
            logger.debug(f"Could not read vLLM config for version detection: {e}")
            vllm_cfg = {}

        host = vllm_cfg.get("host", "localhost")
        port = int(vllm_cfg.get("port", 8774))
        base_url = f"http://{host}:{port}"

        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as client:
                # Prefer /health if available
                resp = await client.get(f"{base_url}/health")
                if resp.status_code == 200:
                    return self.DEFAULT_VERSIONS["vLLM"]

                # Fallback to OpenAI models list
                resp = await client.get(f"{base_url}/v1/models")
                if resp.status_code == 200:
                    return self.DEFAULT_VERSIONS["vLLM"]

                logger.debug(f"vLLM API returned status {resp.status_code}")
        except Exception as e:
            # vLLM is optional at runtime (e.g., during dev); don't treat as error
            logger.debug(f"vLLM reachability check failed: {e}")

        return "unavailable"
    
    async def get_all_versions(self) -> Dict[str, str]:
        """Get all database versions"""
        versions = {}
        for db_name in self.DEFAULT_VERSIONS.keys():
            versions[db_name] = await self.get_version(db_name)
        return versions
    
    def invalidate_cache(self, db_name: Optional[str] = None) -> None:
        """Invalidate version cache"""
        self.cache.invalidate(db_name)


# Singleton instance
_detector_instance: Optional[DatabaseVersionDetector] = None


def get_version_detector() -> DatabaseVersionDetector:
    """Get singleton version detector instance"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = DatabaseVersionDetector(cache_ttl_hours=24)
    return _detector_instance
