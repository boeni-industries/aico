# System – Layout & Content Design

## 1. Information Design Concept

The System section is AICO's **"car dashboard"** – designed to answer two critical questions:

1. **"What's wrong?"** – Instant health visibility
2. **"How do I fix it?"** – Actionable troubleshooting without CLI/config files

### Core Design Principles

- **Glanceable**: One-look system health status (green/yellow/red)
- **Actionable**: Every problem has a visible solution path
- **Reassuring**: Clear feedback that the system is working (or being fixed)
- **No CLI Required**: All common tasks accessible through UI
- **Human-Friendly**: Technical details hidden behind progressive disclosure

The user should feel **in control** and **confident**, not overwhelmed by technical complexity.

## 2. Page Layout

The System page uses a **tab-based layout** optimized for different user needs:

### 2.1 Health Tab (Default) ⭐

**Purpose:** Instant system health visibility and quick actions.

**User Question:** *"Is everything OK right now?"*

**Layout:**

**Top Section – System Status Dashboard**
- **Overall Health Indicator**: Large, prominent status (Healthy/Degraded/Critical)
- **Service Status Grid**: 
  - Backend API (green/yellow/red with response time)
  - Modelservice (with active models count)
  - Database (connection status, disk usage %)
  - Message Bus (broker status, queue depth)
  - Memory Systems (working/semantic/KG health)
  - Scheduler (active jobs, next execution)
- Each service card shows:
  - Status icon with color
  - Key metric (response time, memory usage, etc.)
  - Last check timestamp
  - Quick action button (Restart, View Logs, Diagnose)

**Middle Section – Active Alerts**
- Warning/error cards with:
  - Problem description in plain language
  - Impact assessment ("Conversations may be slow")
  - Suggested fix with action button
  - "Learn More" link to docs

**Bottom Section – Quick Actions**
- One-click buttons for common tasks:
  - "Run Health Check" (full system diagnostic)
  - "Clear All Caches"
  - "Restart Services"
  - "View System Logs"
  - "Test Connections"

### 2.2 Configuration Tab

**Purpose:** Unified configuration management and validation.

**Layout:**
- **Top row – Configuration domains**
  - Cards for each domain (Core, Database, Security, Service Auth).
  - Each card: validation status, source hierarchy, last modified.

- **Middle – Configuration editor**
  - Left: Domain selector and key browser.
  - Right: Live YAML/JSON editor with schema validation.

- **Bottom – Actions**
  - Export/Import buttons, Reload configuration, Validate all domains.

### 2.3 Models & Resources Tab

**Purpose:** Manage what's loaded and using resources.

**User Question:** *"What's running and can I free up resources?"*

**Layout:**

**Top Section – Resource Overview**
- Cards showing:
  - **CPU Usage**: Gauge with breakdown by service
  - **Memory Usage**: Gauge with breakdown by component
  - **Disk Space**: Usage with cleanup suggestions
  - **GPU Status**: If available, utilization

**Middle Section – Active Models**
- Table/cards for each loaded model:
  - Model name and size
  - Memory footprint
  - Last used timestamp
  - Usage count today
  - Actions: "Unload", "Swap", "View Details"
- "Load New Model" button with model browser

**Bottom Section – Plugin Management**
- List of installed plugins:
  - Name, version, status (enabled/disabled)
  - Resource usage if active
  - Enable/disable toggle
  - "Configure" button (opens plugin settings)
  - "Remove" button (with dependency warning)
- "Install Plugin" button

### 2.4 Maintenance Tab

**Purpose:** Database and system maintenance made easy.

**User Question:** *"How do I keep things running smoothly?"*

**Layout:**

**Top Section – Database Health**
- Cards showing:
  - Database size and growth trend
  - Last vacuum/optimization
  - Fragmentation level
  - Backup status (last backup, next scheduled)
- Quick actions:
  - "Optimize Now" (vacuum/analyze)
  - "Backup Now"
  - "Restore from Backup"

**Middle Section – Storage Management**
- **Conversation History**
  - Total conversations count
  - Oldest conversation date
  - "Archive Old Conversations" (with date picker)
  - "Export Conversations"
- **Memory Systems**
  - Working memory size
  - Semantic memory vector count
  - Knowledge graph node/edge count
  - "Prune Old Memories" (with retention policy)
- **Logs & Caches**
  - Log file sizes
  - Cache sizes
  - "Clear Logs Older Than..." (date picker)
  - "Clear All Caches"

**Bottom Section – Update Management**
- Current version display
- "Check for Updates" button
- If updates available:
  - Version comparison
  - Changelog summary
  - "View Full Changelog" link
  - "Update Now" button (with backup reminder)
  - Compatibility warnings if any

### 2.5 Troubleshooting Tab

**Purpose:** Diagnose and fix problems without CLI.

**User Question:** *"Something's not working - how do I fix it?"*

**Layout:**

**Top Section – Connection Tester**
- Test buttons for each component:
  - "Test Backend API"
  - "Test Modelservice"
  - "Test Database"
  - "Test Message Bus"
- Results show:
  - Success/failure with response time
  - Error details if failed
  - Suggested fixes
  - "Run All Tests" button

**Middle Section – Live Log Viewer**
- Real-time log tail with:
  - Service filter (Backend, Modelservice, etc.)
  - Log level filter (ERROR, WARN, INFO, DEBUG)
  - Search/filter box
  - Auto-scroll toggle
  - "Download Logs" button
  - Color-coded log levels
  - Expandable log entries for full details

**Bottom Section – Performance Profiler**
- **Current Bottlenecks**:
  - Slowest endpoints (with response times)
  - Memory-heavy operations
  - Long-running queries
  - Queue backlogs
