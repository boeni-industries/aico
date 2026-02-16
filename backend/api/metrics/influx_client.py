"""
InfluxDB Client Abstraction for Metrics

Provides high-level query interface for metrics collection.
Encapsulates InfluxDB connection management and query execution.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import statistics

from aico.data.influx.connection import InfluxDBConnection
from aico.core.logging import get_logger

logger = get_logger("backend.api.metrics.influx_client")


class MetricsInfluxClient:
    """
    High-level client for querying metrics from InfluxDB.
    
    Provides convenient methods for common metric queries with
    automatic connection management and error handling.
    """
    
    def __init__(self):
        """Initialize the metrics client."""
        self._conn: Optional[InfluxDBConnection] = None
    
    def __enter__(self):
        """Context manager entry - establish connection."""
        self._conn = InfluxDBConnection()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def query(self, flux_query: str) -> List[Dict[str, Any]]:
        """
        Execute a Flux query and return results.
        
        Args:
            flux_query: Flux query string
            
        Returns:
            List of result dictionaries
            
        Raises:
            RuntimeError: If client not used as context manager
        """
        if not self._conn:
            raise RuntimeError("MetricsInfluxClient must be used as context manager")
        
        return self._conn.query(flux_query)
    
    def count_points(
        self,
        measurement: str,
        time_range: str,
        filters: Optional[Dict[str, str]] = None
    ) -> int:
        """
        Count data points in a measurement.
        
        Args:
            measurement: Measurement name (e.g., "api_request")
            time_range: Time range (e.g., "-1h", "-24h")
            filters: Optional tag filters
            
        Returns:
            Count of data points
        """
        filter_clauses = self._build_filter_clauses(filters)
        
        query = f'''
            from(bucket: "aico_telemetry")
            |> range(start: {time_range})
            |> filter(fn: (r) => r._measurement == "{measurement}")
            {filter_clauses}
            |> count()
        '''
        
        results = self.query(query)
        return sum(r.get('value', 0) for r in results)
    
    def sum_field(
        self,
        measurement: str,
        field: str,
        time_range: str,
        filters: Optional[Dict[str, str]] = None,
        bucket: str = "aico_telemetry_downsampled"
    ) -> int:
        """
        Sum values of a field in a measurement (for pre-aggregated count data).
        
        Args:
            measurement: Measurement name (e.g., "api_request_counts_1m")
            field: Field name (e.g., "status_code_i")
            time_range: Time range (e.g., "-1h", "-24h")
            filters: Optional tag filters
            bucket: Bucket name (default: downsampled bucket)
            
        Returns:
            Sum of field values
        """
        filter_clauses = self._build_filter_clauses(filters)
        
        query = f'''
            from(bucket: "{bucket}")
            |> range(start: {time_range})
            |> filter(fn: (r) => r._measurement == "{measurement}")
            |> filter(fn: (r) => r._field == "{field}")
            {filter_clauses}
            |> sum()
        '''
        
        results = self.query(query)
        return int(sum(r.get('value', 0) for r in results))
    
    def count_points_by_field(
        self,
        measurement: str,
        field: str,
        field_value: Any,
        time_range: str,
        filters: Optional[Dict[str, str]] = None
    ) -> int:
        """
        Count data points filtered by field value.
        
        Args:
            measurement: Measurement name (e.g., "scheduler_job")
            field: Field name (e.g., "success_b")
            field_value: Field value to filter by (e.g., True, False)
            time_range: Time range (e.g., "-1h", "-24h")
            filters: Optional tag filters
            
        Returns:
            Count of data points matching field value
        """
        filter_clauses = self._build_filter_clauses(filters)
        
        # Convert Python boolean to Flux boolean
        if isinstance(field_value, bool):
            flux_value = "true" if field_value else "false"
        elif isinstance(field_value, str):
            flux_value = f'"{field_value}"'
        else:
            flux_value = str(field_value)
        
        query = f'''
            from(bucket: "aico_telemetry")
            |> range(start: {time_range})
            |> filter(fn: (r) => r._measurement == "{measurement}")
            |> filter(fn: (r) => r._field == "{field}")
            |> filter(fn: (r) => r._value == {flux_value})
            {filter_clauses}
            |> count()
        '''
        
        results = self.query(query)
        return sum(r.get('value', 0) for r in results)
    
    def count_field_points(
        self,
        measurement: str,
        field: str,
        time_range: str,
        filters: Optional[Dict[str, str]] = None
    ) -> int:
        """
        Count all data points for a specific field (regardless of value).
        
        Useful when you need to count actual events but InfluxDB stores multiple
        fields per event (e.g., scheduler_job has both success_b and duration_ms_f).
        
        Args:
            measurement: Measurement name
            field: Field name to count
            time_range: Time range
            filters: Optional tag filters
            
        Returns:
            Count of data points for this field
        """
        filter_clauses = self._build_filter_clauses(filters)
        
        query = f'''
            from(bucket: "aico_telemetry")
            |> range(start: {time_range})
            |> filter(fn: (r) => r._measurement == "{measurement}")
            |> filter(fn: (r) => r._field == "{field}")
            {filter_clauses}
            |> count()
        '''
        
        results = self.query(query)
        return sum(r.get('value', 0) for r in results)
    
    def mean_field(
        self,
        measurement: str,
        field: str,
        time_range: str,
        filters: Optional[Dict[str, str]] = None,
        bucket: str = "aico_telemetry"
    ) -> float:
        """
        Calculate mean of a field.
        
        Args:
            measurement: Measurement name
            field: Field name
            time_range: Time range
            filters: Optional tag filters
            bucket: Bucket name (default: raw telemetry bucket)
            
        Returns:
            Mean value
        """
        filter_clauses = self._build_filter_clauses(filters)
        
        query = f'''
            from(bucket: "{bucket}")
            |> range(start: {time_range})
            |> filter(fn: (r) => r._measurement == "{measurement}")
            |> filter(fn: (r) => r._field == "{field}")
            {filter_clauses}
            |> mean()
        '''
        
        results = self.query(query)
        return results[0].get('value', 0.0) if results else 0.0
    
    def percentile_field(
        self,
        measurement: str,
        field: str,
        percentile: float,
        time_range: str,
        filters: Optional[Dict[str, str]] = None,
        bucket: str = "aico_telemetry"
    ) -> float:
        """
        Calculate percentile of a field.
        
        Args:
            measurement: Measurement name
            field: Field name
            percentile: Percentile (0.0 to 1.0)
            time_range: Time range
            filters: Optional tag filters
            
        Returns:
            Percentile value
        """
        filter_clauses = self._build_filter_clauses(filters)
        
        query = f'''
            from(bucket: "{bucket}")
            |> range(start: {time_range})
            |> filter(fn: (r) => r._measurement == "{measurement}")
            |> filter(fn: (r) => r._field == "{field}")
            {filter_clauses}
            |> quantile(q: {percentile})
        '''
        
        results = self.query(query)
        return results[0].get('value', 0.0) if results else 0.0
    
    def group_count(
        self,
        measurement: str,
        group_by: str,
        time_range: str,
        filters: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Count points grouped by a tag.
        
        Args:
            measurement: Measurement name
            group_by: Tag to group by
            time_range: Time range
            filters: Optional tag filters
            limit: Optional limit on results
            
        Returns:
            Dictionary mapping group values to counts
        """
        filter_clauses = self._build_filter_clauses(filters)
        limit_clause = f"|> limit(n: {limit})" if limit else ""
        
        query = f'''
            from(bucket: "aico_telemetry")
            |> range(start: {time_range})
            |> filter(fn: (r) => r._measurement == "{measurement}")
            {filter_clauses}
            |> group(columns: ["{group_by}"])
            |> count()
            |> sort(desc: true)
            {limit_clause}
        '''
        
        results = self.query(query)
        return {r.get(group_by, 'unknown'): r.get('value', 0) for r in results}
    
    def sparkline(
        self,
        measurement: str,
        field: str,
        intervals: int,
        interval_duration: str,
        aggregation: str = "mean",
        filters: Optional[Dict[str, str]] = None
    ) -> List[float]:
        """
        Generate sparkline data (time-series of aggregated values).
        
        Optimized to use InfluxDB's window() function for efficient aggregation
        in a single query instead of N separate queries.
        
        Args:
            measurement: Measurement name
            field: Field name (or None for count)
            intervals: Number of intervals
            interval_duration: Duration of each interval (e.g., "1m")
            aggregation: Aggregation function (mean, count, sum)
            filters: Optional tag filters
            
        Returns:
            List of aggregated values for each interval
        """
        filter_clauses = self._build_filter_clauses(filters)
        total_duration = intervals * self._parse_duration_to_seconds(interval_duration)
        
        if field:
            # Field-based aggregation using window()
            query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -{total_duration}s)
                |> filter(fn: (r) => r._measurement == "{measurement}")
                |> filter(fn: (r) => r._field == "{field}")
                {filter_clauses}
                |> window(every: {interval_duration})
                |> {aggregation}()
                |> duplicate(column: "_stop", as: "_time")
            '''
        else:
            # Count-based aggregation using window()
            query = f'''
                from(bucket: "aico_telemetry")
                |> range(start: -{total_duration}s)
                |> filter(fn: (r) => r._measurement == "{measurement}")
                {filter_clauses}
                |> window(every: {interval_duration})
                |> count()
                |> duplicate(column: "_stop", as: "_time")
            '''
        
        results = self.query(query)
        
        # Extract values from windowed results
        sparkline_data = []
        for r in results:
            value = r.get('value', 0.0)
            
            # For count sparklines, convert to rate if needed
            if not field and aggregation == "mean":
                duration_seconds = self._parse_duration_to_seconds(interval_duration)
                value = value / duration_seconds if duration_seconds > 0 else 0.0
            
            sparkline_data.append(value)
        
        # Pad with zeros if we got fewer intervals than expected
        while len(sparkline_data) < intervals:
            sparkline_data.insert(0, 0.0)
        
        # Trim if we got more intervals than expected
        sparkline_data = sparkline_data[-intervals:]
        
        return sparkline_data
    
    def _build_filter_clauses(self, filters: Optional[Dict[str, str]]) -> str:
        """
        Build Flux filter clauses from dictionary.
        
        Args:
            filters: Dictionary of tag filters
            
        Returns:
            Flux filter clauses as string
        """
        if not filters:
            return ""
        
        clauses = []
        for key, value in filters.items():
            clauses.append(f'|> filter(fn: (r) => r.{key} == "{value}")')
        
        return "\n            ".join(clauses)
    
    def _parse_duration_to_seconds(self, duration: str) -> int:
        """
        Parse duration string to seconds.
        
        Args:
            duration: Duration string (e.g., "1m", "1h", "1d")
            
        Returns:
            Duration in seconds
        """
        if duration.endswith('s'):
            return int(duration[:-1])
        elif duration.endswith('m'):
            return int(duration[:-1]) * 60
        elif duration.endswith('h'):
            return int(duration[:-1]) * 3600
        elif duration.endswith('d'):
            return int(duration[:-1]) * 86400
        else:
            return 60  # Default to 1 minute


def calculate_percentile(values: List[float], percentile: float) -> float:
    """
    Calculate percentile from list of values.
    
    Args:
        values: List of numeric values
        percentile: Percentile (0.0 to 1.0)
        
    Returns:
        Percentile value
    """
    if not values:
        return 0.0
    
    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile)
    return sorted_values[min(index, len(sorted_values) - 1)]


def calculate_trend(current: float, previous: float) -> float:
    """
    Calculate percentage trend.
    
    Args:
        current: Current value
        previous: Previous value
        
    Returns:
        Percentage change
    """
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100


def get_metric_status(value: float, thresholds: Dict[str, float]) -> str:
    """
    Determine metric status based on thresholds.
    
    Args:
        value: Metric value
        thresholds: Dictionary with 'warning' and 'critical' thresholds
        
    Returns:
        Status string: 'healthy', 'warning', or 'critical'
    """
    if value >= thresholds.get("critical", float("inf")):
        return "critical"
    elif value >= thresholds.get("warning", float("inf")):
        return "warning"
    return "healthy"
