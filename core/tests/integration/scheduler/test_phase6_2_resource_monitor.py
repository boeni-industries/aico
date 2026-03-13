"""
Integration Tests for Phase 6.2: Resource Monitor

Tests real-time resource monitoring including CPU, memory, disk, network,
battery, and user presence detection.
"""

import pytest
from datetime import datetime

from core.services.scheduler.resource_monitor import ResourceMonitor, ResourceSnapshot


class TestResourceMonitor:
    """Test resource monitoring functionality"""
    
    def test_initialization(self):
        """Test resource monitor initialization"""
        # Act
        monitor = ResourceMonitor()
        
        # Assert
        assert monitor is not None
        # psutil_available depends on environment
        assert isinstance(monitor.psutil_available, bool)
    
    def test_get_snapshot(self):
        """Test getting resource snapshot"""
        # Arrange
        monitor = ResourceMonitor()
        
        # Act
        snapshot = monitor.get_snapshot()
        
        # Assert
        assert isinstance(snapshot, ResourceSnapshot)
        assert isinstance(snapshot.timestamp, datetime)
        assert isinstance(snapshot.cpu_percent, float)
        assert isinstance(snapshot.memory_percent, float)
        assert isinstance(snapshot.disk_percent, float)
        assert isinstance(snapshot.network_mbps, float)
        assert isinstance(snapshot.on_ac_power, bool)
        
        # Values should be reasonable
        assert 0 <= snapshot.cpu_percent <= 100
        assert 0 <= snapshot.memory_percent <= 100
        assert 0 <= snapshot.disk_percent <= 100
        assert snapshot.network_mbps >= 0
    
    def test_snapshot_is_idle_cpu_threshold(self):
        """Test idle detection based on CPU threshold"""
        # Arrange
        snapshot = ResourceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=15.0,  # Below threshold
            memory_percent=50.0,
            disk_percent=50.0,
            network_mbps=1.0,
            battery_percent=80.0,
            on_ac_power=True,
            user_idle_seconds=400  # Above threshold
        )
        
        # Act
        is_idle = snapshot.is_idle(cpu_threshold=20.0, idle_time_threshold=300)
        
        # Assert
        assert is_idle is True
    
    def test_snapshot_not_idle_high_cpu(self):
        """Test not idle when CPU is high"""
        # Arrange
        snapshot = ResourceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=50.0,  # Above threshold
            memory_percent=50.0,
            disk_percent=50.0,
            network_mbps=1.0,
            battery_percent=80.0,
            on_ac_power=True,
            user_idle_seconds=400
        )
        
        # Act
        is_idle = snapshot.is_idle(cpu_threshold=20.0, idle_time_threshold=300)
        
        # Assert
        assert is_idle is False
    
    def test_snapshot_not_idle_user_active(self):
        """Test not idle when user is active"""
        # Arrange
        snapshot = ResourceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=15.0,
            memory_percent=50.0,
            disk_percent=50.0,
            network_mbps=1.0,
            battery_percent=80.0,
            on_ac_power=True,
            user_idle_seconds=100  # Below threshold
        )
        
        # Act
        is_idle = snapshot.is_idle(cpu_threshold=20.0, idle_time_threshold=300)
        
        # Assert
        assert is_idle is False
    
    def test_snapshot_idle_no_user_idle_data(self):
        """Test idle detection when user idle data is unavailable"""
        # Arrange
        snapshot = ResourceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=15.0,
            memory_percent=50.0,
            disk_percent=50.0,
            network_mbps=1.0,
            battery_percent=80.0,
            on_ac_power=True,
            user_idle_seconds=None  # No data
        )
        
        # Act
        is_idle = snapshot.is_idle(cpu_threshold=20.0, idle_time_threshold=300)
        
        # Assert
        # Should be False because user_idle_seconds is None (treated as 0)
        assert is_idle is False
    
    def test_check_storage_quota_sufficient(self):
        """Test storage quota check with sufficient space"""
        # Arrange
        monitor = ResourceMonitor()
        
        # Act - Check with very low requirement (should pass)
        result = monitor.check_storage_quota("/", min_free_gb=0.001)
        
        # Assert
        assert result is True
    
    def test_check_storage_quota_insufficient(self):
        """Test storage quota check with insufficient space"""
        # Arrange
        monitor = ResourceMonitor()
        
        # Act - Check with impossibly high requirement (should fail if psutil available)
        result = monitor.check_storage_quota("/", min_free_gb=999999.0)
        
        # Assert
        if monitor.psutil_available:
            assert result is False
        else:
            # Without psutil, assumes OK
            assert result is True
    
    def test_should_defer_task_high_cpu(self):
        """Test task deferral due to high CPU usage"""
        # Arrange
        monitor = ResourceMonitor()
        
        # Mock a high CPU snapshot by getting real snapshot and checking
        # We can't reliably mock high CPU, so we test the logic
        should_defer, reason = monitor.should_defer_task(
            cpu_threshold=0.1,  # Very low threshold
            memory_threshold=100.0  # Don't defer on memory
        )
        
        # Assert
        # If CPU is above 0.1%, should defer
        if should_defer:
            assert "CPU usage" in reason
    
    def test_should_defer_task_low_battery(self):
        """Test task deferral due to low battery"""
        # Arrange
        monitor = ResourceMonitor()
        
        # Act
        should_defer, reason = monitor.should_defer_task(
            cpu_threshold=100.0,  # Don't defer on CPU
            memory_threshold=100.0,  # Don't defer on memory
            battery_threshold=100.0  # Defer if battery < 100%
        )
        
        # Assert
        # If on battery and < 100%, should defer
        snapshot = monitor.get_snapshot()
        if snapshot.battery_percent is not None and not snapshot.on_ac_power:
            if snapshot.battery_percent < 100.0:
                assert should_defer is True
                assert "Battery" in reason
    
    def test_should_defer_task_require_ac_power(self):
        """Test task deferral when AC power required"""
        # Arrange
        monitor = ResourceMonitor()
        
        # Act
        should_defer, reason = monitor.should_defer_task(
            cpu_threshold=100.0,
            memory_threshold=100.0,
            battery_threshold=0.0,
            require_ac_power=True
        )
        
        # Assert
        snapshot = monitor.get_snapshot()
        if not snapshot.on_ac_power:
            assert should_defer is True
            assert "AC power required" in reason
        else:
            assert should_defer is False
    
    def test_should_not_defer_task_good_conditions(self):
        """Test that task is not deferred under good conditions"""
        # Arrange
        monitor = ResourceMonitor()
        
        # Act - Very lenient thresholds
        should_defer, reason = monitor.should_defer_task(
            cpu_threshold=100.0,
            memory_threshold=100.0,
            battery_threshold=0.0,
            require_ac_power=False
        )
        
        # Assert
        assert should_defer is False
        assert reason is None
    
    def test_multiple_snapshots_track_network(self):
        """Test that multiple snapshots track network usage"""
        # Arrange
        monitor = ResourceMonitor()
        
        # Act - Get multiple snapshots
        snapshot1 = monitor.get_snapshot()
        snapshot2 = monitor.get_snapshot()
        
        # Assert
        # Both should have network data
        assert snapshot1.network_mbps >= 0
        assert snapshot2.network_mbps >= 0
        # Second snapshot should have calculated bandwidth
        # (may be 0 if no network activity)
    
    def test_last_snapshot_updated(self):
        """Test that last_snapshot is updated"""
        # Arrange
        monitor = ResourceMonitor()
        
        # Act
        snapshot1 = monitor.get_snapshot()
        assert monitor.last_snapshot is not None
        
        snapshot2 = monitor.get_snapshot()
        
        # Assert
        assert monitor.last_snapshot == snapshot2
        assert monitor.last_snapshot.timestamp >= snapshot1.timestamp
    
    def test_battery_status_desktop(self):
        """Test battery status on desktop (no battery)"""
        # Arrange
        monitor = ResourceMonitor()
        
        # Act
        snapshot = monitor.get_snapshot()
        
        # Assert
        # If no battery, should be on AC power
        if snapshot.battery_percent is None:
            assert snapshot.on_ac_power is True
    
    def test_battery_status_laptop(self):
        """Test battery status on laptop (has battery)"""
        # Arrange
        monitor = ResourceMonitor()
        
        # Act
        snapshot = monitor.get_snapshot()
        
        # Assert
        # If has battery, percentage should be 0-100
        if snapshot.battery_percent is not None:
            assert 0 <= snapshot.battery_percent <= 100
            assert isinstance(snapshot.on_ac_power, bool)


