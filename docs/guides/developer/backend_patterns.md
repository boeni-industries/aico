# Backend Development Patterns

## Overview

This guide covers current development patterns for AICO's backend service, including plugin development, middleware implementation, and integration with the shared library system.

## Plugin Development

### Plugin Architecture

AICO uses a service container architecture with standardized plugin base classes:

```python
from aico.core.logging_context import create_infrastructure_logger
from backend.core.plugin_base import BasePlugin, PluginMetadata, PluginPriority
from backend.core.service_container import ServiceContainer

class MyPlugin(BasePlugin):
    def __init__(self, name: str, container: ServiceContainer):
        super().__init__(name, container)
        self.logger = create_infrastructure_logger("aico.infrastructure.plugin.my_plugin")
        
    @property
    def metadata(self):
        return PluginMetadata(
            name="My Plugin",
            version="1.0.0",
            description="Example plugin implementation",
            priority=PluginPriority.NORMAL
        )
        
    async def initialize(self) -> None:
        """Initialize plugin with required services."""
        self.config = self.require_service('config')
        self.db_connection = self.require_service('database')
    
    async def start(self) -> None:
        """Start plugin services."""
        self.logger.info("Starting MyPlugin")
        # Plugin startup logic
    
    async def stop(self) -> None:
        """Stop plugin services."""
        self.logger.info("Stopping MyPlugin")
        # Plugin cleanup logic
```

### Plugin Registration

Plugins are registered with the service container during backend startup:

```python
# In BackendLifecycleManager
from backend.api_gateway.plugins.my_plugin import MyPlugin

# Register plugin with service container
container.register_service(
    "my_plugin",
    lambda: MyPlugin("my_plugin", container),
    dependencies=["config", "database"],
    priority=100
)
```

### Database Integration

Plugins receive a shared encrypted database connection:

```python
class DatabasePlugin(BasePlugin):
    def __init__(self, name: str, container: ServiceContainer):
        super().__init__(name, container)
        
    @property
    def metadata(self):
        return PluginMetadata(
            name="Database Plugin",
            version="1.0.0",
            description="Database integration plugin",
            priority=PluginPriority.NORMAL
        )
        
    async def initialize(self) -> None:
        self.db_connection = self.require_service('database')
    
    async def start(self):
        # Use shared connection
        cursor = self.db_connection.execute("SELECT * FROM logs LIMIT 5")
        results = cursor.fetchall()
        self.logger.info(f"Found {len(results)} recent logs")
```

## Middleware Development

### ASGI Middleware Pattern

The current architecture uses ASGI middleware for cross-cutting concerns:

```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class CustomMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, key_manager):
        super().__init__(app)
        self.key_manager = key_manager
    
    async def dispatch(self, request: Request, call_next):
        # Pre-processing
        response = await call_next(request)
        # Post-processing
        return response
```

### Encryption Middleware Integration

The encryption middleware wraps the entire FastAPI app:

```python
from backend.api_gateway.middleware.encryption import EncryptionMiddleware
from aico.security.key_manager import AICOKeyManager

# In main.py
key_manager = AICOKeyManager(config_manager)
app = EncryptionMiddleware(fastapi_app, key_manager)
```

## Message Bus Integration

### Publishing Messages

Use the shared message bus client for inter-module communication:

```python
from aico.core.bus import MessageBusClient

class ServicePlugin(BasePlugin):
    async def start(self):
        self.bus_client = MessageBusClient()
        await self.bus_client.connect()
    
    async def publish_event(self, event_data):
        await self.bus_client.publish("events.service", event_data)
```

### Subscribing to Topics

Subscribe to message bus topics for reactive processing:

```python
async def handle_message(self, topic: str, message: dict):
    self.logger.info(f"Received message on {topic}: {message}")

async def start(self):
    await self.bus_client.subscribe("logs.*", self.handle_message)
```

## Shared Library Integration

### Using Core Utilities

Import shared utilities following the namespace pattern:

```python
from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.core.paths import AICOPaths
from aico.security import AICOKeyManager
from aico.data.libsql.encrypted import EncryptedLibSQLConnection
```

### Configuration Management

Access configuration through the centralized system:

```python
class ConfiguredService:
    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        
        # Access nested configuration
        api_config = self.config.get("core.api_gateway", {})
        port = api_config.get("rest.port", 8771)
        
        # Plugin-specific configuration
        plugin_config = self.config.get("plugins.my_plugin", {})
```

### Logging Patterns

Use structured logging with ZMQ transport:

```python
from aico.core.logging import get_logger

class LoggingService:
    def __init__(self):
        self.logger = get_logger("service", "component")
    
    def process_request(self, request_id: str):
        self.logger.info(
            "Processing request",
            extra={
                "request_id": request_id,
                "event_type": "request_processing",
                "component": "service"
            }
        )
```

## Process Management

### Graceful Shutdown

Implement proper shutdown handling in plugins:

```python
class ManagedPlugin(BasePlugin):
    def __init__(self, name: str, container: ServiceContainer):
        super().__init__(name, container)
        self.running = False
        self.background_tasks = set()
    
    async def start(self):
        self.running = True
        task = asyncio.create_task(self.background_worker())
        self.background_tasks.add(task)
    
    async def stop(self):
        self.running = False
        # Cancel background tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
        # Wait for cleanup
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
```

