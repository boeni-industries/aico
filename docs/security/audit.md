---
title: Audit System Architecture
---

# Security Audit & Monitoring

AICO's security audit system provides comprehensive logging and monitoring of security events across all system components.

**Current Status**: ✅ Core audit logging operational via AICO logging system, advanced threat detection and compliance reporting planned.

## Current Implementation ✅

### Operational Features
- **Centralized Logging**: All security events logged via AICO logging system
- **Message Bus Integration**: Audit events distributed through encrypted ZMQ message bus
- **Database Storage**: Encrypted audit trail stored in libSQL database
- **CLI Access**: `aico logs` command provides audit trail inspection
- **Component Coverage**: Authentication, system operations, and configuration changes logged

### Security Features
- **Encrypted Storage**: All audit data encrypted at rest using AES-256-GCM
- **Structured Logging**: Consistent JSON format with metadata and context
- **Access Control**: Admin-level permissions required for audit access
- **Privacy Protection**: No sensitive user data included in audit records

## Current Audit Coverage

### Authentication Events ✅ Implemented
- **Login Attempts**: Success/failure with user context and IP address
- **Session Management**: JWT token creation, renewal, and expiration
- **Admin Access**: CLI and backend administrative operations
- **Account Security**: Lockout events and security violations

### System Events ✅ Implemented
- **Component Lifecycle**: Service startup, shutdown, and health status
- **Configuration Changes**: Security setting modifications and updates
- **Database Operations**: Encrypted data access patterns and schema changes
- **Message Bus Activity**: Inter-component communication and security events

### Planned Event Types 🚧
- **Access Control**: Authorization decisions and policy violations
- **Data Operations**: File access patterns and encryption operations
- **Plugin Activity**: Third-party plugin security events and permissions
- **Network Security**: Connection attempts, anomalies, and threat detection

## Implementation Examples

### Current Audit Logging
```python
# Authentication event logging
from aico.core.logging import get_logger

logger = get_logger('auth')
logger.info('Authentication successful', extra={
    'user_id': user.id,
    'method': 'jwt_token',
    'ip_address': request.client.host,
    'user_agent': request.headers.get('user-agent'),
    'session_id': session.id
})
```

### System Event Logging
```python
# Component lifecycle logging
logger = get_logger('system')
logger.info('Message bus broker started', extra={
    'component': 'message_bus',
    'ports': [5555, 5556],
    'encryption': 'curve_zmq',
    'startup_time': startup_duration
})
```

### CLI Audit Access
```bash
# View recent authentication events
aico logs tail --filter="auth" --lines=50

# Search for specific events
aico logs search --query="Authentication successful" --since="1h"

# Export audit logs
aico logs export --format=json --output=audit.json
```

## Planned Enhancements 🚧

### Advanced Threat Detection
- **Pattern Analysis**: Real-time detection of suspicious behavior patterns
- **Anomaly Detection**: ML-based identification of unusual access patterns
- **Risk Scoring**: Dynamic risk assessment based on user behavior
- **Automated Response**: Configurable responses to security threats

### Compliance Reporting
- **Audit Reports**: Pre-configured compliance reports for common frameworks
- **Evidence Collection**: Automated gathering of audit evidence
- **Retention Management**: Policy-based audit data retention and archival
- **Export Capabilities**: Secure export of audit data for external review

## Technical Architecture

### Current Integration ✅
- **ZeroMQ Message Bus**: Audit events flow through encrypted message bus
- **LibSQL Storage**: Encrypted audit trail in main database
- **Structured Logging**: JSON format with consistent metadata
- **CLI Interface**: Direct access via `aico logs` commands

### Planned Architecture 🚧
- **Dedicated Audit Collector**: Centralized audit event processing
- **Tamper-Evident Storage**: Hash-chained audit records for integrity
- **Real-Time Monitoring**: Live security event analysis
- **Cross-Component Coverage**: Audit events from all system modules