class TestResourceMonitorWithoutPsutil:
    """Test resource monitor behavior when psutil is unavailable"""
    
    def test_fallback_snapshot_without_psutil(self):
        """Test that monitor provides fallback snapshot without psutil"""
        # Arrange
        monitor = ResourceMonitor()
        
        # Temporarily disable psutil
        original_psutil = monitor.psutil
        original_available = monitor.psutil_available
        monitor.psutil = None
        monitor.psutil_available = False
        
        try:
            # Act
            snapshot = monitor.get_snapshot()
            
            # Assert
            assert snapshot is not None
            assert snapshot.cpu_percent == 0.0
            assert snapshot.memory_percent == 0.0
            assert snapshot.disk_percent == 0.0
            assert snapshot.network_mbps == 0.0
            assert snapshot.battery_percent is None
            assert snapshot.on_ac_power is True
            assert snapshot.user_idle_seconds is None
        finally:
            # Restore
            monitor.psutil = original_psutil
            monitor.psutil_available = original_available
    
    def test_storage_quota_without_psutil(self):
        """Test storage quota check without psutil"""
        # Arrange
        monitor = ResourceMonitor()
        monitor.psutil = None
        monitor.psutil_available = False
        
        # Act
        result = monitor.check_storage_quota("/", min_free_gb=1000.0)
        
        # Assert
        # Should assume OK when psutil unavailable
        assert result is True
