"""
Version management for AICO subsystems.

Reads version information from the VERSIONS file at the project root.
This is the single source of truth for all subsystem versions.
"""

from pathlib import Path
from typing import Dict, Optional


def _find_project_root() -> Path:
    """Find the AICO project root by looking for the VERSIONS file."""
    current = Path(__file__).parent
    
    # Walk up the directory tree looking for VERSIONS file
    while current != current.parent:
        versions_file = current / "VERSIONS"
        if versions_file.exists():
            return current
        current = current.parent
    
    # Fallback: assume we're in a standard AICO structure
    # shared/aico/core/version.py -> go up 3 levels to project root
    return Path(__file__).parent.parent.parent.parent


def _parse_versions_file() -> Dict[str, str]:
    """Parse the VERSIONS file and return a dictionary of subsystem versions."""
    project_root = _find_project_root()
    versions_file = project_root / "VERSIONS"
    
    if not versions_file.exists():
        raise FileNotFoundError(f"VERSIONS file not found at {versions_file}")
    
    versions = {}
    with open(versions_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and ':' in line:
                subsystem, version = line.split(':', 1)
                versions[subsystem.strip()] = version.strip()
    
    return versions


def get_version(subsystem: str) -> str:
    """
    Get the version for a specific subsystem.
    
    Args:
        subsystem: The subsystem name (e.g., 'backend', 'cli', 'shared', etc.)
        
    Returns:
        Version string for the subsystem
        
    Raises:
        ValueError: If subsystem is not found in VERSIONS file
    """
    versions = _parse_versions_file()
    
    if subsystem not in versions:
        available = ', '.join(versions.keys())
        raise ValueError(f"Subsystem '{subsystem}' not found in VERSIONS file. Available: {available}")
    
    return versions[subsystem]


def get_all_versions() -> Dict[str, str]:
    """
    Get all subsystem versions.
    
    Returns:
        Dictionary mapping subsystem names to version strings
    """
    return _parse_versions_file()


# Convenience functions for common subsystems
def get_backend_version() -> str:
    """Get the backend version."""
    return get_version('backend')


def get_cli_version() -> str:
    """Get the CLI version."""
    return get_version('cli')


def get_shared_version() -> str:
    """Get the shared modules version."""
    return get_version('shared')


def get_frontend_version() -> str:
    """Get the frontend version."""
    return get_version('frontend')


def get_studio_version() -> str:
    """Get the studio version."""
    return get_version('studio')


def get_modelservice_version() -> str:
    """Get the modelservice version."""
    return get_version('modelservice')
