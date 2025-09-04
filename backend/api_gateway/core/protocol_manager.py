"""
Protocol Adapter Manager for AICO API Gateway

Manages protocol adapter lifecycle, initialization, and coordination
with dependency injection and configuration-driven setup.
"""

import asyncio
from typing import Dict, List, Optional, Any, Type
from abc import ABC, abstractmethod

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager


class ProtocolAdapter(ABC):
    """Base interface for protocol adapters"""
    
    def __init__(self, config: Dict[str, Any], dependencies: Dict[str, Any]):
        self.config = config
        self.dependencies = dependencies
        self.logger = dependencies.get('logger', get_logger("api_gateway", "protocol"))
        self.running = False
    
    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """Protocol name identifier"""
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Start the protocol adapter"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the protocol adapter"""
        pass
    
    @abstractmethod
    async def handle_request(self, request_data: Any, client_info: Dict[str, Any]) -> Any:
        """Handle protocol-specific request"""
        pass
    
    def is_running(self) -> bool:
        """Check if adapter is running"""
        return self.running


class ProtocolAdapterManager:
    """
    Manages protocol adapter lifecycle and coordination
    
    Handles adapter registration, initialization with dependency injection,
    startup/shutdown coordination, and request routing.
    """
    
    def __init__(self, config: Dict[str, Any], logger=None):
        self.logger = logger if logger else get_logger("api_gateway", "protocol_manager")
        self.config = config
        self.registered_adapters: Dict[str, Type[ProtocolAdapter]] = {}
        self.active_adapters: Dict[str, ProtocolAdapter] = {}
        self.adapter_configs: Dict[str, Dict[str, Any]] = {}
        self.adapter_tasks: Dict[str, asyncio.Task] = {}  # Store background tasks
        
        # Register built-in adapters
        self._register_builtin_adapters()
        
        self.logger.info("Protocol adapter manager initialized")
    
    def _register_builtin_adapters(self) -> None:
        """Register built-in protocol adapters"""
        # REST endpoints handled by main FastAPI backend - no adapter needed
        from ..adapters.websocket_adapter import WebSocketAdapter
        from ..adapters.rest_adapter import RESTAdapter
        self.registered_adapters["rest"] = RESTAdapter
        self.registered_adapters["websocket"] = WebSocketAdapter
    
    def register_adapter(self, name: str, adapter_class: Type[ProtocolAdapter]) -> None:
        """Register a protocol adapter class"""
        if not issubclass(adapter_class, ProtocolAdapter):
            raise ValueError(f"Adapter {name} must implement ProtocolAdapter interface")
        
        self.registered_adapters[name] = adapter_class
        self.logger.debug(f"Registered protocol adapter: {name}")
    
    async def initialize_adapter(self, name: str, config: Dict[str, Any], 
                                dependencies: Dict[str, Any]) -> bool:
        """Initialize a protocol adapter with dependency injection"""
        try:
            if name not in self.registered_adapters:
                self.logger.error(f"Protocol adapter not registered: {name}")
                return False
            
            # Create adapter instance with positional arguments based on adapter type
            adapter_class = self.registered_adapters[name]
            
            if name == "websocket":
                adapter = adapter_class(
                    config,
                    dependencies.get('auth_manager'),
                    dependencies.get('authz_manager'), 
                    dependencies.get('message_router'),
                    dependencies.get('rate_limiter'),
                    dependencies.get('validator')
                )
            elif name == "zeromq_ipc":
                adapter = adapter_class(
                    config,
                    dependencies.get('auth_manager'),
                    dependencies.get('authz_manager'),
                    dependencies.get('message_router'),
                    dependencies.get('adaptive_transport')
                )
            else:
                # Fallback for other adapters
                adapter = adapter_class(config, dependencies)
            
            # Protocol adapters don't have initialize method - they're initialized in constructor
            
            # Store configuration and adapter
            self.adapter_configs[name] = config
            self.active_adapters[name] = adapter
            
            self.logger.info(f"Initialized protocol adapter: {name}")
            return True
            
        except Exception as e:
            print(f"PROTOCOL_MANAGER ERROR: Failed to initialize adapter {name}: {e}")
            import traceback
            traceback.print_exc()
            self.logger.error(f"Failed to initialize adapter {name}: {e}", exc_info=True)
            return False
    
    async def start_adapter(self, name: str) -> bool:
        """Start a specific protocol adapter"""
        try:
            adapter = self.active_adapters.get(name)
            if not adapter:
                #print(f"DEBUG: Adapter not found in active_adapters: {name}")
                #print(f"DEBUG: Available adapters: {list(self.active_adapters.keys())}")
                self.logger.error(f"Adapter not initialized: {name}")
                return False
            
            #print(f"DEBUG: Calling start() on {name} adapter")
            
            # Handle adapter-specific start parameters
            if name == "websocket":
                # WebSocket adapter requires host parameter
                host = self.adapter_configs[name].get("host", "127.0.0.1")
                await adapter.start(host)
            else:
                # Other adapters use parameterless start()
                await adapter.start()
                
            #print(f"DEBUG: {name} adapter start() completed")
            
            # For adapters that create background tasks, store them to keep alive
            if hasattr(adapter, 'server') and adapter.server:
                # WebSocket adapter - keep server alive
                self.adapter_tasks[name] = asyncio.create_task(adapter.server.wait_closed())
                #print(f"DEBUG: Created task to keep {name} server alive")
            elif hasattr(adapter, 'message_task') and adapter.message_task:
                # ZeroMQ adapter - keep message task alive
                self.adapter_tasks[name] = adapter.message_task
                #print(f"DEBUG: Stored {name} message task to keep alive")
            
            self.logger.info(f"Started protocol adapter: {name}")
            return True
            
        except Exception as e:
            #print(f"DEBUG: Failed to start adapter {name}: {e}")
            import traceback
            #print(f"DEBUG: Traceback: {traceback.format_exc()}")
            self.logger.error(f"Failed to start adapter {name}: {e}")
            return False
    
    async def stop_adapter(self, name: str) -> bool:
        """Stop a specific protocol adapter"""
        try:
            adapter = self.active_adapters.get(name)
            if not adapter:
                return True  # Already stopped
            
            # Cancel background task if exists
            if name in self.adapter_tasks:
                task = self.adapter_tasks[name]
                if not task.done():
                    self.logger.info(f"Cancelling background task for adapter: {name}")
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=3.0)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass
                del self.adapter_tasks[name]
            
            await adapter.stop()
            self.logger.info(f"Stopped protocol adapter: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop adapter {name}: {e}")
            return False
    
    async def start_all(self) -> None:
        """Start all initialized adapters"""
        for name in self.active_adapters.keys():
            await self.start_adapter(name)
    
    async def stop_all(self) -> None:
        """Stop all active protocol adapters"""
        # Cancel all background tasks first
        cancel_tasks = []
        for name, task in self.adapter_tasks.items():
            if not task.done():
                self.logger.info(f"Cancelling background task for adapter: {name}")
                task.cancel()
                cancel_tasks.append(task)
        
        # Wait for all tasks to be cancelled
        if cancel_tasks:
            try:
                await asyncio.wait_for(asyncio.gather(*cancel_tasks, return_exceptions=True), timeout=5.0)
            except asyncio.TimeoutError:
                self.logger.warning("Some adapter tasks did not cancel within timeout")
        
        self.adapter_tasks.clear()
        
        # Now stop the adapters themselves
        for name in list(self.active_adapters.keys()):
            await self.stop_adapter(name)
        self.active_adapters.clear()
        self.logger.info("All protocol adapters stopped")
    
    def get_adapter(self, name: str) -> Optional[ProtocolAdapter]:
        """Get an active adapter by name"""
        return self.active_adapters.get(name)
    
    def get_active_protocols(self) -> List[str]:
        """Get list of active protocol names"""
        return [name for name, adapter in self.active_adapters.items() 
                if adapter.is_running()]
    
    def get_adapter_stats(self) -> Dict[str, Any]:
        """Get adapter manager statistics"""
        return {
            "registered_adapters": len(self.registered_adapters),
            "active_adapters": len(self.active_adapters),
            "running_adapters": len(self.get_active_protocols()),
            "adapter_names": list(self.active_adapters.keys())
        }