- **Recent Errors**:
  - Error count by type
  - Most common errors
  - Click to see full stack trace
- "Run Full Diagnostic" button (generates report)

### 2.6 Versions & Compatibility Tab

**Purpose:** Version information and compatibility checking.

**User Question:** *"Are my components compatible?"*

**Layout:**

**Top Section – Component Versions**
- Cards for each component:
  - Backend, Modelservice, Shared Library, Frontend, Studio
  - Current version
  - Build date
  - Status indicator (up-to-date/outdated/incompatible)
  - "View Changelog" link

**Middle Section – Compatibility Matrix**
- Visual grid showing:
  - Component interdependencies
  - Version requirements
  - Compatibility status (green/yellow/red)
  - Warnings for known issues
- "Check Compatibility" button

**Bottom Section – Schema Information**
- Current database schema version
- Applied migrations list
- Pending migrations (if any)
- "View Migration History" (timeline)
- "Apply Pending Migrations" button (with backup warning)

## 3. Visual Design Principles

### 3.1 Status Indicators

**Color System:**
- 🟢 **Green**: Healthy, optimal performance
- 🟡 **Yellow**: Warning, degraded but functional
- 🔴 **Red**: Critical, requires immediate attention
- ⚪ **Gray**: Inactive or disabled

**Visual Hierarchy:**
- Large, prominent overall health indicator
- Service-level status in medium cards
- Metric-level details in small badges

### 3.2 Action Buttons

**Primary Actions** (high contrast, prominent):
- Fix critical issues
- Apply changes
- Run diagnostics

**Secondary Actions** (medium contrast):
- View details
- Configure settings
- Export/import

**Destructive Actions** (red, with confirmation):
- Delete/remove
- Reset to defaults
- Restart services

### 3.3 Progressive Disclosure

- **Level 1**: Status at a glance (colors, icons, key metrics)
- **Level 2**: Click card → drawer with details and actions
- **Level 3**: "Advanced" toggle reveals technical details (raw configs, stack traces)

### 3.4 Feedback & Confirmation

- **Loading States**: Skeleton loaders, progress indicators
- **Success**: Green checkmark with confirmation message (auto-dismiss)
- **Errors**: Red alert with clear explanation and suggested fix
- **Confirmations**: Modal for destructive actions with impact preview

## 4. User Experience Flows

### 4.1 "Something's Broken" Flow

1. User opens System → Health tab
2. Sees red status indicator on specific service
3. Clicks service card → drawer opens
4. Sees error description in plain language
5. Sees "Suggested Fix" with action button
6. Clicks button → system attempts fix
7. Shows progress → success/failure feedback
8. If failed, shows "Try Manual Fix" link to docs

### 4.2 "Change a Setting" Flow

1. User opens System → Configuration tab
2. Browses categories or uses search
3. Finds setting with visual control
4. Adjusts value → sees live validation
5. Clicks "Save Changes"
6. Sees preview of what will change
7. Confirms → system applies changes
8. Shows success message with "Restart Required" if needed

### 4.3 "Free Up Space" Flow

1. User opens System → Maintenance tab
2. Sees disk usage warning
3. Clicks "Storage Management"
4. Sees breakdown of what's using space
5. Selects items to clean up (old logs, archived conversations)
6. Clicks "Clean Up"
7. Sees progress → freed space amount
8. Updated disk usage gauge

## 5. Technical Implementation Notes

### 5.1 Backend API Requirements

**Health Endpoints:**
- `GET /api/v1/system/health` - Overall health status
- `GET /api/v1/system/health/services` - Per-service health
- `POST /api/v1/system/health/check` - Run full diagnostic

**Configuration Endpoints:**
- `GET /api/v1/system/config` - Current configuration
- `GET /api/v1/system/config/schema` - Config schema for validation
- `PUT /api/v1/system/config` - Update configuration
- `GET /api/v1/system/config/presets` - Available presets

**Resource Endpoints:**
- `GET /api/v1/system/resources` - CPU/memory/disk usage
- `GET /api/v1/system/models` - Loaded models
- `POST /api/v1/system/models/{model_id}/unload` - Unload model

**Maintenance Endpoints:**
- `POST /api/v1/system/database/vacuum` - Optimize database
- `POST /api/v1/system/database/backup` - Create backup
- `GET /api/v1/system/storage/stats` - Storage breakdown
- `POST /api/v1/system/cleanup` - Run cleanup tasks

**Troubleshooting Endpoints:**
- `GET /api/v1/system/logs` - Stream logs (SSE)
- `POST /api/v1/system/test/connection` - Test connections
- `GET /api/v1/system/diagnostics` - Generate diagnostic report

### 5.2 Real-Time Updates

- Use WebSocket or SSE for:
  - Live health status updates
  - Log streaming
  - Resource usage monitoring
  - Progress indicators for long operations

### 5.3 Security Considerations

- All system operations require admin authentication
- Destructive actions require confirmation + reason logging
- Configuration changes are audited
- Sensitive values (passwords, keys) are masked in UI
- Export/import validates file integrity

## 6. Navigation & Traceability

- From System you can:
  - Jump to specific docs for subsystems
  - Cross-link to Operations (for service management)
  - Cross-link to Security (for key/encryption changes)
  - View detailed logs in Troubleshooting tab

## 7. Accessibility & Usability

- **Keyboard Navigation**: All actions accessible via keyboard
- **Screen Reader Support**: Proper ARIA labels for status indicators
- **Color Blind Friendly**: Icons + text, not just color for status
- **Mobile Responsive**: Key health info visible on small screens
- **Help Text**: Every setting has contextual help
- **Search**: Quick search across all settings and actions