## Security Features

### Current Security ✅
- **Encrypted Storage**: All audit data encrypted at rest with AES-256-GCM
- **Access Control**: Admin-level permissions required for audit access
- **Structured Format**: Consistent JSON logging with metadata
- **Privacy Protection**: No sensitive user data in audit records

### Planned Security Enhancements 🚧
- **Tamper-Evident Storage**: Hash-chained audit records for integrity verification
- **Audit Trail Verification**: Cryptographic validation of audit record integrity
- **Append-Only Storage**: Prevention of audit record modification or deletion
- **Digital Signatures**: Cryptographic signing of critical audit events

## Privacy & Compliance

### Privacy Safeguards ✅
- **Data Minimization**: Only security-relevant information recorded
- **No Personal Data**: Conversation content never included in audit logs
- **Encrypted Storage**: All audit data encrypted at rest
- **Access Control**: Admin-level permissions required for audit access

### Planned Privacy Features 🚧
- **Configurable Retention**: Automatic pruning of expired audit records
- **Data Redaction**: Automatic removal of sensitive information
- **Export Controls**: Encrypted audit data export for compliance
- **Legal Hold**: Compliance-driven audit data preservation

## Implementation Components

### 1. Audit API

A simple, consistent API for generating audit events:

```python
# Backend (Python) example
from aico.audit import audit_event

def change_user_role(user_id, new_role):
    # Perform the role change
    result = user_service.update_role(user_id, new_role)
    
    # Audit the action
    audit_event(
        category="authorization",
        event_type="role_change",
        outcome="success" if result else "failure",
        subject={"type": "user", "id": current_user.id},
        object={"type": "user", "id": user_id},
        details={"previous_role": user.role, "new_role": new_role}
    )
    
    return result
```

```dart
// Frontend (Flutter) example
import 'package:aico/audit/audit.dart';

void changeUserSettings(String setting, dynamic value) {
  // Update the setting
  userSettings.update(setting, value);
  
  // Audit the change
  auditEvent(
    category: "user_settings",
    eventType: "setting_change",
    outcome: "success",
    object: {"type": "setting", "id": setting},
    details: {"previous_value": previousValue, "new_value": value}
  );
}
```

### 2. Audit Collector Service

The central service responsible for collecting, validating, and storing audit events:

```python
class AuditCollector:
    def __init__(self):
        # Set up ZeroMQ subscription
        self.zmq_context = zmq.Context()
        self.socket = self.zmq_context.socket(zmq.SUB)
        self.socket.connect("tcp://localhost:5555")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "audit.")
        
        # Initialize the store using the existing libSQL database
        self.store = AuditStore()
    
    def start(self):
        while True:
            topic, message = self.socket.recv_multipart()
            audit_record = json.loads(message)
            
            # Store with integrity verification
            self.store.append(audit_record)
            
            # Check for alertable conditions
            if audit_record.get("severity") == "critical":
                self.trigger_alert(audit_record)
```

### 3. Audit Store

A store that leverages libSQL with hash chaining for integrity verification:

```python
class AuditStore:
    def __init__(self):
        # Reuse the existing libSQL database
        self.db = libsql.connect("aico.db")
        self.initialize_schema()
    
    def initialize_schema(self):
        self.db.execute("""
        CREATE TABLE IF NOT EXISTS audit_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            category TEXT NOT NULL,
            event_type TEXT NOT NULL,
            data JSON NOT NULL,
            hash TEXT NOT NULL,
            previous_hash TEXT
        )
        """)
    
    def append(self, record):
        # Add integrity metadata
        record['metadata'] = {
            'previous_hash': self.last_hash,
            'sequence_number': self.get_next_sequence(),
        }
        
        # Calculate record hash
        record_json = json.dumps(record, sort_keys=True)
        record_hash = hashlib.sha256(record_json.encode()).hexdigest()
        record['metadata']['record_hash'] = record_hash
        
        # Store the record
        self.db.execute(
            "INSERT INTO audit_records VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (None, record['audit_id'], record['timestamp'], record['category'],
             record['event_type'], json.dumps(record), record_hash,
             record['metadata']['previous_hash'], record['metadata']['sequence_number'])
        )
        
        # Update last hash
        self.last_hash = record_hash
        
        return record_hash
```

