"""
User Data Cleanup Utilities

Helper functions for cleaning up user data across all storage systems
when deleting users (LMDB, PostgreSQL).
"""

import logging
from typing import Optional
from pathlib import Path
import shutil

from aico.core.logging import get_logger

logger = get_logger("backend.api.admin.user_cleanup")


async def cleanup_user_data(user_uuid: str) -> dict:
    """
    Clean up all user data from storage systems.
    
    Args:
        user_uuid: User UUID to clean up
        
    Returns:
        dict with cleanup results: {lmdb_deleted, errors}
    """
    results = {
        "lmdb_deleted": False,
        "errors": []
    }
    
    # Clean up LMDB conversation data
    try:
        lmdb_path = Path(f"data/lmdb/conversations/{user_uuid}")
        if lmdb_path.exists():
            shutil.rmtree(lmdb_path)
            results["lmdb_deleted"] = True
            logger.info(f"Deleted LMDB data for user {user_uuid}")
    except Exception as e:
        error_msg = f"Failed to delete LMDB data: {str(e)}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
    
    return results
