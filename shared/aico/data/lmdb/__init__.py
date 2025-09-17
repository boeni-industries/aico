"""
Core utilities for managing the LMDB database.

This module provides backend- and CLI-agnostic functions for path resolution
and initialization of the LMDB working memory database.
"""

import lmdb
from pathlib import Path
from typing import Optional

from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths

def get_lmdb_path(config: Optional[ConfigurationManager] = None) -> Path:
    """Resolve the LMDB database path using new hierarchical memory structure."""
    if config is None:
        config = ConfigurationManager()
        config.initialize(lightweight=True)
    
    # Use new hierarchical path structure: data/memory/working/
    # The working directory IS the LMDB database directory (no additional filename needed)
    working_memory_dir = AICOPaths.get_working_memory_path()
    
    return working_memory_dir

def initialize_lmdb_env(config: Optional[ConfigurationManager] = None) -> None:
    """Idempotently initialize the LMDB working memory database environment."""
    if config is None:
        config = ConfigurationManager()
        config.initialize(lightweight=True)

    db_path = get_lmdb_path(config)
    if db_path.exists():
        # Even if it exists, we should ensure the named DBs are there.
        pass

    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    memory_config = config.get("core.memory.working", {})
    map_size = memory_config.get("map_size_mb", 100) * 1024 * 1024
    named_dbs = memory_config.get("named_databases", [])

    try:
        # max_dbs must be set to allow for named databases
        env = lmdb.open(str(db_path), map_size=map_size, max_dbs=len(named_dbs) + 1)
        
        # Create each named database. This is done on the environment, not the transaction.
        for db_name in named_dbs:
            env.open_db(key=db_name.encode('utf-8'), create=True)
        
        env.close()
    except Exception as e:
        # Re-raise as a more specific error if needed, or handle
        raise IOError(f"Failed to initialize LMDB database at {db_path}: {e}") from e
