# Plugin System Architecture

## Overview ✅

The Plugin System provides a standardized architecture for extending AICO backend functionality through modular components. It uses a service container pattern with lifecycle management, dependency injection, and priority-based startup ordering.

**Current Implementation**: Backend-focused plugin system for API Gateway extensibility, not a general third-party plugin marketplace.

## Core Architecture ✅

### BasePlugin System

**Plugin Base Classes**:
- `BasePlugin`: Abstract base with lifecycle methods (`initialize()`, `start()`, `stop()`)
- `InfrastructurePlugin`: For core services (message bus, logging)
- `SecurityPlugin`: For security components (encryption, auth)
- `MiddlewarePlugin`: For request/response processing

**Priority System**:
- Infrastructure: 10 (started first)
- Security: 20
- Middleware: 30
- Business: 40 (started last)

**Configuration**:
- Plugin settings in `core.yaml` under `core.api_gateway.plugins.{name}`
- Enable/disable via `enabled: true/false`
- Plugin-specific configuration sections

### Current Components ✅

**ServiceContainer**:
- Manages plugin registration and dependency injection
- Handles service lifecycle states (INITIALIZING → INITIALIZED → STARTING → RUNNING)
- Provides shared services (database, config, message bus)

**PluginRegistry**:
- Registers plugin classes for factory creation
- Validates plugin inheritance from `BasePlugin`
- Creates factory functions for service container

**BackendLifecycleManager**:
- Orchestrates plugin startup/shutdown in priority order
- Manages FastAPI application lifecycle
- Coordinates graceful shutdown with signal handling

### Message Bus Integration ✅

**Current Implementation**:
- Plugins access message bus via `ServiceContainer.require_service('message_bus')`
- No topic access control or sandboxing implemented
- Plugins can publish/subscribe to any topics
- Direct access to `MessageBusClient` for ZeroMQ communication

**Active Plugins Using Message Bus**:
- **Message Bus Plugin**: Starts ZeroMQ broker (ports 5555/5556)
- **Log Consumer Plugin**: Subscribes to `logs.*` topics
- **Conversation plugins**: Publish to conversation topics (planned)

## Plugin Lifecycle ✅

### Startup Sequence
1. **Registration**: Plugin classes registered in `PluginRegistry`
2. **Factory Creation**: Service container creates plugin instances
3. **Dependency Injection**: Required services injected via container
4. **Priority Ordering**: Plugins started by priority (Infrastructure → Security → Middleware → Business)
5. **Initialization**: `initialize()` called with error handling
6. **Startup**: `start()` called to begin active operations

### Shutdown Sequence
1. **Signal Handling**: SIGTERM/SIGINT triggers graceful shutdown
2. **Plugin Stopping**: `stop()` called on all plugins in reverse priority order
3. **Resource Cleanup**: Database connections, ZMQ sockets closed
4. **Process Exit**: Clean exit with code 0

### Error Handling
- Plugin failures logged but don't stop other plugins
- State tracking via `ServiceState` enum
- Graceful degradation when plugins fail

### Implemented Plugins 

**Core Infrastructure**:
- **message_bus**: ZeroMQ broker for internal communication
- **log_consumer**: Log persistence to encrypted database
- **encryption**: Request/response encryption middleware
- **security**: Authentication and authorization

**API Gateway Middleware**:
- **rate_limiting**: Request throttling and abuse prevention  
- **validation**: Input validation and sanitization
- **routing**: Message routing and correlation

**Location**: `/backend/api_gateway/plugins/`
**Total**: 7 implemented plugins

### Business Plugins
- **Conversation Engine Plugin**: AI conversation processing (planned)
- **Scheduler Plugin**: Task scheduling integration (planned)

## Security Model ✅

### Current Implementation

**Configuration-Based Security**:
- Plugin enable/disable via configuration
- No runtime permission system
- No sandboxing or isolation

**Service Container Access Control**:
- Plugins access services via dependency injection
- Shared database connection with full access
- Direct message bus access

**Planned Enhancements** 🚧:
- Plugin permission system
- Resource usage monitoring
- API access controls
- Audit logging of plugin actions

## Plugin Development ✅

### Creating a Backend Plugin

