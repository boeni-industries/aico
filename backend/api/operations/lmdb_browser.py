"""
LMDB Browser Functions

Provides browsing and querying capabilities for LMDB key-value store.
"""

import json
from typing import Optional, List
from fastapi import HTTPException, status
from aico.core.logging import get_logger
from backend.api.operations.schemas import (
    LMDBBrowseRequest, LMDBBrowseResponse, LMDBKeyInfo, LMDBKeyValueResponse,
)

logger = get_logger("backend", "api.operations.lmdb_browser")


async def browse_lmdb_keys(browse_request: LMDBBrowseRequest) -> LMDBBrowseResponse:
    """
    Browse LMDB keys with filtering and pagination.
    
    Args:
        browse_request: Browse request with filters and pagination
        
    Returns:
        LMDBBrowseResponse with matching keys
    """
    try:
        # Get memory manager from AI registry
        from aico.ai import ai_registry
        memory_manager = ai_registry.get("memory")
        
        if not memory_manager or not hasattr(memory_manager, '_working_store'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory manager not available"
            )
        
        working_store = memory_manager._working_store
        
        # Get the requested database
        db = working_store.dbs.get(browse_request.database_name)
        if not db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database '{browse_request.database_name}' not found"
            )
        
        # Collect matching keys
        all_keys = []
        
        with working_store.env.begin(db=db, write=False) as txn:
            cursor = txn.cursor()
            
            for key_bytes, value_bytes in cursor:
                try:
                    key = key_bytes.decode('utf-8')
                    
                    # Apply key prefix filter
                    if browse_request.key_prefix and not key.startswith(browse_request.key_prefix):
                        continue
                    
                    # Parse value for additional filtering
                    value = json.loads(value_bytes.decode('utf-8'))
                    
                    # Apply user_id filter if specified
                    if browse_request.user_id:
                        value_user_id = value.get('user_id') or value.get('userId')
                        if value_user_id != browse_request.user_id:
                            continue
                    
                    # Create preview (truncate long values)
                    value_str = json.dumps(value, ensure_ascii=False)
                    preview = value_str[:100] + '...' if len(value_str) > 100 else value_str
                    
                    # Extract timestamp if available
                    timestamp = value.get('timestamp') or value.get('created_at')
                    
                    all_keys.append(LMDBKeyInfo(
                        key=key,
                        value_preview=preview,
                        size_bytes=len(value_bytes),
                        timestamp=timestamp
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to process key: {e}")
                    continue
        
        # Apply pagination
        total_count = len(all_keys)
        start_idx = browse_request.offset
        end_idx = start_idx + browse_request.limit
        paginated_keys = all_keys[start_idx:end_idx]
        has_more = end_idx < total_count
        
        logger.info(f"Browse LMDB: {browse_request.database_name}, found {total_count} keys, returning {len(paginated_keys)}")
        
        return LMDBBrowseResponse(
            database_name=browse_request.database_name,
            keys=paginated_keys,
            total_count=total_count,
            has_more=has_more
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to browse LMDB keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to browse LMDB: {str(e)}"
        )


async def get_lmdb_key_value(database_name: str, key: str) -> LMDBKeyValueResponse:
    """
    Get the full value for a specific LMDB key.
    
    Args:
        database_name: LMDB database name
        key: Key to retrieve
        
    Returns:
        LMDBKeyValueResponse with full value
    """
    try:
        # Get memory manager from AI registry
        from aico.ai import ai_registry
        memory_manager = ai_registry.get("memory")
        
        if not memory_manager or not hasattr(memory_manager, '_working_store'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory manager not available"
            )
        
        working_store = memory_manager._working_store
        
        # Get the requested database
        db = working_store.dbs.get(database_name)
        if not db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database '{database_name}' not found"
            )
        
        # Retrieve the key
        with working_store.env.begin(db=db, write=False) as txn:
            value_bytes = txn.get(key.encode('utf-8'))
            
            if value_bytes is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Key '{key}' not found in database '{database_name}'"
                )
            
            value = json.loads(value_bytes.decode('utf-8'))
            
            return LMDBKeyValueResponse(
                key=key,
                value=value,
                size_bytes=len(value_bytes),
                database_name=database_name
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get LMDB key value: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve key: {str(e)}"
        )


async def delete_lmdb_keys(database_name: str, keys: List[str]) -> dict:
    """
    Delete multiple keys from LMDB database.
    
    Args:
        database_name: LMDB database name
        keys: List of keys to delete
        
    Returns:
        Dict with deletion results
    """
    try:
        from aico.ai import ai_registry
        memory_manager = ai_registry.get("memory")
        
        if not memory_manager or not hasattr(memory_manager, '_working_store'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory manager not available"
            )
        
        working_store = memory_manager._working_store
        db = working_store.dbs.get(database_name)
        
        if not db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database '{database_name}' not found"
            )
        
        deleted_count = 0
        failed_keys = []
        
        with working_store.env.begin(db=db, write=True) as txn:
            for key in keys:
                try:
                    if txn.delete(key.encode('utf-8')):
                        deleted_count += 1
                    else:
                        failed_keys.append(key)
                except Exception as e:
                    logger.warning(f"Failed to delete key {key}: {e}")
                    failed_keys.append(key)
        
        logger.info(f"Deleted {deleted_count} keys from {database_name}")
        
        return {
            "deleted_count": deleted_count,
            "failed_count": len(failed_keys),
            "failed_keys": failed_keys
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete LMDB keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete keys: {str(e)}"
        )


async def find_orphaned_lmdb_entries(database_name: str, db_connection) -> dict:
    """
    Find LMDB entries that reference non-existent users.
    
    Args:
        database_name: LMDB database name
        
    Returns:
        Dict with orphaned entry information
    """
    try:
        from aico.ai import ai_registry
        memory_manager = ai_registry.get("memory")
        
        if not memory_manager or not hasattr(memory_manager, '_working_store'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory manager not available"
            )
        
        working_store = memory_manager._working_store
        db = working_store.dbs.get(database_name)
        
        if not db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database '{database_name}' not found"
            )
        
        # Get all valid user UUIDs from database using injected connection
        cursor = db_connection.execute("SELECT uuid FROM user_profiles")
        valid_user_ids = {row[0] for row in cursor.fetchall()}
        
        # Find entries with invalid user_ids
        orphaned_entries = []
        total_entries = 0
        
        with working_store.env.begin(db=db, write=False) as txn:
            cursor = txn.cursor()
            
            for key_bytes, value_bytes in cursor:
                try:
                    total_entries += 1
                    key = key_bytes.decode('utf-8')
                    value = json.loads(value_bytes.decode('utf-8'))
                    
                    user_id = value.get('user_id') or value.get('userId')
                    if user_id and user_id not in valid_user_ids:
                        orphaned_entries.append({
                            "key": key,
                            "user_id": user_id,
                            "preview": json.dumps(value)[:100]
                        })
                        
                except Exception as e:
                    logger.warning(f"Failed to process key for orphan check: {e}")
                    continue
        
        logger.info(f"Found {len(orphaned_entries)} orphaned entries out of {total_entries} total")
        
        return {
            "total_entries": total_entries,
            "orphaned_count": len(orphaned_entries),
            "orphaned_entries": orphaned_entries[:100],  # Limit to first 100
            "valid_user_count": len(valid_user_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to find orphaned entries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find orphaned entries: {str(e)}"
        )