### Background Task Management

Coordinate background tasks with the main process:

```python
async def background_worker(self):
    while self.running:
        try:
            # Background work
            await self.process_queue()
            await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            self.logger.info("Background worker cancelled")
            break
        except Exception as e:
            self.logger.error(f"Background worker error: {e}")
            await asyncio.sleep(5.0)
```

## Database Patterns

### Encrypted Connection Usage

Use the shared encrypted database connection:

```python
class DatabaseService:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def insert_record(self, data):
        cursor = self.db.execute(
            "INSERT INTO table_name (column1, column2) VALUES (?, ?)",
            (data['value1'], data['value2'])
        )
        self.db.commit()
        return cursor.lastrowid
    
    def query_records(self, filter_value):
        cursor = self.db.execute(
            "SELECT * FROM table_name WHERE column1 = ?",
            (filter_value,)
        )
        return cursor.fetchall()
```

### Transaction Management

Handle transactions properly with error recovery:

```python
def transactional_operation(self, operations):
    try:
        for operation in operations:
            self.db.execute(operation['sql'], operation['params'])
        self.db.commit()
        self.logger.info("Transaction completed successfully")
    except Exception as e:
        self.db.rollback()
        self.logger.error(f"Transaction failed, rolled back: {e}")
        raise
```

## Error Handling

### Plugin Error Recovery

Implement robust error handling in plugins:

```python
class ResilientPlugin(BasePlugin):
    async def start(self):
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                await self.initialize_service()
                break
            except Exception as e:
                retry_count += 1
                self.logger.warning(f"Initialization failed (attempt {retry_count}): {e}")
                if retry_count >= max_retries:
                    self.logger.error("Max retries exceeded, plugin failed to start")
                    raise
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
```

### Middleware Error Handling

Handle errors gracefully in middleware:

```python
async def dispatch(self, request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        self.logger.error(f"Request processing failed: {e}")
        return Response(
            content={"error": "Internal server error"},
            status_code=500,
            media_type="application/json"
        )
```

## Testing Patterns

### Plugin Testing

Test plugins with mock dependencies:

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_config():
    config = Mock()
    config.get.return_value = {"test": "value"}
    return config

@pytest.fixture
def mock_db():
    db = Mock()
    db.execute.return_value = Mock()
    return db

@pytest.mark.asyncio
async def test_plugin_start(mock_config, mock_db):
    plugin = MyPlugin(mock_config, db_connection=mock_db)
    await plugin.start()
    assert plugin.running is True
```

### Integration Testing

Test with real shared components:

```python
@pytest.mark.integration
async def test_message_bus_integration():
    from aico.core.config import ConfigurationManager
    from aico.core.bus import MessageBusClient
    
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    
    client = MessageBusClient()
    await client.connect()
    
    # Test publish/subscribe
    received_messages = []
    
    async def handler(topic, message):
        received_messages.append((topic, message))
    
    await client.subscribe("test.*", handler)
    await client.publish("test.message", {"data": "test"})
    
    # Allow message processing
    await asyncio.sleep(0.1)
    
    assert len(received_messages) == 1
    assert received_messages[0][0] == "test.message"
```

## Performance Considerations

### Async/Await Best Practices

Use proper async patterns for non-blocking operations:

```python
class AsyncService:
    async def process_batch(self, items):
        # Process items concurrently
        tasks = [self.process_item(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle results and exceptions
        successful = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]
        
        self.logger.info(f"Processed {len(successful)} items, {len(failed)} failed")
        return successful
```

### Resource Management

Manage resources efficiently in long-running services:

```python
class ResourceManagedService:
    def __init__(self):
        self.connection_pool = {}
        self.cache = {}
        self.max_cache_size = 1000
    
    async def get_connection(self, key):
        if key not in self.connection_pool:
            self.connection_pool[key] = await self.create_connection(key)
        return self.connection_pool[key]
    
    def cache_result(self, key, value):
        if len(self.cache) >= self.max_cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = value
```

## Deployment Patterns

### Service Configuration

Configure services for different deployment environments:

```python
class DeploymentAwareService:
    def __init__(self, config_manager):
        self.config = config_manager
        self.environment = self.config.get("environment", "development")
        
        if self.environment == "production":
            self.setup_production_config()
        else:
            self.setup_development_config()
    
    def setup_production_config(self):
        # Production-specific configuration
        self.log_level = "INFO"
        self.enable_metrics = True
        self.connection_timeout = 30
    
    def setup_development_config(self):
        # Development-specific configuration
        self.log_level = "DEBUG"
        self.enable_metrics = False
        self.connection_timeout = 5
```

### Health Checks

Implement health checks for service monitoring:

```python
class HealthCheckPlugin(BasePlugin):
    async def health_check(self):
        checks = {
            "database": await self.check_database(),
            "message_bus": await self.check_message_bus(),
            "external_services": await self.check_external_services()
        }
        
        all_healthy = all(checks.values())
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
```
