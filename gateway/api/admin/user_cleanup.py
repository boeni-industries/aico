"""
User Data Cleanup Utilities

Helper functions for cleaning up user data across all storage systems
when deleting users.
"""

from aico.core.logging import get_logger

logger = get_logger("gateway.api.admin.user_cleanup")


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

    return results
