"""
AICO API Gateway Core - Modular Architecture

Central orchestrator for the modular API Gateway with plugin system,
protocol adapter management, and lifecycle coordination.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass

from aico.core.logging import get_logger
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
        
        # Initialize auth managers (will be properly set up during plugin loading)
        self.auth_manager = None
        self.authz_manager = None
        self.message_router = None
        
        # Plugin system
        self.plugin_registry = PluginRegistry(config, self.logger)
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
        
        print(f"[GATEWAY CORE] Enabled protocols from config: {list(self.enabled_protocols.keys())}")
        print(f"[GATEWAY CORE] Protocol configs: {self.enabled_protocols}")
        
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
            
            # 1. Stop protocol adapters
            await self._stop_protocols()
            
            # 2. Shutdown plugins
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
            self.message_bus = MessageBusClient("api_gateway")
            await self.message_bus.connect()
            self.logger.info("Connected to message bus")
        except Exception as e:
            self.logger.error(f"Failed to connect to message bus: {e}")
            raise
    
    async def _load_plugins(self) -> None:
        """Load and initialize enabled plugins"""
        try:
            # Register built-in plugins
            await self._register_builtin_plugins()
            
            # Load enabled plugins
            for plugin_name, plugin_config in self.enabled_plugins.items():
                if plugin_config.get("enabled", False):
                    plugin = await self.plugin_registry.load_plugin(plugin_name, plugin_config)
                    if plugin:
                        self.loaded_plugins[plugin_name] = plugin
                        self.logger.info(f"Loaded plugin: {plugin_name}")
            
            self.logger.info(f"Loaded {len(self.loaded_plugins)} plugins")
            
        except Exception as e:
            self.logger.error(f"Failed to load plugins: {e}")
            raise
    
    async def _register_builtin_plugins(self) -> None:
        """Register built-in plugins"""
        # Register built-in plugins
        from ..plugins.log_consumer_plugin import LogConsumerPlugin
        from ..plugins.message_bus_plugin import MessageBusPlugin
        from ..plugins.security_plugin import SecurityPlugin
        from ..plugins.rate_limiting_plugin import RateLimitingPlugin
        from ..plugins.validation_plugin import ValidationPlugin
        from ..plugins.routing_plugin import RoutingPlugin
        
        print(f"[GATEWAY CORE] Importing plugins...")
        
        plugin_classes = [
            LogConsumerPlugin, 
            MessageBusPlugin,
            SecurityPlugin,
            RateLimitingPlugin,
            ValidationPlugin,
            RoutingPlugin
        ]
        
        print(f"[GATEWAY CORE] Plugin classes to register: {[cls.__name__ for cls in plugin_classes]}")
        
        # Debug config structure
        try:
            core_config = self.config.get('core', {})
            print(f"[GATEWAY CORE] Core config keys: {list(core_config.keys()) if hasattr(core_config, 'keys') else 'N/A'}")
            if 'api_gateway' in core_config:
                api_gw_config = core_config['api_gateway']
                print(f"[GATEWAY CORE] API Gateway config keys: {list(api_gw_config.keys()) if hasattr(api_gw_config, 'keys') else 'N/A'}")
                if 'plugins' in api_gw_config:
                    plugins_config = api_gw_config.get('plugins', {})
                    print(f"[GATEWAY CORE] Plugins config: {plugins_config}")
        except Exception as e:
            print(f"[GATEWAY CORE] Error in config debug: {e}")
            import traceback
            print(f"[GATEWAY CORE] Traceback: {traceback.format_exc()}")
        
        for plugin_class in plugin_classes:
            try:
                print(f"[GATEWAY CORE] Processing plugin class: {plugin_class.__name__}")
                # Convert plugin class name to config key format
                # LogConsumerPlugin -> log_consumer, MessageBusPlugin -> message_bus
                plugin_name = plugin_class.__name__.replace('Plugin', '')
                # Convert CamelCase to snake_case
                import re
                plugin_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', plugin_name).lower()
                print(f"[GATEWAY CORE] Plugin name: {plugin_name}")
                
                # Try multiple config paths
                plugins_config = self.config.get('api_gateway.plugins', {})
                if not plugins_config:
                    # Try core.api_gateway.plugins
                    core_config = self.config.get('core', {})
                    api_gateway_config = core_config.get('api_gateway', {})
                    plugins_config = api_gateway_config.get('plugins', {})
                
                plugin_config = plugins_config.get(plugin_name, {})
                print(f"[GATEWAY CORE] Plugin config for {plugin_name}: {plugin_config}")
                print(f"[GATEWAY CORE] Available plugins config keys: {list(plugins_config.keys())}")
                
                print(f"[GATEWAY CORE] Processing plugin: {plugin_name}, enabled: {plugin_config.get('enabled', False)}")
                
                if plugin_config.get('enabled', False):
                    print(f"[GATEWAY CORE] Creating instance of {plugin_class.__name__}")
                    plugin_instance = plugin_class(plugin_config, self.logger)
                    print(f"[GATEWAY CORE] Registering plugin: {plugin_name}")
                    self.plugin_registry.register_plugin(plugin_name, plugin_instance)
                    print(f"[GATEWAY CORE] Registered plugin: {plugin_name}")
                    self.logger.info(f"Registered plugin: {plugin_name}")
                    
                    # Log registered plugins
                    try:
                        registered_plugins = list(self.plugin_registry.registered_plugins.keys())
                        print(f"[GATEWAY CORE] Final registered plugins: {registered_plugins}")
                        self.logger.info(f"Registered plugins: {registered_plugins}")
                    except Exception as e:
                        print(f"[GATEWAY CORE] Error getting registered plugins: {e}")
                        import traceback
                        print(f"[GATEWAY CORE] Traceback: {traceback.format_exc()}")
                else:
                    print(f"[GATEWAY CORE] Plugin {plugin_name} is disabled")
                    self.logger.info(f"Plugin {plugin_name} is disabled")
                    
            except Exception as e:
                print(f"[GATEWAY CORE] Failed to register plugin {plugin_class.__name__}: {e}")
                import traceback
                print(f"[GATEWAY CORE] Traceback: {traceback.format_exc()}")
                self.logger.error(f"Failed to register plugin {plugin_class.__name__}: {e}")
    
    async def _initialize_protocols(self) -> None:
        """Initialize protocol adapters with dependency injection"""
        try:
            # Prepare dependencies for protocol adapters
            dependencies = {
                'config': self.config,
                'logger': self.logger,
                'gateway': self,
                'key_manager': self.key_manager,
                'auth_manager': self.auth_manager,
                'authz_manager': self.authz_manager,
                'message_router': self.message_router,
                'log_consumer': getattr(self, 'log_consumer', None),  # ZMQ log consumer
                'db_connection': getattr(self, 'db_connection', None)  # Database connection
            }
            
            # Initialize REST adapter for FastAPI integration (no separate server)
            print(f"DEBUG: Full config structure: {list(self.config.config_cache.keys())}")
            print(f"DEBUG: Core config: {self.config.config_cache.get('core', {}).keys()}")
            
            # Use proper configuration access pattern
            core_config = self.config.config_cache.get('core', {})
            api_gateway_config = core_config.get('api_gateway', {})
            rest_config = api_gateway_config.get('rest', {})
            
            print(f"DEBUG: API Gateway config: {api_gateway_config.keys()}")
            print(f"DEBUG: REST config: {rest_config}")
            print(f"DEBUG: Registered adapters: {list(self.protocol_manager.registered_adapters.keys())}")
            
            # Initialize REST adapter for FastAPI integration
            success = await self.protocol_manager.initialize_adapter(
                "rest", 
                rest_config, 
                dependencies
            )
            print(f"DEBUG: REST adapter initialization success: {success}")
            
            # Initialize other enabled protocol adapters
            for protocol_name, protocol_config in self.enabled_protocols.items():
                if protocol_name != "rest" and protocol_config.get("enabled", False):
                    print(f"DEBUG: Initializing protocol adapter: {protocol_name}")
                    success = await self.protocol_manager.initialize_adapter(
                        protocol_name, 
                        protocol_config, 
                        dependencies
                    )
                    print(f"DEBUG: {protocol_name} adapter initialization success: {success}")
                    if not success:
                        self.logger.error(f"Failed to initialize protocol adapter: {protocol_name}")
            
            self.logger.info("Protocol adapters initialized")
            
        except Exception as e:
            self.logger.error(f"Protocol initialization failed: {e}")
            raise
    
    async def _start_protocols(self) -> None:
        """Start all initialized protocol adapters"""
        try:
            print(f"DEBUG: Starting protocol adapters...")
            await self.protocol_manager.start_all()
            print(f"DEBUG: Protocol adapters start_all() completed")
            self.logger.info("Protocol adapters started")
        except Exception as e:
            print(f"DEBUG: Failed to start protocols: {e}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
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
        for plugin_name, plugin in self.loaded_plugins.items():
            try:
                await plugin.shutdown()
                self.logger.info(f"Shutdown plugin: {plugin_name}")
            except Exception as e:
                self.logger.error(f"Error shutting down plugin {plugin_name}: {e}")
    
    def configure_fastapi_app(self, app):
        """Configure FastAPI app with plugin middleware"""
        from fastapi.middleware.cors import CORSMiddleware
        from starlette.middleware.base import BaseHTTPMiddleware
        
        # Get configuration
        config = self.config.config_cache.get('core', {})
        api_gateway_config = config.get('api_gateway', {})
        
        # Configure CORS middleware
        cors_origins = api_gateway_config.get("cors_origins", ["http://localhost:3000", "http://127.0.0.1:3000"])
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"]
        )
        
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