```python
from backend.core.plugin_base import BasePlugin, PluginMetadata, PluginPriority
from backend.core.service_container import ServiceContainer

class MyPlugin(BasePlugin):
    def __init__(self, name: str, container: ServiceContainer):
        super().__init__(name, container)
        
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="My Plugin",
            version="1.0.0", 
            description="Example plugin",
            priority=PluginPriority.BUSINESS
        )
        
    async def initialize(self) -> None:
        """Initialize plugin resources"""
        self.database = self.require_service('database')
        self.message_bus = self.require_service('message_bus')
        
    async def start(self) -> None:
        """Start plugin operations"""
        await self.message_bus.connect()
        
    async def stop(self) -> None:
        """Stop plugin operations"""
        await self.message_bus.disconnect()
```

### Development Workflow

1. **Create Plugin Class**: Inherit from appropriate base class
2. **Implement Lifecycle**: Define `initialize()`, `start()`, `stop()` methods
3. **Register Plugin**: Add to plugin registry in lifecycle manager
4. **Configure**: Add plugin settings to `core.yaml`
5. **Test**: Use backend development environment
6. **Deploy**: Plugin loaded automatically on backend startup

### Plugin File Structure

```
backend/api_gateway/plugins/
├── message_bus_plugin.py      # Infrastructure plugin
├── encryption_plugin.py       # Security plugin  
├── log_consumer_plugin.py     # Infrastructure plugin
├── rate_limiting_plugin.py    # Middleware plugin
└── validation_plugin.py       # Middleware plugin
```

**Configuration in `core.yaml`**:
```yaml
core:
  api_gateway:
    plugins:
      message_bus:
        enabled: true
      encryption:
        enabled: true
```

### Plugin Registration

**In `BackendLifecycleManager`**:
```python
# Register plugin classes
registry = get_plugin_registry()
registry.register_plugin_class("message_bus", MessageBusPlugin)
registry.register_plugin_class("encryption", EncryptionPlugin)
registry.register_plugin_class("log_consumer", LogConsumerPlugin)

# Register with service container
container.register_service(
    "message_bus_plugin",
    registry.create_plugin_factory("message_bus")
)
```

**Plugin Metadata via `@property`**:
```python
@property
def metadata(self) -> PluginMetadata:
    return PluginMetadata(
        name="Message Bus Plugin",
        version="1.0.0",
        description="ZeroMQ message bus management", 
        priority=PluginPriority.INFRASTRUCTURE
    )
```

## Technical Implementation ✅

### Current Technology Stack

**Plugin Runtime**:
- Python-based plugins within backend process
- No isolation or sandboxing
- Shared memory space and resources

**Communication**:
- Direct method calls within process
- ZeroMQ message bus for inter-service communication
- Protocol Buffers for message serialization
- Shared database connection

**Storage**:
- Shared access to encrypted libSQL database
- Configuration via YAML files
- No plugin-specific storage isolation

## Plugin Management 

### Current State

**No User Interface**:
- Plugins managed via configuration files only
- No runtime enable/disable capability
- No plugin marketplace or discovery
- Backend-only plugin system

**Configuration Management**:
- Plugin settings in `core.yaml`
- Requires backend restart to change plugin state
- No dynamic plugin loading/unloading

### Planned Features

**Admin Interface**:
- Plugin status monitoring via `/api/v1/admin/` endpoints
- Configuration management through web interface
- Plugin health checks and diagnostics

**Future Enhancements**:
- Dynamic plugin loading without restart
- Plugin marketplace integration
- Frontend plugin system for UI extensions

## Health Monitoring 

### Plugin Health Checks

**Built-in Health Reporting**:
```python
async def health_check(self) -> Dict[str, Any]:
    return {
        "status": "healthy",
        "state": self.state.value,
        "metadata": {
            "version": self.metadata.version,
            "priority": self.metadata.priority.value
        },
        "enabled": self.enabled,
        "configuration": {
            "has_config": bool(self.plugin_config)
        }
    }
```

**Service Container Health**:
- Tracks service states (INITIALIZING → RUNNING → ERROR)
- Provides health status for all registered services
- Includes plugin-specific health information

**Monitoring Integration**:
- Health data available via admin endpoints
- Plugin failures logged with structured data
- Service state transitions tracked

## Summary 

The AICO Plugin System provides a **backend-focused, configuration-driven architecture** for extending API Gateway functionality. It emphasizes:

- **Simplicity**: Clear lifecycle management and dependency injection
- **Reliability**: Priority-based startup and graceful error handling  
- **Integration**: Seamless message bus and database access
- **Maintainability**: Standardized patterns and structured configuration

**Current Focus**: Infrastructure and security plugins for core backend services, not a general-purpose plugin marketplace.
