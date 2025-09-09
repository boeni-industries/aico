"""
Cron Expression Parser and Scheduler

Provides efficient cron expression parsing with caching for high-performance
task scheduling.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from aico.core.logging import get_logger


@dataclass
class CronField:
    """Represents a single cron field (minute, hour, day, etc.)"""
    values: Set[int]
    is_wildcard: bool = False
    
    def matches(self, value: int) -> bool:
        """Check if given value matches this field"""
        return self.is_wildcard or value in self.values


class CronParser:
    """High-performance cron expression parser with caching"""
    
    # Field ranges: min, max, names (for month/day names)
    FIELD_RANGES = {
        'minute': (0, 59, {}),
        'hour': (0, 23, {}),
        'day': (1, 31, {}),
        'month': (1, 12, {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }),
        'weekday': (0, 6, {
            'sun': 0, 'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6
        })
    }
    
    def __init__(self, cache_size: int = 1000):
        self.logger = get_logger("backend", "scheduler.cron_parser")
        self._cache: Dict[str, Tuple[CronField, ...]] = {}
        self._cache_size = cache_size
    
    def parse(self, cron_expr: str) -> Tuple[CronField, ...]:
        """Parse cron expression into CronField objects
        
        Args:
            cron_expr: Standard 5-field cron expression (minute hour day month weekday)
            
        Returns:
            Tuple of 5 CronField objects
            
        Raises:
            ValueError: If cron expression is invalid
        """
        # Check cache first
        if cron_expr in self._cache:
            return self._cache[cron_expr]
        
        # Clean and validate expression
        cron_expr = cron_expr.strip()
        fields = cron_expr.split()
        
        if len(fields) != 5:
            raise ValueError(f"Cron expression must have 5 fields, got {len(fields)}: {cron_expr}")
        
        try:
            # Parse each field
            field_names = ['minute', 'hour', 'day', 'month', 'weekday']
            parsed_fields = []
            
            for i, (field_str, field_name) in enumerate(zip(fields, field_names)):
                field = self._parse_field(field_str, field_name)
                parsed_fields.append(field)
            
            result = tuple(parsed_fields)
            
            # Cache result (with size limit)
            if len(self._cache) >= self._cache_size:
                # Remove oldest entry (simple FIFO)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            
            self._cache[cron_expr] = result
            return result
            
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{cron_expr}': {e}")
    
    def _parse_field(self, field_str: str, field_name: str) -> CronField:
        """Parse a single cron field"""
        min_val, max_val, names = self.FIELD_RANGES[field_name]
        
        # Handle wildcard
        if field_str == '*':
            return CronField(set(range(min_val, max_val + 1)), is_wildcard=True)
        
        values = set()
        
        # Split on commas for multiple values
        for part in field_str.split(','):
            part = part.strip()
            
            if '/' in part:
                # Handle step values (e.g., */5, 0-30/2)
                range_part, step_str = part.split('/', 1)
                step = int(step_str)
                
                if range_part == '*':
                    start, end = min_val, max_val
                elif '-' in range_part:
                    start_str, end_str = range_part.split('-', 1)
                    start = self._parse_value(start_str, names)
                    end = self._parse_value(end_str, names)
                else:
                    start = end = self._parse_value(range_part, names)
                
                # Add stepped values
                for val in range(start, end + 1, step):
                    if min_val <= val <= max_val:
                        values.add(val)
                        
            elif '-' in part:
                # Handle ranges (e.g., 1-5, mon-fri)
                start_str, end_str = part.split('-', 1)
                start = self._parse_value(start_str, names)
                end = self._parse_value(end_str, names)
                
                for val in range(start, end + 1):
                    if min_val <= val <= max_val:
                        values.add(val)
            else:
                # Single value
                val = self._parse_value(part, names)
                if min_val <= val <= max_val:
                    values.add(val)
        
        if not values:
            raise ValueError(f"No valid values found in field: {field_str}")
        
        return CronField(values)
    
    def _parse_value(self, value_str: str, names: Dict[str, int]) -> int:
        """Parse a single value (number or name)"""
        value_str = value_str.strip().lower()
        
        # Try named values first
        if value_str in names:
            return names[value_str]
        
        # Try numeric value
        try:
            return int(value_str)
        except ValueError:
            raise ValueError(f"Invalid value: {value_str}")
    
    def matches(self, cron_expr: str, dt: datetime) -> bool:
        """Check if datetime matches cron expression"""
        try:
            fields = self.parse(cron_expr)
            minute_field, hour_field, day_field, month_field, weekday_field = fields
            
            # Check each field
            if not minute_field.matches(dt.minute):
                return False
            if not hour_field.matches(dt.hour):
                return False
            if not month_field.matches(dt.month):
                return False
            
            # Day and weekday have special OR logic in cron
            day_matches = day_field.matches(dt.day)
            weekday_matches = weekday_field.matches(dt.weekday())
            
            # If both day and weekday are specified (not wildcards), use OR logic
            if not day_field.is_wildcard and not weekday_field.is_wildcard:
                return day_matches or weekday_matches
            else:
                return day_matches and weekday_matches
                
        except Exception as e:
            self.logger.error(f"Error matching cron expression '{cron_expr}': {e}")
            return False
    
    def next_run_time(self, cron_expr: str, after: Optional[datetime] = None) -> Optional[datetime]:
        """Calculate next run time for cron expression
        
        Args:
            cron_expr: Cron expression to evaluate
            after: Calculate next run after this time (default: now)
            
        Returns:
            Next datetime when expression matches, or None if error
        """
        if after is None:
            after = datetime.now()
        
        try:
            # Start from next minute (cron precision is minutes)
            current = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
            
            # Limit search to prevent infinite loops
            max_iterations = 366 * 24 * 60  # One year of minutes
            
            for _ in range(max_iterations):
                if self.matches(cron_expr, current):
                    return current
                current += timedelta(minutes=1)
            
            self.logger.warning(f"Could not find next run time for cron expression: {cron_expr}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error calculating next run time for '{cron_expr}': {e}")
            return None
    
    def validate(self, cron_expr: str) -> bool:
        """Validate cron expression syntax"""
        try:
            self.parse(cron_expr)
            return True
        except ValueError:
            return False
    
    def clear_cache(self):
        """Clear the parsing cache"""
        self._cache.clear()
        self.logger.debug("Cron parser cache cleared")