### 4. Audit Query API

A secure API for searching and retrieving audit records:

```python
class AuditQuery:
    def __init__(self, store):
        self.store = store
    
    def search(self, filters, start_time=None, end_time=None, limit=100, offset=0):
        # Build query based on filters
        query = "SELECT * FROM audit_records WHERE 1=1"
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        if 'category' in filters:
            query += " AND category = ?"
            params.append(filters['category'])
        
        # Add more filters as needed
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Execute query
        results = self.store.db.execute(query, params).fetchall()
        
        # Process and return results
        return [json.loads(row['record_data']) for row in results]
    
    def get_record_by_id(self, audit_id):
        result = self.store.db.execute(
            "SELECT record_data FROM audit_records WHERE audit_id = ?",
            (audit_id,)
        ).fetchone()
        
        if result:
            return json.loads(result['record_data'])
        return None
```

### 5. Admin Interface

The Audit System provides both CLI and UI interfaces for authorized administrators:

#### CLI Commands

```bash
# Search audit logs
aico-cli audit search --category=authentication --start="2025-08-01" --limit=50

# Export audit logs
aico-cli audit export --start="2025-08-01" --end="2025-08-04" --format=json --output=audit.json

# Verify audit chain integrity
aico-cli audit verify-chain

# View audit statistics
aico-cli audit stats --period=30d
```

#### Admin UI Dashboard

The Admin UI provides:
- Interactive audit log search and filtering
- Visual timeline of security events
- Pattern analysis and anomaly detection
- Compliance reporting templates
- Audit health monitoring

## Deployment Patterns

### Coupled Mode (Single Device)

In coupled mode, where frontend and backend run on the same device:

- Audit events flow directly through the local message bus
- All audit storage is on the local device
- Verification and queries operate on the local audit store
- No network transmission of audit data

### Detached Mode (Multi-Device)

In detached mode, where frontend and backend are on separate devices:

- Frontend audit events are sent to backend via secure channel
- Backend maintains the authoritative audit store
- Frontend maintains minimal local audit cache for offline operation
- Synchronization occurs when connection is established
- Integrity verification spans both components

### Federation Considerations

When multiple AICO instances are federated:

- Each instance maintains its own audit store
- Cross-instance actions include federation context
- Audit records can be correlated across instances via trace IDs
- Federation audit events capture synchronization activities

## Security Monitoring & Alerting

The Audit System supports real-time security monitoring:

### 1. Alert Rules

Configurable rules trigger alerts based on audit patterns:

```yaml
alerts:
  - name: "Multiple Authentication Failures"
    condition:
      category: "authentication"
      event_type: "login_attempt"
      outcome: "failure"
      count: 5
      window: "5m"
    actions:
      - "notify_admin"
      - "increase_security"
  
  - name: "Sensitive Data Access"
    condition:
      category: "data"
      object.path: "/data/personal/*"
    actions:
      - "log_access"
      - "notify_user"
```

### 2. Response Actions

Automated responses to security events:

- Temporary account lockout after multiple failures
- Notification to administrators for critical events
- Increased logging verbosity during suspicious activity
- Security posture adjustments based on threat level

### 3. Correlation Engine

Pattern detection across multiple audit events:

