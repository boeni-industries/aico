# Security – Layout & Content Design

## 1. Information Design Concept

The Security section visualizes AICO's **defense posture** across:

- Encryption and key management.
- Transport security and authentication.
- Audit logs and access patterns.

The guiding principle is **"calm security"**:

- Normal operation should feel quiet and reassuring.
- Deviations are clearly highlighted without inducing panic.
- All views are fully traceable from high-level posture to individual events.

## 2. Page Layout

### 2.1 Main Layout

- **Top row – Security posture tiles**
  - Encryption.
  - Transport.
  - Auth.
  - Audit.

- **Middle – Detail panels**
  - Key Management.
  - Authentication & Sessions.
  - Audit Log Explorer.

- **Bottom – Security events timeline**
  - Chronological view of key rotations, failed logins, policy changes.

## 3. Content Design

### 3.1 Posture Tiles

- **Encryption Tile**
  - Current master key age and strength.
  - DB encryption status.

- **Transport Tile**
  - CurveZMQ status.
  - TLS details if applicable.

- **Auth Tile**
  - JWT configuration summary.
  - Active tokens vs. expired.

- **Audit Tile**
  - Log queue health.
  - Recent audit events count.

Each tile is clickable and scrolls/jumps to a deeper section.

### 3.2 Key Management Panel

- **Visuals**
  - Timeline of key generations and rotations.
  - Warning badges for overdue rotation.

- **Functions**
  - Manual rotation trigger.
  - View key metadata (never the key itself).

### 3.3 Authentication & Sessions Panel

- **Visuals**
  - Chart of successful vs failed auth over time.
  - Geography/time-of-day heatmaps where applicable.

- **Functions**
  - Inspect a failed auth event (IP, device, reason).
  - Link to Operations logs for deeper diagnosis.

### 3.4 Audit Log Explorer Panel

- **Visuals**
  - Filterable table of audit entries (actor, action, resource, time).

- **Functions**
  - Filter by user, resource type, time range.
  - Click entry → detail drawer with origin, related logs, and any related goals/actions.

## 4. Navigation & Traceability

- Bidirectional links:
  - From Security to Operations (for infrastructure-related security issues).
  - From other sections back to Security when actions involve security changes.
- Every alert in other pages (e.g., overview anomalies) should have a Security anchor view.

## 5. UX Notes

- Emphasis on calm design: no aggressive colors or animations except where absolutely necessary.
- Clear, human-readable language for all security states.
