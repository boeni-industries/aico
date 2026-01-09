"""
Metrics Drill-Down API Endpoints

Provides detailed breakdowns of API Gateway metrics by:
- Service (Conversation, Memory, Agency, etc.)
- Category (user_chat, admin, security, etc.)
- Endpoint (specific paths)
- HTTP Method (GET, POST, etc.)
- Status Code (2xx, 4xx, 5xx)

Used by MetricDetailDrawer for interactive drill-down analysis.
"""

import time
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field

from backend.api.system.dependencies import get_db_connection


router = APIRouter(prefix="/metrics/drilldown", tags=["metrics-drilldown"])


# Response Models
class BreakdownItem(BaseModel):
    """Single item in a breakdown."""
    name: str
    value: float
    count: int
    percentage: float
    avg_latency: Optional[float] = None
    error_rate: Optional[float] = None


class MetricBreakdown(BaseModel):
    """Breakdown response for a metric."""
    metric_type: str  # "requests", "latency", "errors"
    breakdown_by: str  # "service", "category", "endpoint", "method", "status"
    time_window: str  # "1h", "24h", "7d"
    total_value: float
    items: List[BreakdownItem]


# Helper functions
def get_time_cutoff(window: str) -> float:
    """Get timestamp cutoff for time window."""
    now = time.time()
    windows = {
        "1h": now - 3600,
        "24h": now - (24 * 3600),
        "7d": now - (7 * 24 * 3600)
    }
    return windows.get(window, windows["24h"])


@router.get("/requests", response_model=MetricBreakdown)
async def get_requests_breakdown(
    request: Request,
    by: Literal["service", "category", "endpoint", "method", "status"] = Query("service"),
    window: Literal["1h", "24h", "7d"] = Query("24h")
):
    """
    Get requests/sec breakdown by service, category, endpoint, method, or status.
    
    Args:
        by: Breakdown dimension (service, category, endpoint, method, status)
        window: Time window (1h, 24h, 7d)
    
    Returns:
        Breakdown of requests with counts, percentages, and avg latency
    """
    db_connection = get_db_connection(request)
    cutoff = get_time_cutoff(window)
    
    # Map breakdown type to SQL column
    column_map = {
        "service": "service",
        "category": "category",
        "endpoint": "path",
        "method": "method",
        "status": "CASE WHEN status_code BETWEEN 200 AND 299 THEN '2xx' WHEN status_code BETWEEN 300 AND 399 THEN '3xx' WHEN status_code BETWEEN 400 AND 499 THEN '4xx' WHEN status_code BETWEEN 500 AND 599 THEN '5xx' ELSE 'other' END"
    }
    
    group_column = column_map[by]
    
    with db_connection.get_connection() as conn:
        # Get total requests for percentage calculation
        result = conn.execute(
            "SELECT COUNT(*) FROM otel_api_requests WHERE timestamp > ?",
            (cutoff,)
        ).fetchone()
        total_requests = result[0] if result else 0
        
        if total_requests == 0:
            return MetricBreakdown(
                metric_type="requests",
                breakdown_by=by,
                time_window=window,
                total_value=0.0,
                items=[]
            )
        
        # Get breakdown
        query = f"""
            SELECT 
                {group_column} as name,
                COUNT(*) as count,
                AVG(latency_ms) as avg_latency,
                SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as error_rate
            FROM otel_api_requests
            WHERE timestamp > ?
            GROUP BY name
            ORDER BY count DESC
            LIMIT 20
        """
        
        result = conn.execute(query, (cutoff,)).fetchall()
        
        # Calculate time window in seconds for req/s calculation
        window_seconds = {
            "1h": 3600,
            "24h": 24 * 3600,
            "7d": 7 * 24 * 3600
        }[window]
        
        items = []
        for row in result:
            name = row[0] or "unknown"
            count = row[1]
            avg_latency = row[2]
            error_rate = row[3]
            
            items.append(BreakdownItem(
                name=name,
                value=count / window_seconds,  # Convert to req/s
                count=count,
                percentage=(count / total_requests) * 100,
                avg_latency=round(avg_latency, 2) if avg_latency else None,
                error_rate=round(error_rate, 2) if error_rate else 0.0
            ))
        
        return MetricBreakdown(
            metric_type="requests",
            breakdown_by=by,
            time_window=window,
            total_value=total_requests / window_seconds,
            items=items
        )


