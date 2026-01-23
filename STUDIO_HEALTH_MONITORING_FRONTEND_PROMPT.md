# AICO Health Monitoring Frontend - API Integration Guide

## Backend Base URL
```
http://localhost:8000
```

All endpoints require authentication. Include the JWT token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

---

## API Endpoint 1: System Health Overview

### Request
```http
GET /api/v1/system/health
```

### Response Schema
```typescript
interface SystemHealthResponse {
  status: "healthy" | "degraded" | "critical";  // Overall system status
  healthy_services: number;                      // Count of healthy services
  total_services: number;                        // Total service count
  uptime_percentage: number;                     // System uptime % (0-100)
  uptime_seconds: number;                        // Uptime in seconds
  last_check: string;                           // ISO 8601 timestamp
  summary: {
    critical_issues: number;                    // Count of critical issues
    warnings: number;                           // Count of warnings
    healthy_components: number;                 // Count of healthy components
  };
}
```

### Example Response
```json
{
  "status": "healthy",
  "healthy_services": 8,
  "total_services": 8,
  "uptime_percentage": 99.9,
  "uptime_seconds": 5432,
  "last_check": "2026-01-23T22:13:45.123456Z",
  "summary": {
    "critical_issues": 0,
    "warnings": 1,
    "healthy_components": 8
  }
}
```

### How to Interpret

**`status` field:**
- `"healthy"` → Show green indicator, all systems operational
- `"degraded"` → Show yellow indicator, some services have issues but system is functional
- `"critical"` → Show red indicator, critical services are down

**`uptime_seconds` → Display as human-readable:**
- Convert to hours/minutes: `Math.floor(seconds / 3600)h ${Math.floor((seconds % 3600) / 60)}m`
- Example: 5432 seconds → "1h 30m"

**`uptime_percentage` → Display as percentage:**
- Format: `uptime_percentage.toFixed(1) + "%"`
- Example: 99.9 → "99.9%"

**`last_check` → Display as relative time:**
- Use library like `date-fns` or `dayjs`
- Example: "2 minutes ago", "Just now"

**Health ratio display:**
- Show as: `${healthy_services}/${total_services} services healthy`
- Calculate percentage: `(healthy_services / total_services * 100).toFixed(0) + "%"`

---

## API Endpoint 2: Service Health Details

### Request
```http
GET /api/v1/system/health/services
```

### Response Schema
```typescript
interface ServiceHealthResponse {
  services: ServiceHealth[];
}

interface ServiceHealth {
  name: string;                                  // Service name
  status: "healthy" | "degraded" | "critical";  // Service status
  group: "api" | "storage" | "processing";      // Service category
  metric: ServiceMetric;                         // Primary metric
  trend: "up" | "down" | "stable" | null;       // Metric trend (nullable)
  last_checked: string | null;                   // ISO 8601 timestamp (nullable)
  dependencies: string[] | null;                 // Dependent services (nullable)
  depends_on: string[] | null;                   // Dependencies (nullable)
}

interface ServiceMetric {
  label: string;           // Metric name (e.g., "Database Size")
  value: string;           // Pre-formatted value (e.g., "245.8 MB")
  unit: string | null;     // Unit (e.g., "MB", "ms") - nullable
  history: number[] | null;  // Historical values for sparkline - nullable
  percentage: number | null; // Percentage value 0-100 - nullable
}
```

