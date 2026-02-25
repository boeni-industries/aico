# Credential Management for Containerized Environments

## Problem Statement

The current AICO credential management system relies heavily on macOS Keychain (via Python `keyring` library), which causes **blocking issues** in containerized and non-interactive environments.

### Symptoms

1. **CLI commands hang** waiting for keyring access
2. **Docker containers fail to start** due to keyring prompts
3. **CI/CD pipelines block** on credential access
4. **IDE tool runners hang** in non-interactive contexts

### Root Causes

#### 1. ConfigurationManager Initialization Chain
```
ConfigurationManager.initialize()
  → _load_runtime_configs()
    → _get_runtime_config_file()
      → AICOPaths.get_data_directory()
        → Requires encryption key
          → AICOKeyManager.authenticate()
            → keyring.get_password() ← BLOCKS HERE (macOS password prompt)
```

**Impact**: Almost every CLI command initializes `ConfigurationManager`, triggering potential keyring access.

#### 2. Direct Keyring Access Points

**47 CLI commands** use `AICOKeyManager` directly:
- Database operations (`kg`, `scheduler`, `pg`)
- Security commands (`security passwd`, `security setup`)
- Infrastructure deployment (`deploy pg`, `deploy influx`)
- Service authentication (`gateway auth`, `bus`)

Each `keyring.get_password()` or `keyring.set_password()` call can trigger macOS Keychain authentication dialog.

#### 3. Container Environment Incompatibility

**Why keyring doesn't work in containers:**
- No TTY: `sys.stdin.isatty()` returns `False`
- No macOS Keychain: Linux containers can't access host keyring
- No user interaction: Docker services, systemd, cron jobs are non-interactive
- Security isolation: Containers shouldn't access host keyring for security reasons

## Solution: Environment-Aware Credential Provider

### Design Principles

1. **Non-blocking by default** - Never hang waiting for user input
2. **Environment-aware** - Detect container/CI/local dev contexts
3. **Secure fallback chain** - Multiple credential sources with clear priority
4. **Backward compatible** - Existing local dev workflows still work
5. **Container-first** - Optimized for Docker/Kubernetes deployments

### Credential Resolution Priority

```
1. Environment Variables (AICO_<KEY_NAME>)        ← Highest priority
   - Perfect for containers, CI/CD
   - Easy to inject via docker-compose, K8s ConfigMaps
   - No persistence, regenerated on restart

2. Docker/Kubernetes Secrets (/run/secrets/<key>)
   - Secure secret management
   - Mounted as files in containers
   - Encrypted at rest, access-controlled

3. Encrypted Local File (~/.aico/secrets.enc)
   - For persistent containers
   - Encrypted with master key from env var
   - Survives container restarts

4. System Keyring (macOS Keychain, etc.)         ← Lowest priority
   - Local development only
   - Interactive mode only
   - Never accessed in containers/CI
```

### Implementation

Created `CredentialProvider` class in `/shared/aico/security/credential_provider.py`:

```python
from aico.security.credential_provider import CredentialProvider

# Initialize provider
provider = CredentialProvider(service_name="AICO")

# Get credential (non-blocking)
password = provider.get("postgres_password")

# Get required credential (raises error if not found)
jwt_secret = provider.get("jwt_secret", required=True)

# Check availability without retrieving
if provider.is_available("influx_token"):
    token = provider.get("influx_token")

# Get source information (debugging)
info = provider.get_source_info("postgres_password")
# Returns: {"source": "environment", "env_var_set": True, ...}
```

### Migration Strategy

#### Phase 1: Immediate Fixes (Completed)

1. ✅ Created `CredentialProvider` with non-blocking fallback chain
2. ✅ Fixed `deploy studio` to bypass `ConfigurationManager` keyring access
3. ✅ Added environment variable fallbacks to deployment commands

#### Phase 2: Gradual Migration (Next)

**Update `AICOKeyManager` to use `CredentialProvider`:**

```python
class AICOKeyManager:
    def __init__(self, config: ConfigurationManager):
        self.credential_provider = CredentialProvider(
            service_name=config.get("security.keyring_service_name", "AICO")
        )
    
    def get_jwt_secret(self, service_name: str = "api_gateway") -> str:
        key_name = f"{service_name}_jwt_secret"
        
        # Try credential provider first (non-blocking)
        if secret := self.credential_provider.get(key_name):
            return secret
        
        # Generate new secret if not found
        import secrets
        secret = secrets.token_urlsafe(32)
        
        # Store in credential provider (only works in interactive mode)
        self.credential_provider.set(key_name, secret)
        
        return secret
```

**Update CLI commands to use environment variables:**

```python
# OLD (blocking):
key_manager = AICOKeyManager(config)
password = key_manager.get_database_password("postgres")

# NEW (non-blocking):
provider = CredentialProvider()
password = provider.get("postgres_password") or \
           key_manager.get_database_password("postgres")  # Fallback
```