@router.get("/latency", response_model=MetricBreakdown)
async def get_latency_breakdown(
    request: Request,
    by: Literal["service", "category", "endpoint", "method"] = Query("service"),
    window: Literal["1h", "24h", "7d"] = Query("24h")
):
    """
    Get average response time breakdown by service, category, endpoint, or method.
    
    Args:
        by: Breakdown dimension (service, category, endpoint, method)
        window: Time window (1h, 24h, 7d)
    
    Returns:
        Breakdown of average latency with request counts
    """
    db_connection = get_db_connection(request)
    cutoff = get_time_cutoff(window)
    
    column_map = {
        "service": "service",
        "category": "category",
        "endpoint": "path",
        "method": "method"
    }
    
    group_column = column_map[by]
    
    with db_connection.get_connection() as conn:
        # Get overall average for reference
        result = conn.execute(
            "SELECT AVG(latency_ms), COUNT(*) FROM otel_api_requests WHERE timestamp > ?",
            (cutoff,)
        ).fetchone()
        overall_avg = result[0] if result and result[0] else 0.0
        total_requests = result[1] if result else 0
        
        if total_requests == 0:
            return MetricBreakdown(
                metric_type="latency",
                breakdown_by=by,
                time_window=window,
                total_value=0.0,
                items=[]
            )
        
        # Get breakdown
        query = f"""
            SELECT 
                {group_column} as name,
                AVG(latency_ms) as avg_latency,
                COUNT(*) as count,
                MIN(latency_ms) as min_latency,
                MAX(latency_ms) as max_latency
            FROM otel_api_requests
            WHERE timestamp > ?
            GROUP BY name
            ORDER BY avg_latency DESC
            LIMIT 20
        """
        
        result = conn.execute(query, (cutoff,)).fetchall()
        
        items = []
        for row in result:
            name = row[0] or "unknown"
            avg_latency = row[1]
            count = row[2]
            
            items.append(BreakdownItem(
                name=name,
                value=round(avg_latency, 2) if avg_latency else 0.0,
                count=count,
                percentage=(count / total_requests) * 100,
                avg_latency=round(avg_latency, 2) if avg_latency else None
            ))
        
        return MetricBreakdown(
            metric_type="latency",
            breakdown_by=by,
            time_window=window,
            total_value=round(overall_avg, 2),
            items=items
        )


@router.get("/errors", response_model=MetricBreakdown)
async def get_errors_breakdown(
    request: Request,
    by: Literal["service", "category", "endpoint", "status"] = Query("service"),
    window: Literal["1h", "24h", "7d"] = Query("24h")
):
    """
    Get error rate breakdown by service, category, endpoint, or status code.
    
    Args:
        by: Breakdown dimension (service, category, endpoint, status)
        window: Time window (1h, 24h, 7d)
    
    Returns:
        Breakdown of error rates with error counts
    """
    db_connection = get_db_connection(request)
    cutoff = get_time_cutoff(window)
    
    column_map = {
        "service": "service",
        "category": "category",
        "endpoint": "path",
        "status": "status_code"
    }
    
    group_column = column_map[by]
    
    with db_connection.get_connection() as conn:
        # Get overall error rate
        result = conn.execute(
            """SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors
               FROM otel_api_requests 
               WHERE timestamp > ?""",
            (cutoff,)
        ).fetchone()
        
        total_requests = result[0] if result else 0
        total_errors = result[1] if result else 0
        overall_error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0.0
        
        if total_requests == 0:
            return MetricBreakdown(
                metric_type="errors",
                breakdown_by=by,
                time_window=window,
                total_value=0.0,
                items=[]
            )
        
        # Get breakdown
        if by == "status":
            # For status breakdown, show actual status codes
            query = """
                SELECT 
                    status_code as name,
                    COUNT(*) as count,
                    AVG(latency_ms) as avg_latency
                FROM otel_api_requests
                WHERE timestamp > ? AND status_code >= 400
                GROUP BY status_code
                ORDER BY count DESC
                LIMIT 20
            """
        else:
            query = f"""
                SELECT 
                    {group_column} as name,
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors,
                    AVG(latency_ms) as avg_latency
                FROM otel_api_requests
                WHERE timestamp > ?
                GROUP BY name
                HAVING errors > 0
                ORDER BY errors DESC
                LIMIT 20
            """
        
        result = conn.execute(query, (cutoff,)).fetchall()
        
        items = []
        for row in result:
            if by == "status":
                name = str(row[0])
                count = row[1]
                avg_latency = row[2]
                error_rate = 100.0  # All are errors
            else:
                name = row[0] or "unknown"
                total = row[1]
                errors = row[2]
                avg_latency = row[3]
                count = errors
                error_rate = (errors / total * 100) if total > 0 else 0.0
            
            items.append(BreakdownItem(
                name=name,
                value=error_rate,
                count=count,
                percentage=(count / total_errors * 100) if total_errors > 0 else 0.0,
                avg_latency=round(avg_latency, 2) if avg_latency else None,
                error_rate=round(error_rate, 2)
            ))
        
        return MetricBreakdown(
            metric_type="errors",
            breakdown_by=by,
            time_window=window,
            total_value=round(overall_error_rate, 2),
            items=items
        )