### Example Response
```json
{
  "services": [
    {
      "name": "Backend API",
      "status": "healthy",
      "group": "api",
      "metric": {
        "label": "Uptime",
        "value": "1h 30m",
        "unit": "time",
        "history": null,
        "percentage": null
      },
      "trend": null,
      "last_checked": "2026-01-23T22:13:45.123456Z",
      "dependencies": null,
      "depends_on": null
    },
    {
      "name": "PostgreSQL",
      "status": "healthy",
      "group": "storage",
      "metric": {
        "label": "Database Size",
        "value": "245.8 MB",
        "unit": "MB",
        "history": null,
        "percentage": null
      },
      "trend": null,
      "last_checked": "2026-01-23T22:13:45.123456Z",
      "dependencies": null,
      "depends_on": null
    },
    {
      "name": "ChromaDB",
      "status": "healthy",
      "group": "storage",
      "metric": {
        "label": "Collections",
        "value": "3",
        "unit": "collections",
        "history": null,
        "percentage": null
      },
      "trend": null,
      "last_checked": "2026-01-23T22:13:45.123456Z",
      "dependencies": null,
      "depends_on": null
    },
    {
      "name": "InfluxDB",
      "status": "healthy",
      "group": "storage",
      "metric": {
        "label": "Buckets",
        "value": "2",
        "unit": "buckets",
        "history": null,
        "percentage": null
      },
      "trend": null,
      "last_checked": "2026-01-23T22:13:45.123456Z",
      "dependencies": null,
      "depends_on": null
    },
    {
      "name": "LMDB",
      "status": "healthy",
      "group": "storage",
      "metric": {
        "label": "Database Size",
        "value": "12.5 MB",
        "unit": "MB",
        "history": null,
        "percentage": null
      },
      "trend": null,
      "last_checked": "2026-01-23T22:13:45.123456Z",
      "dependencies": null,
      "depends_on": null
    },
    {
      "name": "Message Bus",
      "status": "healthy",
      "group": "processing",
      "metric": {
        "label": "Active Subscribers",
        "value": "5",
        "unit": "subscribers",
        "history": null,
        "percentage": null
      },
      "trend": null,
      "last_checked": "2026-01-23T22:13:45.123456Z",
      "dependencies": null,
      "depends_on": null
    },
    {
      "name": "Scheduler",
      "status": "healthy",
      "group": "processing",
      "metric": {
        "label": "Active Tasks",
        "value": "12 enabled",
        "unit": "tasks",
        "history": null,
        "percentage": null
      },
      "trend": null,
      "last_checked": "2026-01-23T22:13:45.123456Z",
      "dependencies": null,
      "depends_on": null
    },
    {
      "name": "Modelservice",
      "status": "healthy",
      "group": "processing",
      "metric": {
        "label": "Latency",
        "value": "150ms",
        "unit": "ms",
        "history": null,
        "percentage": null
      },
      "trend": null,
      "last_checked": "2026-01-23T22:13:45.123456Z",
      "dependencies": null,
      "depends_on": null
    }
  ]
}
```

### How to Interpret

**`status` field:**
- `"healthy"` → Green indicator (●), service operating normally
- `"degraded"` → Yellow indicator (●), service has issues but functional
- `"critical"` → Red indicator (●), service is down or severely impaired

**`group` field - Organize services into sections:**
- `"api"` → Core API services (Backend API)
- `"storage"` → Database services (PostgreSQL, ChromaDB, InfluxDB, LMDB)
- `"processing"` → Processing services (Message Bus, Scheduler, Modelservice)

**`metric.value` field:**
- Already formatted by backend - display as-is
- Examples: "245.8 MB", "1h 30m", "5", "12 enabled"

**`metric.unit` field:**
- Can be null - only display if present
- Use for tooltips or additional context

**`trend` field:**
- `"up"` → Show ↑ arrow (green)
- `"down"` → Show ↓ arrow (red)
- `"stable"` → Show → arrow (gray)
- `null` → Don't show any trend indicator

**`last_checked` field:**
- Convert to relative time: "2 minutes ago", "Just now"
- If null, show "Never checked"

**Service Grouping for Display:**
```typescript
const groupedServices = {
  api: services.filter(s => s.group === 'api'),
  storage: services.filter(s => s.group === 'storage'),
  processing: services.filter(s => s.group === 'processing')
};
```

---

## API Endpoint 3: System Issues

### Request
```http
GET /api/v1/system/health/issues
```

### Response Schema
```typescript
interface SystemIssuesResponse {
  issues: SystemIssue[];
  total_count: number;  // Total number of issues
}

interface SystemIssue {
  id: string;                                    // Issue identifier
  issue_id: string;                              // Unique issue ID
  severity: "warning" | "error" | "critical";   // Issue severity
  service: string;                               // Affected service name
  title: string;                                 // Issue title
  detected_at: string;                           // ISO 8601 timestamp
  resolved_at: string | null;                    // ISO 8601 timestamp (nullable)
  status: "active" | "resolving" | "resolved";  // Issue status
  metrics: Record<string, any>;                  // Related metrics (object)
  impact: Record<string, any>;                   // Impact assessment (object)
  remediation: RemediationAction[];              // Available remediation actions
}

interface RemediationAction {
  action_id: string;      // Action identifier
  label: string;          // Action label for display
  impact: string;         // Expected impact description
  skill_id: string | null; // Skill to invoke (nullable)
}
```

