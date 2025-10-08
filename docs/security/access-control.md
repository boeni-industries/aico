# Access Control Architecture

## Overview

AICO implements comprehensive access control across all system components using modern security patterns. The architecture supports fine-grained permissions while maintaining simplicity and performance.

**Current Status**: 🚧 Planned implementation - core authentication infrastructure exists, full access control system in development.

---

## Core Principles
- **Principle of Least Privilege:** Every user, module, and plugin is granted only the minimum permissions required for its function.
- **Deny by Default:** All access is denied unless explicitly permitted by policy.
- **Centralized Policy Management:** Policies are defined and managed centrally, with distributed enforcement.
- **Defense in Depth:** Authorization is enforced at multiple layers (API gateway, message bus, module, plugin sandbox).
- **Testability & Auditability:** Policies are testable, versioned, and all access decisions are logged for audit.

---

## Access Control Models

**Primary Model**: Role-Based Access Control (RBAC) with planned ABAC extensions

- **RBAC**: System-wide roles (user, admin, plugin) ✅ Implemented
- **ABAC**: Context-aware decisions (device, time, location) 🚧 Planned
- **ReBAC**: Resource ownership patterns 🚧 Planned

---

## Architecture & Enforcement

### Current Implementation
- **API Gateway**: JWT-based authentication ✅ Operational
- **Session Management**: Token validation and renewal ✅ Operational  
- **Admin Access**: CLI and backend admin endpoints ✅ Operational

### Planned Components
- **Policy Decision Point (PDP)**: Centralized policy evaluation
- **Message Bus Access Control**: Topic-level permissions
- **Plugin Sandbox**: Isolated plugin execution environment
- **Resource-Level Permissions**: Fine-grained data access controls

---

## Implementation Principles

- **Server-Side Enforcement**: All security decisions made on backend ✅ Implemented
- **Comprehensive Logging**: Access decisions logged for audit ✅ Implemented  
- **Deny by Default**: No access without explicit permission ✅ Implemented
- **Centralized Policy Management**: Single source of truth for permissions 🚧 Planned

---

## Policy Evolution & Testing
- **Versioned Policies:** All changes are tracked, reviewed, and testable.
- **Automated Testing:** Unit and integration tests for all access control logic.
- **Audit Trails:** Complete logs for policy changes and access decisions.

---

## Current Use Cases

- **Admin Authentication**: CLI and backend admin operations require valid JWT tokens
- **API Access Control**: All REST endpoints protected by authentication middleware
- **Session Management**: Time-limited sessions with automatic renewal

## Planned Use Cases

- **Plugin Permissions**: Granular access control for third-party plugins
- **Data-Level Security**: Row and column-level access controls
- **Context-Aware Access**: Time, location, and device-based restrictions

---

## Implementation Examples

### Current Authentication Flow
```python
# JWT token validation in API Gateway
from aico.security.auth import AuthenticationManager

auth_manager = AuthenticationManager()
token_valid = auth_manager.validate_jwt_token(request.headers.get('Authorization'))
if not token_valid:
    raise HTTPException(status_code=401, detail="Authentication required")
```

### Planned Access Control
```python
# Future ABAC policy evaluation
from aico.security.access_control import PolicyDecisionPoint

pdp = PolicyDecisionPoint()
decision = pdp.evaluate(
    subject={'user_id': user.id, 'role': user.role},
    resource={'type': 'conversation', 'owner': conversation.owner_id},
    action='read',
    context={'time': datetime.now(), 'device': request.device_id}
)
if decision != 'PERMIT':
    raise HTTPException(status_code=403, detail="Access denied")
```

---

## Example Use Cases
- A plugin can only access message bus topics and APIs for which it is explicitly permitted, based on its manifest and user-granted permissions.
- A user’s ability to view, edit, or delete data is determined by a combination of their role, attributes (device, time, context), and resource ownership.
- The API gateway denies all requests by default unless a valid, signed token and matching policy are present.

---

## References
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP Microservices Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Microservices_Security_Cheat_Sheet.html)
- [NIST SP 800-162: ABAC Guide](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-162.pdf)
