# Legacy Native Process Architecture - Cleanup Audit

**Date**: 2026-03-01  
**Status**: Phase 1 - Audit Complete

## Executive Summary

The AICO system has successfully migrated to a Docker-first architecture with NATS, PostgreSQL, and service separation (gateway/core/modelservice). However, the CLI still contains extensive native process management code that assumes services run as Python processes on the host machine. This creates confusion and maintenance burden.

## Audit Findings

### 1. Native Process Management in CLI

#### `cli/commands/gateway.py` (1284 lines)
**Native Process Code:**
- Lines 68-115: `_is_gateway_running()` - PID file + HTTP health check
- Lines 188-440: `start()` command - Full native process spawning with:
  - UV/pip dependency management
  - subprocess.Popen with platform-specific detach logic
  - Windows pythonw.exe handling
  - Foreground/background mode switching
- Lines 443-488: `stop()` command - ProcessManager-based shutdown
- Lines 491-498: `restart()` command - Stop + start orchestration

**Dependencies:**
- `aico.core.process.ProcessManager` (PID-based process tracking)
- `psutil` for process scanning
- Platform-specific subprocess flags (DETACHED_PROCESS, CREATE_NEW_PROCESS_GROUP)

#### `cli/commands/modelservice.py` (674 lines)
**Native Process Code:**
- Lines 44-88: `_is_modelservice_running()` - Message bus health + process scanning fallback
- Lines 229-350: `start()` command - Native process spawning similar to gateway
- Lines 353-400: `stop()` command - ProcessManager-based shutdown
- Lines 403-420: `restart()` command - Stop + start orchestration

**Dependencies:**
- Same ProcessManager and psutil dependencies
- NATS health check as primary detection (good!)
- Process scanning as fallback (legacy)

### 2. ProcessManager Class

#### `shared/aico/core/process.py`
**Functionality:**
- PID file management (`~/.aico/pids/`)
- Cross-platform process lifecycle (start/stop/status)
- Graceful shutdown with timeout
- Stale process cleanup via psutil

**Usage:** Only used by CLI gateway/modelservice commands

### 3. Docker Architecture (Current Reality)

#### `docker/docker-compose.local.yml`
**Services:**
- `aico-gateway` (container: aico-gateway) - Runs `gateway_main.py`
- `aico-core` (container: aico-core) - Runs `core_main.py`
- `aico-modelservice` (container: aico-modelservice) - Runs modelservice
- `aico-nats` - NATS + JetStream
- `aico-postgres` - PostgreSQL 18

**Container Management:**
- Docker Compose handles lifecycle
- Health checks via Docker
- Logs via `docker logs`
- No PID files, no native processes

### 4. Conflict Analysis

| Aspect | Native CLI Assumes | Docker Reality |
|--------|-------------------|----------------|
| Process Model | Python processes on host | Containers managed by Docker |
| Start/Stop | subprocess.Popen + PID files | docker-compose up/down |
| Status Check | PID file + psutil scan | Docker container status |
| Logs | File-based or stdout capture | docker logs |
| Dependencies | UV/pip install on host | Pre-built in container images |
| Configuration | Host filesystem paths | Container-mounted volumes |

## Impact Assessment

### User Confusion
- Two ways to start services: `aico gateway start` vs `docker-compose up`
- Unclear which method to use
- CLI commands fail when services run in Docker
- No clear migration path documented

### Maintenance Burden
- Dual codepaths for same functionality
- Platform-specific process management complexity
- ProcessManager class only used by deprecated commands
- Testing requires both native and Docker scenarios

### Technical Debt
- 1000+ lines of native process code to maintain
- psutil dependency only for legacy process scanning
- PID file management infrastructure unused in Docker
- Subprocess platform-specific flags for Windows/Unix

## Recommendations

### Phase 1: Remove Native Process Management (2-3 weeks)

#### Step 1.1: Deprecate Commands (Week 1)
- Add deprecation warnings to `aico gateway start/stop/restart`
- Add deprecation warnings to `aico modelservice start/stop/restart`
- Point users to `aico deploy` instead
- Document migration in CLI help text

#### Step 1.2: Create Docker-Aware Commands (Week 1-2)
- Implement `aico ps` - List running containers
- Implement `aico logs <service>` - Wrapper for docker logs
- Implement `aico exec <service> <command>` - Wrapper for docker exec
- Update `aico gateway status` to check Docker containers
- Update `aico modelservice status` to check Docker containers

#### Step 1.3: Remove Native Code (Week 2-3)
- Remove `start()`, `stop()`, `restart()` from gateway.py
- Remove `start()`, `stop()`, `restart()` from modelservice.py
- Remove `shared/aico/core/process.py` (ProcessManager)
- Remove psutil dependency from CLI
- Clean up PID file directories

#### Step 1.4: Update Documentation (Week 3)
- Update README with Docker-first approach
- Create migration guide for users on native processes
- Update CLI help text and examples
- Add troubleshooting for Docker-specific issues

### Files to Modify

**Remove:**
- `cli/commands/gateway.py` - Lines 188-498 (start/stop/restart commands)
- `cli/commands/modelservice.py` - Lines 229-420 (start/stop/restart commands)
- `shared/aico/core/process.py` - Entire file (ProcessManager class)

**Create:**
- `cli/commands/ps.py` - Docker container listing
- `cli/commands/exec.py` - Docker exec wrapper
- `cli/utils/docker_client.py` - Docker API wrapper utilities

**Modify:**
- `cli/commands/gateway.py` - Update `status()` to check Docker
- `cli/commands/modelservice.py` - Update `status()` to check Docker
- `cli/commands/logs.py` - Add Docker logs integration
- `cli/commands/deploy.py` - Enhance with up/down/restart subcommands

### Dependencies

**Add:**
- `docker` Python package (official Docker SDK)

**Remove:**
- `psutil` (only used for native process scanning)

## Success Criteria

- [ ] All native process start/stop commands removed
- [ ] Docker-aware status commands implemented
- [ ] `aico ps` command shows running containers
- [ ] `aico logs <service>` streams container logs
- [ ] ProcessManager class removed
- [ ] psutil dependency removed from CLI
- [ ] Documentation updated with Docker-first approach
- [ ] Migration guide published
- [ ] No PID files created during normal operation

## Risk Mitigation

**Risk:** Users on native processes can't upgrade  
**Mitigation:** Provide clear migration guide, deprecation period with warnings

**Risk:** Docker not installed on user systems  
**Mitigation:** `aico deploy` checks for Docker and provides installation instructions

**Risk:** Breaking existing workflows  
**Mitigation:** Deprecation warnings for 1-2 releases before removal

## Timeline

- **Week 1**: Deprecation warnings + Docker-aware status
- **Week 2**: New Docker commands (ps, logs, exec)
- **Week 3**: Remove native code + documentation
- **Week 4**: Testing + migration guide

## Next Steps

1. Add deprecation warnings to existing commands
2. Implement Docker detection in CLI
3. Create `aico ps` command
4. Update status commands to check containers
5. Remove native process code
6. Update documentation
