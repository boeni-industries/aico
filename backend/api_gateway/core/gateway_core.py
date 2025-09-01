"""
AICO API Gateway Core - Modular Architecture

Central orchestrator for the modular API Gateway with plugin system,
protocol adapter management, and lifecycle coordination.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass

from aico.core.logging import get_logger, get_logger_factory
from aico.core.config import ConfigurationManager
from aico.core.bus import MessageBusClient
from aico.security.key_manager import AICOKeyManager

from .plugin_registry import PluginRegistry, PluginInterface
from .protocol_manager import ProtocolAdapterManager
from ..adapters.base import ProtocolAdapter


@dataclass
class GatewayStatus:
    """Gateway status information"""
    running: bool
    protocols_active: List[str]
    plugins_loaded: List[str]
    message_bus_connected: bool
    uptime_seconds: float


class GatewayCore:
    """
    Core orchestrator for the modular AICO API Gateway
    
    Responsibilities:
    - Plugin system management
    - Protocol adapter coordination
    - Lifecycle management
    - Configuration-driven setup
    - Dependency injection
    """
    
    def __init__(self, config: ConfigurationManager, logger=None, db_connection=None):
        self.config = config
        self.logger = logger or get_logger("api_gateway", "core")
        self.db_connection = db_connection
        
        # Core services
        self.key_manager = AICOKeyManager(config)
        self.message_bus: Optional[MessageBusClient] = None
        
        # ZMQ context for plugins
        import zmq
        self.zmq_context = zmq.Context()
        
        # Initialize auth managers (will be properly set up during plugin loading)
        self.auth_manager = None
        self.authz_manager = None
        self.message_router = None
        
        # Plugin system
        self.plugin_registry = PluginRegistry(config, self.logger)
        self.plugin_registry.db_connection = self.db_connection
        self.loaded_plugins: Dict[str, PluginInterface] = {}
        
        # Protocol management
        self.protocol_manager = ProtocolAdapterManager(config, self.logger)
        
        # State
        self.running = False
        self.start_time = 0.0
        
        # Gateway configuration - use proper config path
        core_config = config.get("core", {})
        gateway_config = core_config.get("api_gateway", {})
        self.enabled_protocols = gateway_config.get("protocols", {})
        self.enabled_plugins = gateway_config.get("plugins", {})
        
        self.logger.info(f"Enabled protocols from config: {list(self.enabled_protocols.keys())}")
        self.logger.info(f"Protocol configs: {self.enabled_protocols}")
        
        self.logger.info("Gateway core initialized", extra={
            "enabled_protocols": list(self.enabled_protocols.keys()),
            "enabled_plugins": list(self.enabled_plugins.keys())
        })
    
    async def start(self) -> None:
        """Start the API Gateway with all components"""
        try:
            self.start_time = time.time()
            
            self.logger.info("Starting AICO API Gateway...")
            
            # 1. Connect to message bus
            await self._connect_message_bus()
            
            # 2. Load and initialize plugins
            await self._load_plugins()

            # 2.5. Re-initialize loggers to ensure ZMQ transport is attached
            # This is necessary because some loggers may be created before the ZMQ context is ready.
            logger_factory = get_logger_factory()
            if logger_factory:
                logger_factory.reinitialize_loggers()
                # Ensure all loggers mark DB ready and flush any bootstrap buffers
                logger_factory.mark_all_databases_ready()
            
            # 3. Initialize protocol adapters
            await self._initialize_protocols()
            
            # 4. Start protocol adapters
            await self._start_protocols()
            
            self.running = True
            self.logger.info("AICO API Gateway started successfully", extra={
                "protocols": list(self.protocol_manager.get_active_protocols()),
                "plugins": list(self.loaded_plugins.keys())
            })
            
        except Exception as e:
            self.logger.error(f"Failed to start API Gateway: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop the API Gateway and cleanup resources"""
        try:
            self.logger.info("Stopping AICO API Gateway...")
            self.running = False
            
            # 1. Stop protocol adapters (includes cancelling their background tasks)
            await self._stop_protocols()
            
            # 2. Shutdown plugins (includes cancelling their background tasks)
            await self._shutdown_plugins()
            
            # 3. Disconnect message bus
            if self.message_bus:
                await self.message_bus.disconnect()
                self.message_bus = None
            
            self.logger.info("AICO API Gateway stopped")
            
        except Exception as e:
            self.logger.error(f"Error during gateway shutdown: {e}")
    
    async def _connect_message_bus(self) -> None:
        """Connect to the AICO message bus"""
        try:
            print("[GATEWAY CORE] Attempting to connect to message bus...")
            self.message_bus = MessageBusClient("api_gateway")
            print("[GATEWAY CORE] MessageBusClient created, calling connect()...")
            await self.message_bus.connect()
            print("[GATEWAY CORE] MessageBusClient.connect() completed successfully")
            # Set message bus on plugin registry for dependency injection
            self.plugin_registry.message_bus = self.message_bus
            self.logger.info("Connected to message bus")
            print("[GATEWAY CORE] Message bus connection established")
        except Exception as e:
            self.logger.error(f"Failed to connect to message bus: {e}")
            print(f"[GATEWAY CORE] ERROR: Failed to connect to message bus: {e}")
            import traceback
            print(f"[GATEWAY CORE] Traceback: {traceback.format_exc()}")
            raise
    
    async def _load_plugins(self) -> None:
        """Load and initialize enabled plugins"""
        try:
            # Register built-in plugins
            await self._register_builtin_plugins()
            
            # Skip Step 2 plugin loading since we handle plugins directly in Step 1
            # This avoids the "Plugin not registered" errors for plugins that don't implement PluginInterface
            pass
            
            self.logger.info(f"Loaded {len(self.loaded_plugins)} plugins")
            
        except Exception as e:
            self.logger.error(f"Failed to load plugins: {e}")
            raise
    
    async def _register_builtin_plugins(self):
        """Register built-in plugins based on configuration"""
        self.logger.debug("Starting plugin registration process")
        print("[GATEWAY CORE] Starting plugin registration process")
        
        # Debug: Show the entire config structure
        all_config = self.config.config_cache
        self.logger.debug(f"Full config structure keys: {list(all_config.keys())}")
        print(f"[GATEWAY CORE] Full config structure keys: {list(all_config.keys())}")
        
        # Debug: Check if api_gateway exists in config (it's nested under 'core')
        core_config = self.config.get('core', {})
        api_gateway_config = core_config.get('api_gateway', {})
        self.logger.debug(f"core config keys: {list(core_config.keys())}")
        print(f"[GATEWAY CORE] core config keys: {list(core_config.keys())}")
        self.logger.debug(f"api_gateway config keys: {list(api_gateway_config.keys())}")
        print(f"[GATEWAY CORE] api_gateway config keys: {list(api_gateway_config.keys())}")
        
        # Get plugins configuration from core.api_gateway.plugins
        plugins_config = api_gateway_config.get('plugins', {})
        self.logger.debug(f"Plugin config lookup result: {plugins_config}")
        print(f"[GATEWAY CORE] Plugin config lookup result: {plugins_config}")
        
        if not plugins_config:
            self.logger.warning("No plugins configuration found at 'api_gateway.plugins'")
            print("[GATEWAY CORE] WARNING: No plugins configuration found at 'api_gateway.plugins'")
            return
        
        # Import plugin classes
        from backend.log_consumer import AICOLogConsumer
        from backend.api_gateway.plugins.message_bus_plugin import MessageBusPlugin
        
        # Define available plugin classes
        plugin_classes = {
            'message_bus': MessageBusPlugin,
            'log_consumer': AICOLogConsumer,
        }
        
        self.logger.debug(f"Available plugin classes: {list(plugin_classes.keys())}")
        print(f"[GATEWAY CORE] Available plugin classes: {list(plugin_classes.keys())}")
        
        # Register each plugin
        for plugin_name, plugin_class in plugin_classes.items():
            self.logger.debug(f"Processing plugin: {plugin_name}")
            print(f"[GATEWAY CORE] Processing plugin: {plugin_name}")
            
            plugin_config = plugins_config.get(plugin_name, {})
            self.logger.debug(f"Config for {plugin_name}: {plugin_config}")
            print(f"[GATEWAY CORE] Config for {plugin_name}: {plugin_config}")
            
            if plugin_config.get('enabled', False):
                self.logger.info(f"Registering plugin: {plugin_name}")
                print(f"[GATEWAY CORE] Registering plugin: {plugin_name}")
                try:
                    plugin_instance = plugin_class(self.config, self.db_connection, self.zmq_context)
                    plugin_instance.start()
                    # Store in loaded_plugins for immediate access
                    self.loaded_plugins[plugin_name] = plugin_instance
                    self.logger.info(f"Successfully registered and started plugin: {plugin_name}")
                    print(f"[GATEWAY CORE] Successfully registered and started plugin: {plugin_name}")
                except Exception as e:
                    self.logger.error(f"Failed to register plugin {plugin_name}: {e}")
                    print(f"[GATEWAY CORE] ERROR: Failed to register plugin {plugin_name}: {e}")
                    import traceback
                    print(f"[GATEWAY CORE] Traceback: {traceback.format_exc()}")
            else:
                self.logger.debug(f"Plugin {plugin_name} is disabled or not configured")
                print(f"[GATEWAY CORE] Plugin {plugin_name} is disabled or not configured")
        
        # Log final plugin count
        active_plugins = list(self.loaded_plugins.keys())
        self.logger.info(f"Active plugins: {active_plugins}")
        print(f"[GATEWAY CORE] Active plugins: {active_plugins}")
        
        # Update gateway core references to plugin instances
        security_plugin = self.loaded_plugins.get('security')
        if security_plugin and hasattr(security_plugin, 'auth_manager'):
            self.auth_manager = security_plugin.auth_manager
            self.logger.info("Updated gateway core auth_manager from security plugin")
        
        if security_plugin and hasattr(security_plugin, 'authz_manager'):
            self.authz_manager = security_plugin.authz_manager
            self.logger.info("Updated gateway core authz_manager from security plugin")
    
    async def _initialize_protocols(self) -> None:
        """Initialize protocol adapters with dependency injection"""
        try:
            # Prepare dependencies for protocol adapters
            # Get log consumer from loaded plugins
            log_consumer_plugin = self.loaded_plugins.get('log_consumer')
            log_consumer = log_consumer_plugin if log_consumer_plugin else None
            
            dependencies = {
                'config': self.config,
                'logger': self.logger,
                'gateway': self,
                'key_manager': self.key_manager,
                'auth_manager': self.auth_manager,
                'authz_manager': self.authz_manager,
                'message_router': self.message_router,
                'log_consumer': log_consumer,  # ZMQ log consumer from plugin
                'db_connection': getattr(self, 'db_connection', None)  # Database connection
            }
            
            # Initialize REST adapter for FastAPI integration (no separate server)
            self.logger.debug(f"Full config structure: {list(self.config.config_cache.keys())}")
            self.logger.debug(f"Core config: {self.config.config_cache.get('core', {}).keys()}")
            
            # Use proper configuration access pattern
            core_config = self.config.config_cache.get('core', {})
            api_gateway_config = core_config.get('api_gateway', {})
            rest_config = api_gateway_config.get('rest', {})
            
            self.logger.debug(f"API Gateway config: {api_gateway_config.keys()}")
            self.logger.debug(f"REST config: {rest_config}")
            self.logger.debug(f"Registered adapters: {list(self.protocol_manager.registered_adapters.keys())}")
            
            # Initialize REST adapter for FastAPI integration
            success = await self.protocol_manager.initialize_adapter(
                "rest", 
                rest_config, 
                dependencies
            )
            self.logger.debug(f"REST adapter initialization success: {success}")
            
            # Initialize other enabled protocol adapters
            for protocol_name, protocol_config in self.enabled_protocols.items():
                if protocol_name != "rest" and protocol_config.get("enabled", False):
                    self.logger.debug(f"Initializing protocol adapter: {protocol_name}")
                    success = await self.protocol_manager.initialize_adapter(
                        protocol_name, 
                        protocol_config, 
                        dependencies
                    )
                    self.logger.debug(f"{protocol_name} adapter initialization success: {success}")
                    if not success:
                        self.logger.error(f"Failed to initialize protocol adapter: {protocol_name}")
            
            self.logger.info("Protocol adapters initialized")
            
        except Exception as e:
            self.logger.error(f"Protocol initialization failed: {e}")
            raise
    
    async def _start_protocols(self) -> None:
        """Start all initialized protocol adapters"""
        try:
            self.logger.debug("Starting protocol adapters...")
            await self.protocol_manager.start_all()
            self.logger.debug("Protocol adapters start_all() completed")
            self.logger.info("Protocol adapters started")
        except Exception as e:
            self.logger.error(f"Failed to start protocols: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.logger.error(f"Failed to start protocols: {e}")
            raise
    
    async def _stop_protocols(self) -> None:
        """Stop all protocol adapters"""
        try:
            await self.protocol_manager.stop_all()
            self.logger.info("Protocol adapters stopped")
        except Exception as e:
            self.logger.error(f"Error stopping protocols: {e}")
    
    async def _shutdown_plugins(self) -> None:
        """Shutdown all loaded plugins"""
        shutdown_tasks = []
        for plugin_name, plugin in self.loaded_plugins.items():
            try:
                # Create shutdown task for each plugin
                shutdown_task = asyncio.create_task(plugin.shutdown())
                shutdown_task.set_name(f"shutdown_{plugin_name}")
                shutdown_tasks.append((plugin_name, shutdown_task))
            except Exception as e:
                self.logger.error(f"Error creating shutdown task for plugin {plugin_name}: {e}")
        
        # Wait for all plugins to shutdown with timeout
        for plugin_name, task in shutdown_tasks:
            try:
                await asyncio.wait_for(task, timeout=5.0)
                self.logger.info(f"Shutdown plugin: {plugin_name}")
            except asyncio.TimeoutError:
                self.logger.warning(f"Plugin {plugin_name} shutdown timed out, cancelling")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            except Exception as e:
                self.logger.error(f"Error shutting down plugin {plugin_name}: {e}")
    
    def configure_fastapi_app(self, app):
        """Configure FastAPI app with plugin middleware"""
        from fastapi.middleware.cors import CORSMiddleware
        from starlette.middleware.base import BaseHTTPMiddleware
        
        # Get configuration
        config = self.config.config_cache.get('core', {})
        api_gateway_config = config.get('api_gateway', {})
        
        # NOTE: CORS middleware disabled to prevent bypassing ASGI encryption middleware
        # FastAPI HTTP middleware intercepts requests before ASGI middleware can process them
        # CORS should be handled at the ASGI level if needed
        self.logger.info("Skipped CORS middleware - would bypass ASGI encryption middleware")
        self.logger.info("CORS middleware skipped - would bypass ASGI encryption middleware")
        
        # Let plugins configure their middleware
        for plugin_name, plugin in self.loaded_plugins.items():
            if hasattr(plugin, 'configure_fastapi_middleware'):
                try:
                    plugin.configure_fastapi_middleware(app)
                    self.logger.info(f"Plugin {plugin_name} configured FastAPI middleware")
                except Exception as e:
                    self.logger.error(f"Plugin {plugin_name} failed to configure middleware: {e}")
    
    async def handle_request(self, protocol: str, request_data: Any, client_info: Dict[str, Any]) -> Any:
        """
        Handle incoming request through the plugin pipeline
        
        This is the main request processing pipeline that coordinates
        all plugins in the correct execution order.
        """
        try:
            # Create request context
            context = {
                'protocol': protocol,
                'request_data': request_data,
                'client_info': client_info,
                'gateway': self,
                'plugins': self.loaded_plugins
            }
            
            # Get plugin execution order from registry
            execution_order = self.plugin_registry.get_execution_order()
            
            # Execute plugin pipeline in priority order
            for plugin_name in execution_order:
                plugin = self.loaded_plugins.get(plugin_name)
                if plugin and plugin.is_enabled():
                    context = await plugin.process_request(context)
                    if context.get('error'):
                        # Plugin returned an error, stop processing
                        return context['error']
            
            # Return the final response
            return context.get('response', {'success': True})
            
        except Exception as e:
            self.logger.error(f"Request handling error: {e}", extra={
                "protocol": protocol,
                "client": client_info.get("client_id", "unknown")
            })
            raise
    
    def get_status(self) -> GatewayStatus:
        """Get current gateway status"""
        return GatewayStatus(
            running=self.running,
            protocols_active=list(self.protocol_manager.get_active_protocols()),
            plugins_loaded=list(self.loaded_plugins.keys()),
            message_bus_connected=self.message_bus is not None,
            uptime_seconds=time.time() - self.start_time if self.running else 0.0
        )
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginInterface]:
        """Get a loaded plugin by name"""
        return self.loaded_plugins.get(plugin_name)
    
    def get_protocol_adapter(self, protocol_name: str) -> Optional[ProtocolAdapter]:
        """Get a protocol adapter by name"""
        return self.protocol_manager.get_adapter(protocol_name)
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for the gateway"""
        try:
            health_data = {
                'status': 'healthy' if self.running else 'stopped',
                'uptime_seconds': time.time() - self.start_time if self.running else 0.0,
                'message_bus_connected': self.message_bus is not None,
                'plugins': {},
                'protocols': {}
            }
            
            # Plugin health checks
            for plugin_name, plugin in self.loaded_plugins.items():
                health_data['plugins'][plugin_name] = {
                    'enabled': plugin.is_enabled(),
                    'version': plugin.metadata.version,
                    'priority': plugin.metadata.priority.name
                }
            
            # Protocol adapter health checks
            for protocol_name in self.protocol_manager.get_active_protocols():
                adapter = self.protocol_manager.get_adapter(protocol_name)
                if adapter:
                    health_data['protocols'][protocol_name] = await adapter.health_check()
            
            return health_data
            
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get gateway statistics"""
        return {
            'gateway': {
                'running': self.running,
                'uptime_seconds': time.time() - self.start_time if self.running else 0.0
            },
            'plugins': self.plugin_registry.get_plugin_stats(),
            'protocols': self.protocol_manager.get_adapter_stats(),
            'message_bus': {
                'connected': self.message_bus is not None
            }
        }