### Example Response
```json
{
  "issues": [
    {
      "id": "issue-123e4567-e89b-12d3-a456-426614174000",
      "issue_id": "high-memory-usage-backend",
      "severity": "warning",
      "service": "Backend API",
      "title": "High Memory Usage",
      "detected_at": "2026-01-23T22:10:30.123456Z",
      "resolved_at": null,
      "status": "active",
      "metrics": {
        "current_memory_mb": 1450,
        "threshold_mb": 1200,
        "percentage": 87.5
      },
      "impact": {
        "severity_level": "medium",
        "affected_operations": ["API requests", "Background tasks"]
      },
      "remediation": [
        {
          "action_id": "restart-backend",
          "label": "Restart Backend Service",
          "impact": "Will cause 10-15 seconds of downtime",
          "skill_id": null
        },
        {
          "action_id": "clear-cache",
          "label": "Clear Memory Cache",
          "impact": "No downtime, may temporarily slow responses",
          "skill_id": "maint.system.clear_cache"
        }
      ]
    }
  ],
  "total_count": 1
}
```

### How to Interpret

**`severity` field - Color coding:**
- `"warning"` → Yellow/Amber badge (#F59E0B), non-critical issue
- `"error"` → Orange badge (#FB923C), significant issue
- `"critical"` → Red badge (#DC2626), critical issue requiring immediate attention

**`status` field - Display state:**
- `"active"` → Show as "Active" with pulsing indicator
- `"resolving"` → Show as "Resolving..." with spinner
- `"resolved"` → Show as "Resolved" with checkmark (usually filtered out)

**`detected_at` field:**
- Convert to relative time: "10 minutes ago", "2 hours ago"
- Also show absolute time on hover: "Jan 23, 2026 10:10 PM"

**`metrics` object:**
- Free-form object, display key-value pairs
- Example rendering:
  ```
  Memory: 1450 MB / 1200 MB (87.5%)
  ```

**`impact` object:**
- Free-form object, display relevant information
- Example rendering:
  ```
  Severity: Medium
  Affected: API requests, Background tasks
  ```

**`remediation` array:**
- Display as action buttons
- If `skill_id` is null, action requires manual intervention
- If `skill_id` is present, can be triggered via API (future feature)
- Show `impact` as tooltip or warning text

**Issue Count Display:**
```typescript
// Count by severity
const criticalCount = issues.filter(i => i.severity === 'critical').length;
const errorCount = issues.filter(i => i.severity === 'error').length;
const warningCount = issues.filter(i => i.severity === 'warning').length;

// Display as badges:
// Critical: 0  |  Errors: 0  |  Warnings: 1
```

---

## Data Polling Strategy

### Recommended Polling Intervals

```typescript
// Poll system health overview every 15 seconds
const SYSTEM_HEALTH_POLL_INTERVAL = 15000;

// Poll service details every 30 seconds
const SERVICE_HEALTH_POLL_INTERVAL = 30000;

// Poll issues every 30 seconds
const ISSUES_POLL_INTERVAL = 30000;
```

### Implementation Example

```typescript
import { useEffect, useState } from 'react';

function useHealthData() {
  const [systemHealth, setSystemHealth] = useState(null);
  const [services, setServices] = useState([]);
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchSystemHealth = async () => {
      try {
        const response = await fetch('/api/v1/system/health', {
          headers: {
            'Authorization': `Bearer ${getAuthToken()}`
          }
        });
        const data = await response.json();
        setSystemHealth(data);
      } catch (err) {
        setError(err.message);
      }
    };

    const fetchServices = async () => {
      try {
        const response = await fetch('/api/v1/system/health/services', {
          headers: {
            'Authorization': `Bearer ${getAuthToken()}`
          }
        });
        const data = await response.json();
        setServices(data.services);
      } catch (err) {
        setError(err.message);
      }
    };

    const fetchIssues = async () => {
      try {
        const response = await fetch('/api/v1/system/health/issues', {
          headers: {
            'Authorization': `Bearer ${getAuthToken()}`
          }
        });
        const data = await response.json();
        setIssues(data.issues);
      } catch (err) {
        setError(err.message);
      }
    };

    // Initial fetch
    Promise.all([fetchSystemHealth(), fetchServices(), fetchIssues()])
      .finally(() => setLoading(false));

    // Set up polling
    const healthInterval = setInterval(fetchSystemHealth, 15000);
    const servicesInterval = setInterval(fetchServices, 30000);
    const issuesInterval = setInterval(fetchIssues, 30000);

    return () => {
      clearInterval(healthInterval);
      clearInterval(servicesInterval);
      clearInterval(issuesInterval);
    };
  }, []);

  return { systemHealth, services, issues, loading, error };
}
```

---

## UI Layout Requirements

### Dashboard Structure

**1. System Overview Section (Top)**
- Display `status` as large colored indicator:
  - `"healthy"` → Green circle (●) + "All Systems Operational"
  - `"degraded"` → Yellow circle (●) + "Some Services Degraded"
  - `"critical"` → Red circle (●) + "Critical Issues Detected"
- Show `uptime_seconds` formatted as "Running for Xh Ym"
- Show `healthy_services / total_services` as "X/Y services healthy"
- Display `last_check` as "Last updated: X seconds ago"

**2. Services Section (Middle)**

Group services by `group` field:

```typescript
// Group services
const apiServices = services.filter(s => s.group === 'api');
const storageServices = services.filter(s => s.group === 'storage');
const processingServices = services.filter(s => s.group === 'processing');
```

For each service, display a card with:
- Service `name` as header
- `status` as colored dot (● green/yellow/red)
- `metric.label`: `metric.value` (e.g., "Database Size: 245.8 MB")
- `trend` as arrow if not null (↑ ↓ →)
- `last_checked` as relative time

**3. Issues Section (Bottom)**

Display issue count badges:
```typescript
const criticalCount = issues.filter(i => i.severity === 'critical').length;
const errorCount = issues.filter(i => i.severity === 'error').length;
const warningCount = issues.filter(i => i.severity === 'warning').length;

// Show as: "Critical: 0  |  Errors: 0  |  Warnings: 1"
```

For each issue, display:
- `severity` badge (colored)
- `title` as heading
- `service` name
- `detected_at` as relative time
- `remediation` actions as buttons

---

## Color Palette (Exact Values)

### Status Colors
```css
/* Healthy/Success */
--status-healthy: #10B981;     /* green-500 */
--status-healthy-bg: #D1FAE5;  /* green-100 */

/* Degraded/Warning */
--status-degraded: #F59E0B;    /* amber-500 */
--status-degraded-bg: #FEF3C7; /* amber-100 */

/* Critical/Error */
--status-critical: #DC2626;    /* red-600 */
--status-critical-bg: #FEE2E2; /* red-100 */
```

### Severity Colors (for issues)
```css
--severity-warning: #F59E0B;   /* amber-500 */
--severity-error: #FB923C;     /* orange-400 */
--severity-critical: #DC2626;  /* red-600 */
```

### Group Colors (for service categories)
```css
--group-api: #8B5CF6;          /* purple-500 */
--group-storage: #06B6D4;      /* cyan-500 */
--group-processing: #EC4899;   /* pink-500 */
```

---

## Utility Functions

### Format Uptime
```typescript
function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

// Usage: formatUptime(5432) → "1h 30m"
```

### Format Relative Time
```typescript
import { formatDistanceToNow } from 'date-fns';

function formatRelativeTime(isoTimestamp: string): string {
  return formatDistanceToNow(new Date(isoTimestamp), { addSuffix: true });
}

// Usage: formatRelativeTime("2026-01-23T22:13:45Z") → "2 minutes ago"
```

### Get Status Color
```typescript
function getStatusColor(status: 'healthy' | 'degraded' | 'critical'): string {
  const colors = {
    healthy: '#10B981',
    degraded: '#F59E0B',
    critical: '#DC2626'
  };
  return colors[status];
}
```

### Get Severity Badge Color
```typescript
function getSeverityColor(severity: 'warning' | 'error' | 'critical'): string {
  const colors = {
    warning: '#F59E0B',
    error: '#FB923C',
    critical: '#DC2626'
  };
  return colors[severity];
}
```

---

## Error Handling

### API Error Responses

If an endpoint fails, you'll receive:
```json
{
  "detail": "Error message here"
}
```

### Handle Errors
```typescript
try {
  const response = await fetch('/api/v1/system/health');
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch health data');
  }
  
  const data = await response.json();
  // Use data...
} catch (error) {
  // Show error toast/notification
  console.error('Health check failed:', error.message);
  // Keep showing last known good data
}
```

### Retry Logic
```typescript
async function fetchWithRetry(url: string, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${getAuthToken()}` }
      });
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
}
```

---

## Testing the Integration

### 1. Test with curl

```bash
# Get auth token first
TOKEN="your-jwt-token-here"