#### Phase 3: Container Optimization

**Docker Compose example:**

```yaml
services:
  gateway:
    environment:
      # Credentials via environment variables
      AICO_POSTGRES_PASSWORD: ${AICO_PG_PASSWORD}
      AICO_JWT_SECRET: ${AICO_JWT_SECRET}
      AICO_INFLUX_ADMIN_TOKEN: ${AICO_INFLUX_ADMIN_TOKEN}
      AICO_NONINTERACTIVE: "true"  # Disable keyring access
    secrets:
      # Or via Docker secrets (more secure)
      - postgres_password
      - jwt_secret

secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
  jwt_secret:
    file: ./secrets/jwt_secret.txt
```

**Kubernetes example:**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aico-credentials
type: Opaque
stringData:
  postgres_password: "..."
  jwt_secret: "..."
---
apiVersion: v1
kind: Pod
metadata:
  name: aico-gateway
spec:
  containers:
  - name: gateway
    env:
    - name: AICO_POSTGRES_PASSWORD
      valueFrom:
        secretKeyRef:
          name: aico-credentials
          key: postgres_password
    - name: AICO_JWT_SECRET
      valueFrom:
        secretKeyRef:
          name: aico-credentials
          key: jwt_secret
```

### Environment Variables Reference

| Variable | Description | Used By |
|----------|-------------|---------|
| `AICO_POSTGRES_PASSWORD` | PostgreSQL password | Core, Gateway, CLI |
| `AICO_JWT_SECRET` | JWT signing secret | Gateway |
| `AICO_INFLUX_ADMIN_PASSWORD` | InfluxDB admin password | Deploy commands |
| `AICO_INFLUX_ADMIN_TOKEN` | InfluxDB API token | Telemetry, monitoring |
| `AICO_GRAFANA_PASSWORD` | Grafana admin password | Deploy commands |
| `AICO_MASTER_KEY` | Master encryption key (hex) | All encrypted storage |
| `AICO_NONINTERACTIVE` | Disable keyring access (`true`/`false`) | All CLI commands |

### Benefits

1. **No more hanging scripts** - Credentials resolve immediately or fail fast
2. **Container-native** - Works seamlessly in Docker/Kubernetes
3. **CI/CD friendly** - Easy to inject credentials via environment
4. **Secure by default** - Supports Docker secrets, K8s secrets
5. **Backward compatible** - Local dev with keyring still works
6. **Debuggable** - Clear source information for troubleshooting

### Security Considerations

1. **Environment variables** - Visible in `docker inspect`, process listings
   - Use for non-sensitive config or development only
   - Rotate regularly

2. **Docker secrets** - Encrypted at rest, access-controlled
   - Preferred for production deployments
   - Mounted as tmpfs, not in environment

3. **Kubernetes secrets** - Base64 encoded, RBAC protected
   - Use with encryption at rest enabled
   - Consider external secret managers (Vault, AWS Secrets Manager)

4. **System keyring** - OS-level encryption, user-scoped
   - Best for local development
   - Not suitable for containers/services

### Testing

**Test credential resolution:**

```bash
# Test environment variable
export AICO_POSTGRES_PASSWORD="test123"
python -c "from aico.security.credential_provider import CredentialProvider; \
           p = CredentialProvider(); \
           print(p.get_source_info('postgres_password'))"

# Test Docker secrets
mkdir -p /run/secrets
echo "secret123" > /run/secrets/postgres_password
python -c "from aico.security.credential_provider import CredentialProvider; \
           p = CredentialProvider(); \
           print(p.get('postgres_password'))"

# Test non-interactive mode
export AICO_NONINTERACTIVE=true
python -c "from aico.security.credential_provider import CredentialProvider; \
           p = CredentialProvider(); \
           print(f'Interactive: {p.is_interactive}')"
```

### Troubleshooting

**Command hangs waiting for password:**
- Set `AICO_NONINTERACTIVE=true` to disable keyring access
- Provide credentials via environment variables
- Check if running in container without proper credential injection

**Credential not found:**
```bash
# Check credential sources
python -c "from aico.security.credential_provider import CredentialProvider; \
           import json; \
           p = CredentialProvider(); \
           print(json.dumps(p.get_source_info('postgres_password'), indent=2))"
```

**Keyring access in container:**
- Containers should never access keyring
- Set `AICO_NONINTERACTIVE=true` in container environment
- Use environment variables or Docker secrets instead

## Conclusion

The new `CredentialProvider` solves the keyring blocking issues by:
1. Detecting execution context (interactive vs non-interactive)
2. Providing non-blocking credential resolution
3. Supporting multiple credential sources with clear priority
4. Maintaining backward compatibility with existing workflows

This enables AICO to run seamlessly in containerized environments while preserving the convenience of keyring-based credential management for local development.
