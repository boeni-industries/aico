"""PostgreSQL connection helper for CLI commands.

Provides a simple connection helper for CLI commands that need direct database access.
This is appropriate for admin/debug tools that need low-level database inspection.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
from pathlib import Path
import sys

# Add shared module to path
if getattr(sys, 'frozen', False):
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.security.key_manager import AICOKeyManager


def get_pg_connection():
    """Get PostgreSQL connection for CLI commands.
    
    Returns a psycopg2 connection with RealDictCursor for dict-like row access.
    """
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    
    pg_cfg = config.get("core.database.postgres", {})
    if not pg_cfg:
        raise ValueError("No PostgreSQL configuration found in core.yaml")
    
    host = pg_cfg.get("host", "127.0.0.1")
    port = int(pg_cfg.get("port", 5432))
    db_name = pg_cfg.get("db_name", "aico")
    user = pg_cfg.get("user", "postgres")
    
    # Get password from keyring
    key_manager = AICOKeyManager(config)
    password = key_manager.get_database_password("postgres", username=user)
    
    if not password:
        raise ValueError("PostgreSQL password not found in keyring. Run 'aico deploy pg'")
    
    # Create connection with dict cursor
    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=db_name,
        user=user,
        password=password,
        cursor_factory=RealDictCursor
    )
    
    return conn
