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
        "InfluxDB": "2.8.0",
        "ChromaDB": "0.5.x",
        "LMDB": "0.9.x",
        "Ollama": "0.5.x",
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
            "InfluxDB": "docker exec + influxd version",
            "ChromaDB": "python package version",
            "LMDB": "python package version",
            "Ollama": "HTTP API /api/version",
        }
        return methods.get(db_name, "unknown")
    
    async def _detect_version(self, db_name: str) -> str:
        """Detect version for specific database"""
        logger.info(f"Attempting to detect version for {db_name}...")
        
        try:
            if db_name == "PostgreSQL":
                version = await self._detect_postgresql_version()
            elif db_name == "InfluxDB":
                version = await self._detect_influxdb_version()
            elif db_name == "ChromaDB":
                version = await self._detect_chromadb_version()
            elif db_name == "LMDB":
                version = await self._detect_lmdb_version()
            elif db_name == "Ollama":
                version = await self._detect_ollama_version()
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
        """Detect PostgreSQL version from container"""
        logger.debug("Attempting PostgreSQL version detection via docker exec...")
        
        try:
            pg_password = os.environ.get("AICO_PG_PASSWORD")
            if not pg_password:
                logger.error(
                    "AICO_PG_PASSWORD is not set; cannot perform authenticated PostgreSQL "
                    "version detection inside aico-postgres container"
                )
                raise RuntimeError("AICO_PG_PASSWORD not set")

            # Try docker exec first
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    "docker",
                    "exec",
                    "-e",
                    f"PGPASSWORD={pg_password}",
                    "aico-postgres",
                    "psql",
                    "-U",
                    "postgres",
                    "-t",
                    "-c",
                    "SELECT version()",
                ],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse version from output like "PostgreSQL 18.1 on ..."
                output = result.stdout.strip()
                if "PostgreSQL" in output:
                    version_part = output.split("PostgreSQL")[1].strip().split()[0]
                    logger.info(f"PostgreSQL version detected successfully: {version_part}")
                    return version_part
                else:
                    logger.error(f"PostgreSQL version query returned unexpected format: {output}")
            else:
                logger.error(f"PostgreSQL version query failed with exit code {result.returncode}: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("PostgreSQL version detection timed out after 5 seconds")
        except Exception as e:
            logger.error(f"PostgreSQL version detection failed: {e}", exc_info=True)
        
        # If we get here, detection failed
        fallback = self.DEFAULT_VERSIONS["PostgreSQL"]
        logger.error(f"PostgreSQL version detection FAILED - using fallback: {fallback}")
        return fallback
    
    async def _detect_influxdb_version(self) -> str:
        """Detect InfluxDB version from container"""
        logger.debug("Attempting InfluxDB version detection via docker exec...")
        
        try:
            # Try docker exec
            result = await asyncio.to_thread(
                subprocess.run,
                ["docker", "exec", "aico-influxdb", "influxd", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse version from output like "InfluxDB v2.8.0 ..."
                output = result.stdout.strip()
                if "InfluxDB" in output:
                    version_part = output.split("InfluxDB")[1].strip().split()[0].lstrip('v')
                    logger.info(f"InfluxDB version detected successfully: {version_part}")
                    return version_part
                else:
                    logger.error(f"InfluxDB version query returned unexpected format: {output}")
            else:
                logger.error(f"InfluxDB version query failed with exit code {result.returncode}: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("InfluxDB version detection timed out after 5 seconds")
        except Exception as e:
            logger.error(f"InfluxDB version detection failed: {e}", exc_info=True)
        
        # If we get here, detection failed
        fallback = self.DEFAULT_VERSIONS["InfluxDB"]
        logger.error(f"InfluxDB version detection FAILED - using fallback: {fallback}")
        return fallback
    
    async def _detect_chromadb_version(self) -> str:
        """Detect ChromaDB version from Python package"""
        logger.debug("Attempting ChromaDB version detection from Python package...")
        
        try:
            import chromadb
            version = chromadb.__version__
            logger.info(f"ChromaDB version detected successfully: {version}")
            return version
        except ImportError:
            logger.error("ChromaDB package not installed - cannot detect version")
        except AttributeError:
            logger.error("ChromaDB package has no __version__ attribute")
        except Exception as e:
            logger.error(f"ChromaDB version detection failed: {e}", exc_info=True)
        
        # If we get here, detection failed
        fallback = self.DEFAULT_VERSIONS["ChromaDB"]
        logger.error(f"ChromaDB version detection FAILED - using fallback: {fallback}")
        return fallback
    
    async def _detect_lmdb_version(self) -> str:
        """Detect LMDB version from Python package"""
        logger.debug("Attempting LMDB version detection from Python package...")
        
        try:
            import lmdb
            version = lmdb.version()
            version_str = ".".join(map(str, version))
            logger.info(f"LMDB version detected successfully: {version_str}")
            return version_str
        except ImportError:
            logger.error("LMDB package not installed - cannot detect version")
        except AttributeError:
            logger.error("LMDB package has no version() function")
        except Exception as e:
            logger.error(f"LMDB version detection failed: {e}", exc_info=True)
        
        # If we get here, detection failed
        fallback = self.DEFAULT_VERSIONS["LMDB"]
        logger.error(f"LMDB version detection FAILED - using fallback: {fallback}")
        return fallback
    
    async def _detect_ollama_version(self) -> str:
        """Detect Ollama version from HTTP API"""
        logger.debug("Attempting Ollama version detection via HTTP API...")
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get("http://localhost:11434/api/version")
                if response.status_code == 200:
                    version_data = response.json()
                    version = version_data.get("version", self.DEFAULT_VERSIONS["Ollama"])
                    logger.info(f"Ollama version detected successfully: {version}")
                    return version
                else:
                    logger.error(f"Ollama API returned status {response.status_code}")
        except httpx.TimeoutException:
            logger.error("Ollama version detection timed out after 2 seconds")
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama - service may not be running")
        except Exception as e:
            logger.error(f"Ollama version detection failed: {e}", exc_info=True)
        
        # If we get here, detection failed
        fallback = self.DEFAULT_VERSIONS["Ollama"]
        logger.error(f"Ollama version detection FAILED - using fallback: {fallback}")
        return fallback
    
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
