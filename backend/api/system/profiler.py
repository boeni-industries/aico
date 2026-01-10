"""
Performance Profiler for Slow Endpoints

Adds detailed timing instrumentation to identify bottlenecks in slow API endpoints.
"""

import time
import functools
from typing import Callable, Any
from contextlib import contextmanager

from aico.core.logging import get_logger

logger = get_logger("backend", "api.profiler")


@contextmanager
def profile_section(section_name: str, log_threshold_ms: float = 100):
    """
    Context manager to profile a code section.
    
    Usage:
        with profile_section("database_query"):
            result = db.execute(...)
    
    Args:
        section_name: Name of the section being profiled
        log_threshold_ms: Log if section takes longer than this (ms)
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        if duration_ms >= log_threshold_ms:
            logger.info(
                f"[PROFILE] {section_name}: {duration_ms:.2f}ms",
                extra={"section": section_name, "duration_ms": duration_ms}
            )


def profile_endpoint(func: Callable) -> Callable:
    """
    Decorator to profile an entire endpoint with section breakdowns.
    
    Usage:
        @profile_endpoint
        async def get_system_overview(...):
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        endpoint_start = time.perf_counter()
        endpoint_name = f"{func.__module__}.{func.__name__}"
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            total_duration_ms = (time.perf_counter() - endpoint_start) * 1000
            if total_duration_ms >= 500:  # Log if endpoint takes > 500ms
                logger.warning(
                    f"[PROFILE] Endpoint {endpoint_name} took {total_duration_ms:.2f}ms",
                    extra={
                        "endpoint": endpoint_name,
                        "total_duration_ms": total_duration_ms
                    }
                )
    
    return wrapper


class PerformanceTimer:
    """
    Utility class for detailed performance timing within an endpoint.
    
    Usage:
        timer = PerformanceTimer("get_system_overview")
        
        timer.start("database_query")
        result = db.execute(...)
        timer.stop("database_query")
        
        timer.start("lmdb_scan")
        conversations = scan_lmdb()
        timer.stop("lmdb_scan")
        
        timer.report()  # Logs breakdown
    """
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.sections = {}
        self.current_section = None
        self.current_start = None
        self.operation_start = time.perf_counter()
    
    def start(self, section_name: str):
        """Start timing a section."""
        if self.current_section:
            # Auto-stop previous section
            self.stop(self.current_section)
        
        self.current_section = section_name
        self.current_start = time.perf_counter()
    
    def stop(self, section_name: str = None):
        """Stop timing a section."""
        if not self.current_start:
            return
        
        duration_ms = (time.perf_counter() - self.current_start) * 1000
        
        section = section_name or self.current_section
        if section:
            self.sections[section] = duration_ms
        
        self.current_section = None
        self.current_start = None
    
    def report(self, log_threshold_ms: float = 100):
        """Report timing breakdown."""
        total_duration_ms = (time.perf_counter() - self.operation_start) * 1000
        
        if total_duration_ms < log_threshold_ms:
            return
        
        # Sort sections by duration
        sorted_sections = sorted(self.sections.items(), key=lambda x: x[1], reverse=True)
        
        breakdown = ", ".join([f"{name}: {dur:.0f}ms" for name, dur in sorted_sections])
        accounted_time = sum(self.sections.values())
        unaccounted = total_duration_ms - accounted_time
        
        logger.warning(
            f"[PROFILE] {self.operation_name} breakdown (total: {total_duration_ms:.0f}ms): "
            f"{breakdown}, unaccounted: {unaccounted:.0f}ms",
            extra={
                "operation": self.operation_name,
                "total_ms": total_duration_ms,
                "sections": self.sections,
                "unaccounted_ms": unaccounted
            }
        )
