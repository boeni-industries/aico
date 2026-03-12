"""
Resource Monitoring for Task Scheduling

Provides real-time system resource monitoring including CPU, memory, disk,
network, battery, and user presence detection.

Phase 6.2: Resource Monitoring
"""

import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from dataclasses import dataclass

from aico.core.logging import get_logger


logger = get_logger("core.scheduler.resource_monitor")


@dataclass
class ResourceSnapshot:
    """Snapshot of system resources at a point in time"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_mbps: float
    battery_percent: Optional[float]
    on_ac_power: bool
    user_idle_seconds: Optional[int]
    
    def is_idle(self, cpu_threshold: float = 20.0, idle_time_threshold: int = 300) -> bool:
        """Check if system is idle
        
        Args:
            cpu_threshold: CPU usage threshold for idle (%)
            idle_time_threshold: User idle time threshold (seconds)
            
        Returns:
            True if system is considered idle
        """
        cpu_idle = self.cpu_percent < cpu_threshold
        user_idle = (self.user_idle_seconds or 0) > idle_time_threshold
        return cpu_idle and user_idle


class ResourceMonitor:
    """Monitors system resources for task scheduling decisions"""
    
    def __init__(self):
        """Initialize resource monitor"""
        self.last_snapshot: Optional[ResourceSnapshot] = None
        self.last_network_io = None
        self.last_network_time = None
        
        # Try to import psutil
        try:
            import psutil
            self.psutil = psutil
            self.psutil_available = True
            logger.info("Resource monitor initialized with psutil")
        except ImportError:
            self.psutil = None
            self.psutil_available = False
            logger.warning("psutil not available - resource monitoring limited")
    
    def get_snapshot(self) -> ResourceSnapshot:
        """Get current resource snapshot
        
        Returns:
            ResourceSnapshot with current system state
        """
        if not self.psutil_available:
            # Return default snapshot if psutil not available
            return ResourceSnapshot(
                timestamp=datetime.now(timezone.utc),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                network_mbps=0.0,
                battery_percent=None,
                on_ac_power=True,
                user_idle_seconds=None
            )
        
        # Get CPU usage
        cpu_percent = self.psutil.cpu_percent(interval=0.1)
        
        # Get memory usage
        memory = self.psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Get disk usage (root partition)
        try:
            disk = self.psutil.disk_usage('/')
            disk_percent = disk.percent
        except Exception as e:
            logger.warning(f"Failed to get disk usage: {e}")
            disk_percent = 0.0
        
        # Get network usage (Mbps)
        network_mbps = self._get_network_mbps()
        
        # Get battery status
        battery_percent, on_ac_power = self._get_battery_status()
        
        # Get user idle time
        user_idle_seconds = self._get_user_idle_time()
        
        snapshot = ResourceSnapshot(
            timestamp=datetime.now(timezone.utc),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            network_mbps=network_mbps,
            battery_percent=battery_percent,
            on_ac_power=on_ac_power,
            user_idle_seconds=user_idle_seconds
        )
        
        self.last_snapshot = snapshot
        return snapshot
    
    def _get_network_mbps(self) -> float:
        """Calculate current network usage in Mbps"""
        try:
            net_io = self.psutil.net_io_counters()
            current_time = time.time()
            
            if self.last_network_io and self.last_network_time:
                # Calculate bytes transferred since last check
                bytes_sent = net_io.bytes_sent - self.last_network_io.bytes_sent
                bytes_recv = net_io.bytes_recv - self.last_network_io.bytes_recv
                total_bytes = bytes_sent + bytes_recv
                
                # Calculate time elapsed
                time_elapsed = current_time - self.last_network_time
                
                if time_elapsed > 0:
                    # Convert to Mbps
                    mbps = (total_bytes * 8) / (time_elapsed * 1_000_000)
                else:
                    mbps = 0.0
            else:
                mbps = 0.0
            
            # Update last values
            self.last_network_io = net_io
            self.last_network_time = current_time
            
            return mbps
            
        except Exception as e:
            logger.warning(f"Failed to get network usage: {e}")
            return 0.0
    
    def _get_battery_status(self) -> tuple[Optional[float], bool]:
        """Get battery percentage and AC power status
        
        Returns:
            Tuple of (battery_percent, on_ac_power)
        """
        try:
            battery = self.psutil.sensors_battery()
            if battery:
                return (battery.percent, battery.power_plugged)
            else:
                # No battery (desktop)
                return (None, True)
        except Exception as e:
            logger.warning(f"Failed to get battery status: {e}")
            return (None, True)
    
    def _get_user_idle_time(self) -> Optional[int]:
        """Get user idle time in seconds
        
        Returns:
            Seconds since last user activity, or None if unavailable
        """
        try:
            # macOS: Use ioreg to get idle time
            if os.uname().sysname == 'Darwin':
                import subprocess
                result = subprocess.run(
                    ['ioreg', '-c', 'IOHIDSystem'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                
                for line in result.stdout.split('\n'):
                    if 'HIDIdleTime' in line:
                        # Extract nanoseconds and convert to seconds
                        idle_ns = int(line.split('=')[1].strip())
                        idle_seconds = idle_ns // 1_000_000_000
                        return idle_seconds
            
            # Linux: Check /proc/uptime and last user activity
            elif os.uname().sysname == 'Linux':
                # This is a simplified approach
                # For production, use X11 idle time or similar
                return None
            
            # Windows: Use GetLastInputInfo
            elif os.name == 'nt':
                import ctypes
                class LASTINPUTINFO(ctypes.Structure):
                    _fields_ = [
                        ('cbSize', ctypes.c_uint),
                        ('dwTime', ctypes.c_uint),
                    ]
                
                lastInputInfo = LASTINPUTINFO()
                lastInputInfo.cbSize = ctypes.sizeof(lastInputInfo)
                ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo))
                
                millis = ctypes.windll.kernel32.GetTickCount() - lastInputInfo.dwTime
                return millis // 1000
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to get user idle time: {e}")
            return None
    
    def check_storage_quota(self, path: str, min_free_gb: float = 1.0) -> bool:
        """Check if storage quota is satisfied
        
        Args:
            path: Path to check
            min_free_gb: Minimum free space required (GB)
            
        Returns:
            True if quota is satisfied
        """
        if not self.psutil_available:
            return True  # Assume OK if can't check
        
        try:
            disk = self.psutil.disk_usage(path)
            free_gb = disk.free / (1024 ** 3)
            
            if free_gb < min_free_gb:
                logger.warning(
                    f"Storage quota check failed: {free_gb:.2f}GB free < {min_free_gb}GB required"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to check storage quota: {e}")
            return True  # Assume OK on error
    
    def should_defer_task(self, 
                          cpu_threshold: float = 80.0,
                          memory_threshold: float = 80.0,
                          battery_threshold: float = 20.0,
                          require_ac_power: bool = False) -> tuple[bool, Optional[str]]:
        """Check if task should be deferred due to resource constraints
        
        Args:
            cpu_threshold: Maximum CPU usage (%)
            memory_threshold: Maximum memory usage (%)
            battery_threshold: Minimum battery level (%)
            require_ac_power: Whether AC power is required
            
        Returns:
            Tuple of (should_defer, reason)
        """
        snapshot = self.get_snapshot()
        
        # Check CPU
        if snapshot.cpu_percent > cpu_threshold:
            return (True, f"CPU usage {snapshot.cpu_percent:.1f}% > {cpu_threshold}%")
        
        # Check memory
        if snapshot.memory_percent > memory_threshold:
            return (True, f"Memory usage {snapshot.memory_percent:.1f}% > {memory_threshold}%")
        
        # Check battery
        if snapshot.battery_percent is not None:
            if snapshot.battery_percent < battery_threshold and not snapshot.on_ac_power:
                return (True, f"Battery {snapshot.battery_percent:.1f}% < {battery_threshold}%")
        
        # Check AC power requirement
        if require_ac_power and not snapshot.on_ac_power:
            return (True, "AC power required but on battery")
        
        return (False, None)