# Test system health
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/system/health

# Test service health
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/system/health/services

# Test issues
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/system/health/issues
```

### 2. Expected Service Names

You will always receive these 8 services:
1. **Backend API** (group: "api")
2. **PostgreSQL** (group: "storage")
3. **ChromaDB** (group: "storage")
4. **InfluxDB** (group: "storage")
5. **LMDB** (group: "storage")
6. **Message Bus** (group: "processing")
7. **Scheduler** (group: "processing")
8. **Modelservice** (group: "processing")

### 3. Null Value Handling

**Important:** Many fields can be `null`. Always check before using:

```typescript
// ✅ Correct
const trendArrow = service.trend ? getTrendArrow(service.trend) : null;

// ✅ Correct
const lastChecked = service.last_checked 
  ? formatRelativeTime(service.last_checked)
  : 'Never checked';

// ✅ Correct  
const unit = service.metric.unit ? ` ${service.metric.unit}` : '';

// ❌ Wrong - will crash if null
const trendArrow = getTrendArrow(service.trend);
```

---

## Implementation Checklist

### Phase 1: Basic Display
- [ ] Create TypeScript interfaces matching API schemas
- [ ] Implement `useHealthData` hook with polling
- [ ] Build System Overview component
- [ ] Build Service Card component
- [ ] Build Service List with grouping
- [ ] Build Issues List component
- [ ] Add status color indicators
- [ ] Format timestamps as relative time
- [ ] Format uptime as human-readable

### Phase 2: Polish
- [ ] Add loading states
- [ ] Add error handling with retry
- [ ] Add trend arrows (↑ ↓ →)
- [ ] Add severity badges for issues
- [ ] Add "Last updated" timestamp
- [ ] Add smooth transitions
- [ ] Make responsive (mobile/tablet/desktop)

### Phase 3: Advanced
- [ ] Add filtering by status
- [ ] Add search by service name
- [ ] Add service detail modal
- [ ] Add issue remediation action buttons
- [ ] Add manual refresh button
- [ ] Add auto-refresh toggle
- [ ] Add toast notifications for new issues

---

## Quick Reference

### API Endpoints Summary
```
GET /api/v1/system/health          → System overview
GET /api/v1/system/health/services → Service details
GET /api/v1/system/health/issues   → Active issues
```

### Status Values
```
System/Service: "healthy" | "degraded" | "critical"
Issue Severity: "warning" | "error" | "critical"
Issue Status: "active" | "resolving" | "resolved"
```

### Service Groups
```
"api"        → Backend API
"storage"    → PostgreSQL, ChromaDB, InfluxDB, LMDB
"processing" → Message Bus, Scheduler, Modelservice
```

### Nullable Fields (Always Check!)
```typescript
service.trend          // can be null
service.last_checked   // can be null
service.dependencies   // can be null
service.depends_on     // can be null
service.metric.unit    // can be null
service.metric.history // can be null
service.metric.percentage // can be null
issue.resolved_at      // can be null
action.skill_id        // can be null
```

### Color Codes
```
Healthy:   #10B981 (green)
Degraded:  #F59E0B (amber)
Critical:  #DC2626 (red)

Warning:   #F59E0B (amber)
Error:     #FB923C (orange)
```

