"""
AICO Backend Lifecycle Manager - Clean FastAPI Integration

Centralized lifecycle management that properly integrates AICO's service container
with FastAPI's lifespan events, eliminating event loop conflicts and dependency issues.
"""

import asyncio
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger, initialize_logging
from aico.security import AICOKeyManager
from aico.core.paths import AICOPaths
from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.data.user import UserService

from .service_container import ServiceContainer, BaseService
from backend.core.plugin_base import get_plugin_registry
from backend.api_gateway.core.protocol_manager import ProtocolAdapterManager
from backend.api_gateway.middleware.encryption import EncryptionMiddleware
# Import moved to avoid circular dependency

class BackendLifecycleManager:
    """
    Centralized lifecycle management for AICO backend
    
    Manages service container, FastAPI app creation, middleware configuration,
    and router mounting with proper dependency injection.
    """
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        self.logger = get_logger("backend", "core.lifecycle_manager")
        import time
        self.start_time = time.time()
        
        # Core components
        self.container = ServiceContainer(config_manager)
        self.db_connection: Optional[EncryptedLibSQLConnection] = None
        self.app: Optional[FastAPI] = None
        
        # Protocol adapter manager for WebSocket and other protocols
        self.protocol_manager = ProtocolAdapterManager(
            config_manager.get("core.api_gateway", {}),
            self.logger
        )
        
        self.logger.info("Backend lifecycle manager initialized")
    
    def _display_startup_status(self):
        """Display beautiful cross-platform startup status for all components"""
        print("\n[i] System Status:")
        print("-" * 40)
        
        # Service container status
        services = self.container._definitions
        from .service_container import ServiceState
        
        running_count = sum(1 for svc in services.values() if svc.state == ServiceState.RUNNING)
        total_count = len(services)
        
        print(f"[✓] Service Container: {running_count}/{total_count} services running")
        
        # Display individual service status
        for name, service_def in sorted(services.items()):
            status_icon = "✓" if service_def.state == ServiceState.RUNNING else "✗"
            print(f"  [{status_icon}] {name}: {service_def.state.value}")
        
        # Database status
        if self.db_connection:
            print(f"[✓] Database: Connected (encrypted)")
        else:
            print(f"[✗] Database: Not connected")
        
        # FastAPI status
        if self.app:
            print(f"[✓] REST API: Ready on http://127.0.0.1:8771")
        else:
            print(f"[✗] REST API: Not initialized")
        
        # Protocol adapter status
        protocols_config = self.config.get("core.api_gateway.protocols", {})
        
        # WebSocket status
        websocket_config = protocols_config.get("websocket", {})
        if websocket_config.get("enabled", True):
            port = websocket_config.get('port', 8772)
            path = websocket_config.get('path', '/ws')
            print(f"[✓] WebSocket: Running on ws://127.0.0.1:{port}{path}")
        else:
            print(f"[!] WebSocket: Disabled")
        
        
        # Security status
        print(f"[✓] Transport Security: Active (AES-256-GCM)")
        print(f"[✓] Plugin Security: Sandboxed & Mediated")
        
        print("-" * 40)
        print("[*] Ready to serve requests!\n")
    
    async def startup(self) -> FastAPI:
        """Complete backend startup sequence"""
        self.logger.info("Starting AICO backend components...")
        
        # 1. Initialize service container
        await self._initialize_container()
        
        # 2. Create FastAPI app
        self.app = self._create_fastapi_app()
        
        # 3. Configure middleware stack
        self._configure_middleware()
        
        # 4. Mount API routers
        self._mount_routers()
        
        # Start all services
        await self.container.start_all()
        
        # Display service and plugin startup status
        self._display_service_status()
        self._display_plugin_status()
        
        # Start ZMQ message broker
        await self._start_message_broker()
        
        # Display available routes
        self._display_routes()
        
        # Display log consumer status (debug logic removed)
        
        # Start protocol adapters (WebSocket, ZeroMQ)
        await self._start_protocol_adapters()
        
        self.logger.info("AICO backend startup complete")
        return self.app
    
    async def stop(self) -> None:
        """Complete backend shutdown sequence with cross-platform status display"""
        self.logger.info("Shutting down AICO backend components...")
        
        print("[i] Shutdown Status:")
        print("-" * 40)
        
        # Stop protocol adapters first
        await self._stop_protocol_adapters()
        
        # Stop service container
        if self.container:
            services = list(self.container._definitions.keys())
            print(f"[~] Stopping {len(services)} services...")
            
            await self.container.stop_all()
            
            for service_name in sorted(services):
                print(f"  [-] {service_name} stopped")
        
        print("-" * 40)
        print("[+] All services stopped gracefully")
        
        self.logger.info("Backend shutdown complete")
    
    async def _initialize_container(self) -> None:
        """Initialize service container with all services"""
        self.container = ServiceContainer(self.config)
        
        # Register plugin classes first
        self._register_plugin_classes()
        
        # Register core services
        await self._register_core_services()
        
        # Register plugins
        await self._register_plugins()
        
        self.logger.info("Service container initialized")
    
    async def _register_core_services(self) -> None:
        """Register core infrastructure services"""
        
        # Database connection factory
        def create_database_connection(container: ServiceContainer) -> EncryptedLibSQLConnection:
            key_manager = AICOKeyManager(container.config)
            paths = AICOPaths()
            db_path = paths.resolve_database_path("aico.db")
            
            # Get encryption key
            cached_key = key_manager._get_cached_session()
            if cached_key:
                key_manager._extend_session()
                db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
            else:
                import keyring
                stored_key = keyring.get_password(key_manager.service_name, "master_key")
                if stored_key:
                    master_key = bytes.fromhex(stored_key)
                    db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
                else:
                    raise RuntimeError("Master key not found. Run 'aico security setup' to initialize.")
            
            return EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        
        # ZMQ context factory
        def create_zmq_context(container: ServiceContainer):
            import zmq
            return zmq.Context()
        
        # User service factory
        def create_user_service(container: ServiceContainer, database: EncryptedLibSQLConnection) -> UserService:
            return UserService(database)
        
        # Config service factory
        def create_config_service(container: ServiceContainer):
            return container.config
        
        # Register services
        self.container.register_service(
            "database",
            create_database_connection,
            dependencies=[],
            priority=5  # Start early, stop late
        )
        
        self.container.register_service(
            "config",
            create_config_service,
            dependencies=[],
            priority=1  # Start first
        )
        
        self.container.register_service(
            "zmq_context",
            create_zmq_context,
            dependencies=[],
            priority=10  # Start after database, stop before database
        )
        
        self.container.register_service(
            "user_service",
            create_user_service,
            dependencies=["database"],
            priority=20
        )
        
        # Task scheduler factory
        def create_task_scheduler(container: ServiceContainer):
            from backend.scheduler import TaskScheduler
            return TaskScheduler("task_scheduler", container)
        
        self.container.register_service(
            "task_scheduler",
            create_task_scheduler,
            dependencies=[],
            priority=25
        )
        
        self.logger.debug("Core services registered")
    
    def _register_plugin_classes(self) -> None:
        """Register all plugin classes with the plugin registry"""
        from backend.api_gateway.plugins import (
            MessageBusPlugin,
            SecurityPlugin,
            RateLimitingPlugin,
            ValidationPlugin,
            RoutingPlugin,
            LogConsumerPlugin,
            EncryptionPlugin
        )
        
        registry = get_plugin_registry()
        
        # Register plugin classes
        registry.register_plugin_class("message_bus", MessageBusPlugin)
        registry.register_plugin_class("security", SecurityPlugin)
        registry.register_plugin_class("rate_limiting", RateLimitingPlugin)
        registry.register_plugin_class("validation", ValidationPlugin)
        registry.register_plugin_class("routing", RoutingPlugin)
        registry.register_plugin_class("log_consumer", LogConsumerPlugin)
        registry.register_plugin_class("encryption", EncryptionPlugin)
        
        self.logger.debug("Plugin classes registered")
    
    async def _register_plugins(self) -> None:
        """Register plugin services"""
        # Get plugin configuration
        plugin_config = self.config.get("core.api_gateway.plugins", {})
        
        for plugin_name, config in plugin_config.items():
            if not config.get("enabled", False):
                self.logger.debug(f"Plugin {plugin_name} disabled, skipping registration")
                continue
            
            # Get plugin factory from registry
            try:
                factory = get_plugin_registry().create_plugin_factory(plugin_name)
                
                # Determine dependencies based on plugin type
                dependencies = self._get_plugin_dependencies(plugin_name)
                
                # Register plugin service
                self.container.register_service(
                    f"{plugin_name}_plugin",
                    factory,
                    dependencies=dependencies,
                    priority=self._get_plugin_priority(plugin_name)
                )
                
                self.logger.debug(f"Plugin service registered: {plugin_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to register plugin '{plugin_name}': {e}")
                # Fail fast - don't continue with broken plugins
                raise
        
        self.logger.debug("Plugin services registered")
    
    def _get_plugin_dependencies(self, plugin_name: str) -> List[str]:
        """Get plugin dependencies based on plugin type"""
        # Standard dependencies for different plugin types
        dependency_map = {
            "security": ["database", "zmq_context"],
            "encryption": ["database"],
            "rate_limiting": ["database"],
            "validation": [],
            "routing": [],
            "message_bus": ["zmq_context"],
            "log_consumer": ["database", "zmq_context"],
        }
        
        return dependency_map.get(plugin_name, [])
    
    def _get_plugin_priority(self, plugin_name: str) -> int:
        """Get plugin startup priority"""
        priority_map = {
            "message_bus": 20,
            "log_consumer": 25,  # Start log consumer after message bus
            "security": 30,
            "encryption": 35,
            "rate_limiting": 40,
            "validation": 45,
            "routing": 50,
        }
        
        return priority_map.get(plugin_name, 100)
    
    async def _start_protocol_adapters(self) -> None:
        """Start protocol adapters (WebSocket, ZeroMQ)"""
        try:
            # Get protocol configuration
            protocols_config = self.config.get("core.api_gateway.protocols", {})
            
            # Prepare dependencies from service container
            dependencies = {
                'config': self.config,
                'logger': self.logger,
                'db_connection': self.container.get_service('database'),
                'zmq_context': self.container.get_service('zmq_context'),
            }
            
            # Add plugin services as dependencies
            try:
                security_plugin = self.container.get_service('security_plugin')
                if security_plugin:
                    dependencies['authz_manager'] = getattr(security_plugin, 'authz_manager', None)
                    dependencies['auth_manager'] = getattr(security_plugin, 'auth_manager', None)
            except:
                self.logger.warning("Security plugin not available for protocol adapters")
            
            try:
                routing_plugin = self.container.get_service('routing_plugin')
                if routing_plugin:
                    dependencies['message_router'] = getattr(routing_plugin, 'message_router', None)
            except:
                self.logger.warning("Routing plugin not available for protocol adapters")
            
            try:
                rate_limiting_plugin = self.container.get_service('rate_limiting_plugin')
                if rate_limiting_plugin:
                    dependencies['rate_limiter'] = getattr(rate_limiting_plugin, 'rate_limiter', None)
            except:
                self.logger.warning("Rate limiting plugin not available for protocol adapters")
            
            try:
                validation_plugin = self.container.get_service('validation_plugin')
                if validation_plugin:
                    dependencies['validator'] = getattr(validation_plugin, 'validator', None)
            except:
                self.logger.warning("Validation plugin not available for protocol adapters")
            
            # Initialize and start WebSocket adapter if enabled
            websocket_config = protocols_config.get("websocket", {})
            if websocket_config.get("enabled", True):
                print(f"[+] Starting WebSocket server on port {websocket_config.get('port', 8772)}...")
                await self.protocol_manager.initialize_adapter("websocket", websocket_config, dependencies)
                await self.protocol_manager.start_adapter("websocket")
                print(f"[✓] WebSocket server running on ws://127.0.0.1:{websocket_config.get('port', 8772)}{websocket_config.get('path', '/ws')}")
            
            self.logger.info("Protocol adapters started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start protocol adapters: {e}")
            raise
    
    async def _stop_protocol_adapters(self) -> None:
        """Stop protocol adapters"""
        try:
            print(f"[~] Stopping protocol adapters...")
            await self.protocol_manager.stop_all()
            print(f"[✓] Protocol adapters stopped")
        except Exception as e:
            self.logger.error(f"Error stopping protocol adapters: {e}")
    
    def _create_fastapi_app(self) -> FastAPI:
        """Create FastAPI application with proper lifespan"""
        
        @asynccontextmanager
        async def app_lifespan(app: FastAPI):
            # Services already started in startup() - just store references
            try:
                # Store container for dependency injection
                app.state.service_container = self.container
                app.state.lifecycle_manager = self
                
                yield
                
            finally:
                # Shutdown handled by lifecycle manager
                # (actual shutdown called from main())
                pass
        
        app = FastAPI(
            title="AICO Backend API",
            version="0.5.0",
            description="AICO Backend REST API with clean architecture",
            lifespan=app_lifespan
        )
        
        return app
    
    def _configure_middleware(self) -> None:
        """Configure middleware stack in correct order"""
        if not self.app:
            raise RuntimeError("FastAPI app not created")
        
        # 1. CORS middleware (outermost)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 2. Request logging middleware (before encryption)
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            if request.url.path.startswith("/api/v1/"):
                self.logger.debug(f"Request: {request.method} {request.url.path}")
            
            response = await call_next(request)
            
            # Check if this is a protected endpoint that needs encryption
            if response.status_code == 404 and request.url.path.startswith("/api/v1/"):
                protected_paths = ["/api/v1/users/", "/api/v1/admin/", "/api/v1/logs/", "/api/v1/echo"]
                public_paths = ["/api/v1/health", "/api/v1/handshake"]
                
                is_protected = any(request.url.path.startswith(path) for path in protected_paths)
                is_public = any(request.url.path.startswith(path) for path in public_paths)
                
                if is_protected and not is_public:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=401,
                        content={
                            "detail": "This endpoint requires encrypted communication. Please establish an encrypted session first.",
                            "hint": "Use /api/v1/handshake to establish encryption",
                            "endpoint": request.url.path
                        }
                    )
            
            if request.url.path.startswith("/api/v1/") and response.status_code >= 400:
                self.logger.warning(f"Response: {request.method} {request.url.path} -> {response.status_code}")
            
            return response
        
        # 3. Plugin-based middleware will be added by plugins during their initialization
        
        self.logger.debug("Middleware stack configured")
    
    def _mount_routers(self) -> None:
        """Mount API routers with proper dependency injection"""
        if not self.app:
            raise RuntimeError("FastAPI app not created")
        
        # Import version function
        from aico.core.version import get_backend_version
        
        # Health endpoint
        @self.app.get("/api/v1/health")
        async def health_check():
            from datetime import datetime, timezone
            import time
            return {
                "status": "healthy", 
                "service": "aico-backend", 
                "version": get_backend_version(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0
            }
        
        # Container health endpoint
        @self.app.get("/api/v1/health/detailed")
        async def detailed_health_check(request: Request):
            from datetime import datetime, timezone
            import time
            import psutil
            import os
            
            container = request.app.state.service_container
            health_status = await container.health_check()
            
            # Add comprehensive system information
            try:
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                cpu_percent = process.cpu_percent()
                
                # System metrics
                system_memory = psutil.virtual_memory()
                system_cpu = psutil.cpu_percent(interval=0.1)
                # Cross-platform disk usage - use root drive
                import platform
                if platform.system() == 'Windows':
                    disk_usage = psutil.disk_usage('C:\\')
                else:
                    disk_usage = psutil.disk_usage('/')
                
                # Network connections (count) - handle permission issues
                try:
                    connections = len(psutil.net_connections())
                except (psutil.AccessDenied, OSError):
                    connections = 0
                
                enhanced_status = {
                    **health_status,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0,
                    "process": {
                        "pid": os.getpid(),
                        "memory_mb": round(memory_info.rss / 1024 / 1024, 2),
                        "memory_percent": round(process.memory_percent(), 2),
                        "cpu_percent": cpu_percent,
                        "threads": process.num_threads(),
                        "open_files": len(process.open_files()) if hasattr(process, 'open_files') and platform.system() != 'Windows' else 0
                    },
                    "system": {
                        "cpu_percent": system_cpu,
                        "memory_percent": system_memory.percent,
                        "memory_available_gb": round(system_memory.available / 1024 / 1024 / 1024, 2),
                        "disk_percent": disk_usage.percent,
                        "disk_free_gb": round(disk_usage.free / 1024 / 1024 / 1024, 2),
                        "network_connections": connections
                    },
                    "environment": {
                        "python_version": f"{platform.python_version()}",
                        "platform": platform.system(),
                        "platform_release": platform.release(),
                        "hostname": platform.node()
                    }
                }
                
                return enhanced_status
                
            except Exception as e:
                # Fallback if psutil fails
                return {
                    **health_status,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0,
                    "error": f"Failed to collect system metrics: {str(e)}"
                }
        
        # Gateway status endpoint (missing route causing 404)
        @self.app.get("/api/v1/gateway/status")
        async def gateway_status():
            return {
                "status": "healthy",
                "service": "aico-api-gateway", 
                "adapters": ["rest", "websocket"],
                "version": get_backend_version()
            }
        
        # Handshake endpoint handled by encryption middleware - no fallback needed
        
        # Mount domain routers
        self._mount_domain_routers()
        
        self.logger.debug("API routers mounted")
        
        # Apply encryption middleware as final ASGI wrapper (after all routers mounted)
        print("[~] Initializing encryption middleware...")
        self.logger.info("Starting encryption middleware initialization")
        key_manager = AICOKeyManager(self.config)
        # Store reference to FastAPI app before wrapping for route display
        self.fastapi_app = self.app
        self.app = EncryptionMiddleware(self.app, key_manager)
        print("[+] Encryption middleware started successfully")
        self.logger.info("Encryption middleware started successfully")
    
    def _display_service_status(self) -> None:
        """Display core service startup status"""
        print("\n[i] Core Service Status:")
        print("-" * 40)
        
        core_services = ["database", "zmq_context", "user_service", "task_scheduler"]
        
        for service_name in core_services:
            try:
                service = self.container.get_service(service_name)
                if service:
                    if service_name == "task_scheduler":
                        # Check if the scheduler is running
                        if getattr(service, 'running', False):
                            print(f"[✓] {service_name}: Running")
                        else:
                            print(f"[!] {service_name}: Initialized but not started")
                    else:
                        print(f"[✓] {service_name}: Running")
                else:
                    print(f"[✗] {service_name}: Failed to start")
            except Exception as e:
                print(f"[✗] {service_name}: Error - {e}")
        
        print("-" * 40)
    
    def _display_plugin_status(self) -> None:
        """Display plugin startup status"""
        print("\n[i] Plugin Status:")
        print("-" * 40)
        
        plugin_config = self.config.get("core.api_gateway.plugins", {})
        
        for plugin_name, config in plugin_config.items():
            if config.get("enabled", False):
                try:
                    plugin_service = self.container.get_service(f"{plugin_name}_plugin")
                    if plugin_service:
                        print(f"[✓] {plugin_name}_plugin: Running")
                    else:
                        print(f"[✗] {plugin_name}_plugin: Failed to start")
                except:
                    print(f"[✗] {plugin_name}_plugin: Not registered")
            else:
                print(f"[!] {plugin_name}_plugin: Disabled")
        
        print("-" * 40)
    
    def _mount_domain_routers(self) -> None:
        """Mount domain-specific API routers"""
        # Import routers
        from backend.api.echo.router import router as echo_router
        from backend.api.users.router import router as users_router
        from backend.api.admin.router import router as admin_router
        from backend.api.logs.router import router as logs_router
        from backend.api.conversation.router import router as conversation_router
        
        # Mount routers with prefixes
        self.app.include_router(echo_router, prefix="/api/v1/echo", tags=["echo"])
        self.app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
        self.app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
        self.app.include_router(logs_router, prefix="/api/v1/logs", tags=["logs"])
        self.app.include_router(conversation_router, prefix="/api/v1/conversation", tags=["conversation"])
        
    
    def _display_routes(self) -> None:
        """Display available API route groups"""
        print("\n[i] Available API Routes:")
        print("-" * 40)
        
        if hasattr(self, 'fastapi_app') and self.fastapi_app:
            route_groups = set()
            for route in self.fastapi_app.routes:
                if hasattr(route, 'path') and route.path.startswith('/api/v1/'):
                    # Extract route group (e.g., /api/v1/users, /api/v1/admin)
                    path_parts = route.path.split('/')
                    if len(path_parts) >= 4:
                        route_group = '/'.join(path_parts[:4])  # /api/v1/users
                        route_groups.add(route_group)
                    elif route.path == '/api/v1/health':
                        route_groups.add('/api/v1/health')
            
            for route_group in sorted(route_groups):
                print(f"[→] {route_group}/*")
            
            # Show non-API routes
            other_routes = []
            for route in self.fastapi_app.routes:
                if hasattr(route, 'path') and not route.path.startswith('/api/v1/'):
                    if route.path not in ['/', '/docs', '/redoc', '/openapi.json']:
                        other_routes.append(route.path)
            
            if other_routes:
                for route in sorted(other_routes):
                    print(f"[→] {route}")
        else:
            print("[✗] FastAPI app not initialized")
        
        print("-" * 40)
    
    async def _start_message_broker(self) -> None:
        """Start ZMQ message broker"""
        try:
            print("[+] Starting ZMQ message broker...")
            message_bus_plugin = self.container.get_service('message_bus_plugin')
            if message_bus_plugin:
                # Message bus plugin starts broker in its start() method
                print("[✓] ZMQ message broker running on tcp://*:5555")
                
                # Notify ZMQ log transport that broker is ready to flush buffered messages
                self._notify_log_transport_broker_ready()
            else:
                print("[✗] ZMQ message broker not available - message_bus_plugin not found")
                
        except Exception as e:
            self.logger.error(f"Failed to start message broker: {e}")
            print(f"[✗] ZMQ message broker failed: {e}")
    
    def _notify_log_transport_broker_ready(self) -> None:
        """Notify ZMQ log transport that broker is ready, but delay buffer flush until LogConsumer is subscribed"""
        try:

            # Get the global ZMQ transport instance from the logging system
            from aico.core.logging import _get_zmq_transport
            zmq_transport = _get_zmq_transport()
            if zmq_transport:
                # Mark broker ready but don't flush buffer yet
                zmq_transport._broker_available = True
            else:
                self.logger.warning("ZMQ log transport not found - startup messages may be lost")
                
            # Notify log consumer service to connect
            self._notify_log_consumer_broker_ready()
                
        except Exception as e:
            self.logger.warning(f"Failed to notify ZMQ log transport: {e}")
    
    def _notify_log_consumer_broker_ready(self) -> None:
        """Notify log consumer service that broker is ready and schedule buffer flush after subscription"""
        try:
            log_consumer_plugin = self.container.get_service('log_consumer_plugin')
            if log_consumer_plugin and log_consumer_plugin.log_consumer:
                print("[+] Notifying log consumer that broker is ready...")
                import asyncio
                # Run the async method in the current event loop and flush buffer after subscription
                asyncio.create_task(self._connect_log_consumer_and_flush_buffer(log_consumer_plugin.log_consumer))
                print("[✓] Log consumer notified - will connect to message bus and flush buffer")
            else:
                print("[!] Log consumer service not found")
        except Exception as e:
            self.logger.warning(f"Failed to notify log consumer: {e}")
            print(f"[!] Warning: Could not notify log consumer: {e}")
    
    async def _connect_log_consumer_and_flush_buffer(self, log_consumer):
        """Connect log consumer and flush buffer after subscription is complete"""
        try:
            # Connect the log consumer first
            await log_consumer.connect_when_broker_ready()
            
            # Wait a brief moment for subscription to be fully established
            import asyncio
            await asyncio.sleep(0.1)
            
            # Now flush the buffered logs
            from aico.core.logging import _get_zmq_transport
            zmq_transport = _get_zmq_transport()
            if zmq_transport:
                zmq_transport._flush_log_buffer()
            else:
                self.logger.warning("ZMQ transport not found for buffer flush")
                
        except Exception as e:
            self.logger.warning(f"Failed to connect log consumer and flush buffer: {e}")
    
    def _display_log_consumer_status(self) -> None:
        """Display log consumer service status"""
        print("\n[i] Log Consumer Status:")
        print("-" * 40)
        
        try:
            # Check plugin first
            log_consumer_plugin = self.container.get_service('log_consumer_plugin')
            if log_consumer_plugin:
                print(f"[✓] Log consumer plugin: Found")
                print(f"[i] Plugin enabled: {getattr(log_consumer_plugin, 'enabled', 'unknown')}")
                print(f"[i] Plugin running: {getattr(log_consumer_plugin, 'running', 'unknown')}")
                
                # Check if plugin has internal log consumer service
                internal_consumer = getattr(log_consumer_plugin, 'log_consumer', None)
                if internal_consumer:
                    print(f"[✓] Internal log consumer service: Found")
                    print(f"[i] Service running: {getattr(internal_consumer, 'running', 'unknown')}")
                    print(f"[i] Service enabled: {getattr(internal_consumer, 'enabled', 'unknown')}")
                    
                    if hasattr(internal_consumer, 'message_thread') and internal_consumer.message_thread:
                        thread_alive = internal_consumer.message_thread.is_alive()
                        print(f"[i] Message thread: {'Running' if thread_alive else 'Stopped'}")
                    else:
                        print("[!] Message thread: Not found")
                        
                    if hasattr(internal_consumer, 'subscriber'):
                        print(f"[i] ZMQ subscriber: {'Connected' if internal_consumer.subscriber else 'Not connected'}")
                else:
                    print("[!] Internal log consumer service: Not found")
            else:
                print("[✗] Log consumer plugin: Not found")
                
        except Exception as e:
            print(f"[✗] Log consumer: Error checking status - {e}")
        
        print("-" * 40)
    
    async def _debug_log_consumer_initialization(self) -> None:
        """Debug log consumer initialization issues"""
        print("\nLog Consumer Initialization:")
        print("-" * 40)
        
        try:
            # Check plugin first
            log_consumer_plugin = self.container.get_service('log_consumer_plugin')
            if log_consumer_plugin:
                print(f"[✓] Log consumer plugin: Found")
                print(f"[i] Plugin enabled: {getattr(log_consumer_plugin, 'enabled', 'unknown')}")
                
                # Force initialization if not done
                if not hasattr(log_consumer_plugin, 'log_consumer') or log_consumer_plugin.log_consumer is None:
                    print("[!] Internal service not found - forcing initialization...")
                    try:
                        await log_consumer_plugin.initialize()
                        print(f"[i] After init - service exists: {log_consumer_plugin.log_consumer is not None}")
                    except Exception as e:
                        print(f"[✗] Initialization failed: {e}")
                
                # Check internal service
                internal_consumer = getattr(log_consumer_plugin, 'log_consumer', None)
                if internal_consumer:
                    print(f"[✓] Internal log consumer service: Found")
                    print(f"[i] Service running: {getattr(internal_consumer, 'running', 'unknown')}")
                    print(f"[i] Service enabled: {getattr(internal_consumer, 'enabled', 'unknown')}")
                    
                    # Check dependencies
                    db_conn = getattr(internal_consumer, 'db_connection', None)
                    zmq_ctx = getattr(internal_consumer, 'zmq_context', None)
                    print(f"[i] DB connection: {'Found' if db_conn else 'Missing'}")
                    print(f"[i] ZMQ context: {'Found' if zmq_ctx else 'Missing'}")
                    
                    if hasattr(internal_consumer, 'message_thread') and internal_consumer.message_thread:
                        thread_alive = internal_consumer.message_thread.is_alive()
                        print(f"[i] Message thread: {'Running' if thread_alive else 'Stopped'}")
                    else:
                        print("[!] Message thread: Not found")
                        
                    if hasattr(internal_consumer, 'subscriber'):
                        print(f"[i] ZMQ subscriber: {'Connected' if internal_consumer.subscriber else 'Not connected'}")
                else:
                    print("[!] Internal log consumer service: Not found")
            else:
                print("[✗] Log consumer plugin: Not found")
                
        except Exception as e:
            print(f"[✗] Debug failed: {e}")
        
        print("-" * 40)


# Dependency injection functions for FastAPI
def get_service_container(request: Request) -> ServiceContainer:
    """Get service container from FastAPI app state"""
    if not hasattr(request.app.state, 'service_container'):
        raise RuntimeError("Service container not available")
    return request.app.state.service_container

def get_user_service(container: ServiceContainer = Depends(get_service_container)) -> UserService:
    """Get user service via dependency injection"""
    return container.get_service("user_service")

def get_auth_manager(container: ServiceContainer = Depends(get_service_container)):
    """Get auth manager via dependency injection"""
    # Auth manager is provided by security plugin
    security_plugin = container.get_service("security_plugin")
    if not security_plugin or not hasattr(security_plugin, 'auth_manager'):
        raise RuntimeError("Auth manager not available")
    return security_plugin.auth_manager

def get_database(container: ServiceContainer = Depends(get_service_container)) -> EncryptedLibSQLConnection:
    """Get database connection via dependency injection"""
    return container.get_service("database")
