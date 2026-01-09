"""
Device Registration and Management Service for AICO Authentication

Provides device registration, fingerprinting, and lifecycle management
with User-Agent parsing for multiplatform support.
"""

import uuid
import re
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from ..data.libsql.connection import LibSQLConnection


@dataclass
class DeviceInfo:
    """Device information data class"""
    uuid: str
    device_name: str
    device_type: str
    platform: str
    last_seen: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DeviceService:
    """
    Device registration and management service.
    
    Handles device registration, User-Agent parsing, and device lifecycle
    management with multiplatform support.
    """
    
    def __init__(self, db_connection: LibSQLConnection):
        self.db = db_connection
    
    def register_or_update_device(
        self,
        device_uuid: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_name: Optional[str] = None,
        device_type: Optional[str] = None,
        platform: Optional[str] = None
    ) -> str:
        """
        Register a new device or update existing device.
        
        Args:
            device_uuid: Optional device UUID (generated if not provided)
            user_agent: User-Agent string for parsing device info
            device_name: Override device name
            device_type: Override device type
            platform: Override platform
            
        Returns:
            str: Device UUID
        """
        # Generate device UUID if not provided
        if not device_uuid:
            device_uuid = str(uuid.uuid4())
        
        # Parse User-Agent if provided
        parsed_info = self._parse_user_agent(user_agent) if user_agent else {}
        
        # Use provided values or fall back to parsed values
        final_device_name = device_name or parsed_info.get('device_name', device_uuid)
        final_device_type = device_type or parsed_info.get('device_type', 'web')
        final_platform = platform or parsed_info.get('platform', 'unknown')
        
        # Check if device exists
        existing = self.db.execute(
            "SELECT uuid FROM auth_devices WHERE uuid = ?",
            (device_uuid,)
        ).fetchone()
        
        now = datetime.utcnow().isoformat()
        
        if existing:
            # Update existing device
            self.db.execute("""
                UPDATE auth_devices 
                SET device_name = ?,
                    device_type = ?,
                    platform = ?,
                    last_seen = ?,
                    updated_at = ?,
                    is_active = TRUE
                WHERE uuid = ?
            """, (
                final_device_name,
                final_device_type,
                final_platform,
                now,
                now,
                device_uuid
            ))
        else:
            # Create new device
            self.db.execute("""
                INSERT INTO auth_devices (
                    uuid, device_name, device_type, platform,
                    last_seen, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, TRUE, ?, ?)
            """, (
                device_uuid,
                final_device_name,
                final_device_type,
                final_platform,
                now,
                now,
                now
            ))
        
        self.db.commit()
        return device_uuid
    
    def get_device(self, device_uuid: str) -> Optional[DeviceInfo]:
        """
        Get device information.
        
        Args:
            device_uuid: Device UUID
            
        Returns:
            DeviceInfo if found, None otherwise
        """
        result = self.db.execute("""
            SELECT uuid, device_name, device_type, platform,
                   last_seen, is_active, created_at, updated_at
            FROM auth_devices
            WHERE uuid = ?
        """, (device_uuid,)).fetchone()
        
        if not result:
            return None
        
        return DeviceInfo(
            uuid=result[0],
            device_name=result[1],
            device_type=result[2],
            platform=result[3],
            last_seen=datetime.fromisoformat(result[4]) if result[4] else None,
            is_active=bool(result[5]),
            created_at=datetime.fromisoformat(result[6]) if result[6] else None,
            updated_at=datetime.fromisoformat(result[7]) if result[7] else None
        )
    
    def update_last_seen(self, device_uuid: str) -> bool:
        """
        Update device last_seen timestamp.
        
        Args:
            device_uuid: Device UUID
            
        Returns:
            bool: True if updated, False if device not found
        """
        now = datetime.utcnow().isoformat()
        result = self.db.execute("""
            UPDATE auth_devices 
            SET last_seen = ?, updated_at = ?
            WHERE uuid = ?
        """, (now, now, device_uuid))
        self.db.commit()
        
        return result.rowcount > 0
    
    def deactivate_device(self, device_uuid: str) -> bool:
        """
        Deactivate a device.
        
        Args:
            device_uuid: Device UUID
            
        Returns:
            bool: True if deactivated, False if device not found
        """
        result = self.db.execute("""
            UPDATE auth_devices 
            SET is_active = FALSE, updated_at = ?
            WHERE uuid = ?
        """, (datetime.utcnow().isoformat(), device_uuid))
        self.db.commit()
        
        return result.rowcount > 0
    
    def _parse_user_agent(self, user_agent: str) -> Dict[str, str]:
        """
        Parse User-Agent string to extract device information.
        
        Supports multiple platforms:
        - Web browsers (Chrome, Firefox, Safari, Edge, etc.)
        - Mobile devices (iOS, Android)
        - Desktop platforms (Windows, macOS, Linux)
        
        Args:
            user_agent: User-Agent string
            
        Returns:
            Dict with device_name, device_type, and platform
        """
        if not user_agent:
            return {
                'device_name': 'Unknown Device',
                'device_type': 'web',
                'platform': 'unknown'
            }
        
        ua_lower = user_agent.lower()
        
        # Detect platform
        platform = self._detect_platform(ua_lower)
        
        # Detect device type
        device_type = self._detect_device_type(ua_lower)
        
        # Detect browser/client
        browser = self._detect_browser(ua_lower)
        
        # Build device name
        device_name = f"{browser} on {platform}"
        
        return {
            'device_name': device_name,
            'device_type': device_type,
            'platform': platform
        }
    
    def _detect_platform(self, ua_lower: str) -> str:
        """Detect operating system platform"""
        if 'iphone' in ua_lower or 'ipad' in ua_lower:
            return 'iOS'
        elif 'android' in ua_lower:
            return 'Android'
        elif 'mac os x' in ua_lower or 'macintosh' in ua_lower:
            return 'macOS'
        elif 'windows nt 10' in ua_lower:
            return 'Windows 10/11'
        elif 'windows nt 6.3' in ua_lower:
            return 'Windows 8.1'
        elif 'windows nt 6.2' in ua_lower:
            return 'Windows 8'
        elif 'windows nt 6.1' in ua_lower:
            return 'Windows 7'
        elif 'windows' in ua_lower:
            return 'Windows'
        elif 'linux' in ua_lower:
            if 'ubuntu' in ua_lower:
                return 'Ubuntu'
            elif 'fedora' in ua_lower:
                return 'Fedora'
            elif 'debian' in ua_lower:
                return 'Debian'
            else:
                return 'Linux'
        elif 'cros' in ua_lower:
            return 'Chrome OS'
        else:
            return 'Unknown'
    
    def _detect_device_type(self, ua_lower: str) -> str:
        """Detect device type (mobile, tablet, desktop)"""
        if 'mobile' in ua_lower or 'android' in ua_lower and 'mobile' in ua_lower:
            return 'mobile'
        elif 'tablet' in ua_lower or 'ipad' in ua_lower:
            return 'tablet'
        elif 'iphone' in ua_lower:
            return 'mobile'
        else:
            return 'desktop'
    
    def _detect_browser(self, ua_lower: str) -> str:
        """Detect browser or client application"""
        # Check for specific browsers in order of specificity
        if 'edg/' in ua_lower or 'edge/' in ua_lower:
            return 'Edge'
        elif 'opr/' in ua_lower or 'opera' in ua_lower:
            return 'Opera'
        elif 'chrome' in ua_lower and 'chromium' not in ua_lower:
            return 'Chrome'
        elif 'firefox' in ua_lower or 'fxios' in ua_lower:
            return 'Firefox'
        elif 'safari' in ua_lower and 'chrome' not in ua_lower:
            return 'Safari'
        elif 'msie' in ua_lower or 'trident' in ua_lower:
            return 'Internet Explorer'
        elif 'curl' in ua_lower:
            return 'cURL'
        elif 'postman' in ua_lower:
            return 'Postman'
        elif 'python' in ua_lower:
            return 'Python Client'
        else:
            return 'Web Browser'