```python
def detect_patterns(recent_events):
    # Check for brute force pattern
    login_failures = [e for e in recent_events 
                     if e['category'] == 'authentication' and e['outcome'] == 'failure']
    
    if len(login_failures) >= 5:
        # Group by source IP
        by_ip = group_by(login_failures, lambda e: e['context']['ip_address'])
        
        for ip, events in by_ip.items():
            if len(events) >= 3:
                trigger_alert("possible_brute_force", {
                    "ip_address": ip,
                    "attempt_count": len(events),
                    "target_accounts": list(set(e['object']['id'] for e in events))
                })
```

## Compliance & Reporting

The Audit System supports compliance requirements through:

### 1. Compliance Reports

Pre-configured reports for common compliance frameworks:

- Access control effectiveness
- Authentication activity
- Data access patterns
- Configuration changes
- Security incident timeline

### 2. Evidence Collection

Automated evidence gathering for audits:

```python
def generate_compliance_evidence(framework, period_start, period_end):
    evidence = {}
    
    # Collect authentication evidence
    evidence['authentication'] = {
        'total_logins': count_events('authentication', 'login_attempt', 'success', period_start, period_end),
        'failed_logins': count_events('authentication', 'login_attempt', 'failure', period_start, period_end),
        'password_changes': count_events('authentication', 'password_change', None, period_start, period_end),
        'mfa_usage': calculate_mfa_percentage(period_start, period_end)
    }
    
    # Collect access control evidence
    evidence['access_control'] = {
        'permission_changes': list_events('authorization', 'permission_change', None, period_start, period_end),
        'role_changes': list_events('authorization', 'role_change', None, period_start, period_end),
        'access_denials': count_events('authorization', 'access_attempt', 'denied', period_start, period_end)
    }
    
    # More evidence types...
    
    return evidence
```

### 3. Retention Compliance

Automated enforcement of retention policies:

```python
def enforce_retention_policy():
    # Get retention period from config
    retention_days = config.get('audit.retention_days', 90)
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    # Check for legal hold
    if not is_legal_hold_active():
        # Delete or archive expired records
        if config.get('audit.archive_expired', False):
            archive_records_before(cutoff_date)
        else:
            delete_records_before(cutoff_date)
```

## Best Practices

### 1. When to Audit

Audit events should be generated for:

- All authentication and authorization decisions
- Access to sensitive data or functions
- Configuration and security policy changes
- User consent grants and withdrawals
- Security-relevant system operations
- Plugin installation, activation, and permissions

### 2. Audit Detail Level

Balance between security needs and privacy:

- **High Detail:** Security operations, authentication, authorization
- **Medium Detail:** System configuration, plugin activity, data access patterns
- **Low Detail:** User interactions, feature usage (metadata only)
- **No Auditing:** Conversation content, personal data, emotional state

### 3. Implementation Guidelines

For developers implementing audit hooks:

- Use the audit API consistently across all modules
- Include all required fields in every audit event
- Never log sensitive data in audit records
- Ensure audit calls don't block main execution path
- Test audit coverage as part of security review

### 4. Operational Recommendations

For system administrators:

- Regularly review audit logs for anomalies
- Test the integrity verification process periodically
- Configure appropriate retention periods
- Establish clear procedures for audit review
- Document all custom alert rules and responses

## Conclusion

The AICO Audit System provides comprehensive visibility into system operations while respecting user privacy and maintaining system performance. By capturing security-relevant events across all components, it enables effective monitoring, compliance, and incident response while upholding AICO's core principles of privacy-first design and local-first processing.

The tamper-evident storage ensures the integrity of audit records, while the flexible query capabilities support both automated monitoring and manual investigation. Together with AICO's broader security architecture, the Audit System forms a critical component of the platform's defense-in-depth strategy.

## References

- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [NIST SP 800-92: Guide to Computer Security Log Management](https://csrc.nist.gov/publications/detail/sp/800-92/final)
- [AICO Security Architecture](./data-security.md)
- AICO Access Control (file does not exist)
- [AICO Instrumentation](../operations/instrumentation/instrumentation.md)
- [AICO Instrumentation Logging](../operations/instrumentation/instrumentation-logging.md)
