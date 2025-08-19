"""
Timezone utilities for AICO CLI commands.

Provides consistent timezone handling across all CLI commands that display timestamps.
"""

from datetime import datetime
from typing import Optional


def format_timestamp_local(utc_timestamp: str, show_utc: bool = False) -> str:
    """
    Convert UTC timestamp to local timezone for display.
    
    Args:
        utc_timestamp: UTC timestamp string (ISO format with Z or +00:00)
        show_utc: If True, display as UTC with "UTC" suffix
        
    Returns:
        Formatted timestamp string in local timezone or UTC
        
    Examples:
        >>> format_timestamp_local("2025-08-13T13:29:52Z")
        "2025-08-13 15:29:52"  # In CEST (UTC+2)
        
        >>> format_timestamp_local("2025-08-13T13:29:52Z", show_utc=True)
        "2025-08-13 13:29:52 UTC"
    """
    try:
        # Parse UTC timestamp (handle both Z and +00:00 formats)
        if utc_timestamp.endswith('Z'):
            dt_utc = datetime.fromisoformat(utc_timestamp[:-1] + '+00:00')
        else:
            dt_utc = datetime.fromisoformat(utc_timestamp)
        
        if show_utc:
            return dt_utc.strftime('%Y-%m-%d %H:%M:%S UTC')
        else:
            # Convert to local timezone
            local_dt = dt_utc.astimezone()
            return local_dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        # Fallback to original format if parsing fails
        return utc_timestamp[:19]


def get_timezone_suffix(show_utc: bool = False) -> str:
    """
    Get appropriate timezone suffix for column headers.
    
    Args:
        show_utc: If True, return UTC suffix
        
    Returns:
        Empty string for local time, " (UTC)" for UTC time
    """
    return " (UTC)" if show_utc else ""
