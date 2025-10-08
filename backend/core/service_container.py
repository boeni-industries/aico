"""
AICO Service Container - Dependency Injection and Lifecycle Management

Provides centralized service registration, dependency resolution, and lifecycle management
following AICO's architectural principles with fail-fast behavior and clear logging.
"""

import asyncio
from typing import Dict, Any, Callable, List, Optional, Set, TypeVar, Type
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger

T = TypeVar('T')

class ServiceState(Enum):
    """Service lifecycle states"""
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class ServiceDefinition:
    """Service registration definition"""
    name: str
    factory: Callable
    dependencies: List[str]
    singleton: bool = True
    auto_start: bool = True
    priority: int = 100  # Lower numbers start first

class ServiceError(Exception):
    """Service container errors"""
    pass

class CircularDependencyError(ServiceError):
    """Circular dependency detected"""
    pass

class ServiceNotFoundError(ServiceError):
    """Service not found in container"""
    pass

class BaseService(ABC):
    """Base class for all services with standardized lifecycle"""
    
    def __init__(self, name: str, container: 'ServiceContainer'):
        self.name = name
        self.container = container
        self.config = container.config.get(f"core.services.{name}", {})
        self.logger = get_logger("backend", f"service.{name}")
        self.state = ServiceState.REGISTERED
        self._dependencies_resolved = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize service resources - called once during startup"""
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Start service operations - called after all dependencies initialized"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop service operations - called during shutdown"""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "healthy": self.state == ServiceState.RUNNING
        }
    
    def require_service(self, service_name: str) -> Any:
        """Get required service from container with clear error handling"""
        try:
            service = self.container.get_service(service_name)
            if service is None:
                raise ServiceNotFoundError(f"Required service '{service_name}' not found for '{self.name}'")
            return service
        except Exception as e:
            self.logger.error(f"Failed to get required service '{service_name}': {e}")
            raise
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value with clear path resolution"""
        return self.container.config.get(key, default)

class ServiceContainer:
    """Central dependency injection container with lifecycle management"""
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        self.logger = get_logger("backend", "core.service_container")
        
        # Service registry
        self._definitions: Dict[str, ServiceDefinition] = {}
        self._instances: Dict[str, Any] = {}
        self._states: Dict[str, ServiceState] = {}
        
        # Lifecycle tracking
        self._startup_order: List[str] = []
        self._shutdown_order: List[str] = []
        self._initializing: Set[str] = set()
        
        self.logger.info("Service container initialized")
    
    def register_service(
        self, 
        name: str, 
        factory: Callable, 
        dependencies: List[str] = None,
        singleton: bool = True,
        auto_start: bool = True,
        priority: int = 100
    ) -> None:
        """Register service with dependency resolution"""
        if name in self._definitions:
            raise ServiceError(f"Service '{name}' already registered")
        
        dependencies = dependencies or []
        
        definition = ServiceDefinition(
            name=name,
            factory=factory,
            dependencies=dependencies,
            singleton=singleton,
            auto_start=auto_start,
            priority=priority
        )
        
        self._definitions[name] = definition
        self._states[name] = ServiceState.REGISTERED
        
        self.logger.info(f"Service registered: {name} (deps: {dependencies}, priority: {priority})")
    
    def register_instance(self, name: str, instance: Any) -> None:
        """Register existing service instance"""
        if name in self._instances:
            raise ServiceError(f"Service instance '{name}' already exists")
        
        self._instances[name] = instance
        self._states[name] = ServiceState.RUNNING
        
        self.logger.info(f"Service instance registered: {name}")
    
    def get_service(self, name: str) -> Any:
        """Get service instance with lazy initialization"""
        # Return existing instance if available
        if name in self._instances:
            return self._instances[name]
        
        # Check if service is registered
        if name not in self._definitions:
            raise ServiceNotFoundError(f"Service '{name}' not registered")
        
        # Prevent circular dependencies during initialization
        if name in self._initializing:
            raise CircularDependencyError(f"Circular dependency detected for service '{name}'")
        
        # Create instance
        return self._create_service_instance(name)
    
    def _create_service_instance(self, name: str) -> Any:
        """Create service instance with dependency resolution"""
        definition = self._definitions[name]
        
        self.logger.debug(f"Creating service instance: {name}")
        self._initializing.add(name)
        self._states[name] = ServiceState.INITIALIZING
        
        try:
            # Resolve dependencies first
            resolved_deps = {}
            for dep_name in definition.dependencies:
                resolved_deps[dep_name] = self.get_service(dep_name)
            
            # Create instance
            if definition.dependencies:
                # Pass dependencies as keyword arguments
                instance = definition.factory(self, **resolved_deps)
            else:
                # No dependencies
                instance = definition.factory(self)
            
            # Store instance if singleton
            if definition.singleton:
                self._instances[name] = instance
            
            self._states[name] = ServiceState.INITIALIZED
            self.logger.info(f"Service instance created: {name}")
            
            return instance
            
        except Exception as e:
            self._states[name] = ServiceState.ERROR
            self.logger.error(f"Failed to create service '{name}': {e}")
            raise ServiceError(f"Service creation failed for '{name}': {e}")
        finally:
            self._initializing.discard(name)
    
    async def start_all(self) -> None:
        """Start all auto-start services in dependency order"""
        self.logger.info("Starting all services...")
        
        # Calculate startup order
        self._calculate_startup_order()
        
        # Initialize and start services
        for service_name in self._startup_order:
            definition = self._definitions[service_name]
            
            if not definition.auto_start:
                self.logger.debug(f"Skipping auto-start disabled service: {service_name}")
                continue
            
            try:
                # Get or create service instance
                self.logger.info(f"🚀 [SERVICE_CONTAINER] Creating service instance: {service_name}")
                service = self.get_service(service_name)
                self.logger.info(f"✅ [SERVICE_CONTAINER] Service instance created: {service_name}")
                
                # Check if service has BaseService methods (duck typing approach)
                has_lifecycle_methods = (
                    hasattr(service, 'initialize') and callable(getattr(service, 'initialize')) and
                    hasattr(service, 'start') and callable(getattr(service, 'start')) and
                    hasattr(service, 'stop') and callable(getattr(service, 'stop')) and
                    hasattr(service, 'state')
                )
                
                # Removed debug print
                
                if has_lifecycle_methods:
                    self.logger.info(f"🔧 [SERVICE_CONTAINER] Initializing service: {service_name}")
                    # Initialize service
                    if service.state == ServiceState.INITIALIZED:
                        service.state = ServiceState.STARTING
                        self.logger.info(f"🚀 [SERVICE_CONTAINER] Starting service: {service_name}")
                        await service.start()
                        self.logger.info(f"✅ [SERVICE_CONTAINER] Service started: {service_name}")
                    else:
                        # Service needs initialization first
                        await service.initialize()
                        service.state = ServiceState.STARTING
                        self.logger.info(f"🚀 [SERVICE_CONTAINER] Starting service: {service_name}")
                        await service.start()
                        self.logger.info(f"✅ [SERVICE_CONTAINER] Service started: {service_name}")
                else:
                    # Service has no start() method
                    self.logger.info(f"⚠️ [SERVICE_CONTAINER] Service {service_name} has no lifecycle methods")
                    pass
                
                self._states[service_name] = ServiceState.RUNNING
                self.logger.info(f"Service started: {service_name}")
                
            except Exception as e:
                self._states[service_name] = ServiceState.ERROR
                self.logger.error(f"Failed to start service '{service_name}': {e}")
                raise ServiceError(f"Service startup failed for '{service_name}': {e}")
        
        self.logger.info(f"All services started successfully ({len(self._startup_order)} services)")
    
    async def stop_all(self) -> None:
        """Stop all services in reverse dependency order"""
        self.logger.info("Stopping all services...")
        
        # Stop in reverse order
        for service_name in reversed(self._shutdown_order):
            if service_name not in self._instances:
                continue
            
            try:
                service = self._instances[service_name]
                
                if isinstance(service, BaseService):
                    if service.state == ServiceState.RUNNING:
                        self.logger.debug(f"Stopping service: {service_name}")
                        service.state = ServiceState.STOPPING
                        await service.stop()
                        service.state = ServiceState.STOPPED
                
                self._states[service_name] = ServiceState.STOPPED
                self.logger.info(f"Service stopped: {service_name}")
                
            except Exception as e:
                self.logger.error(f"Error stopping service '{service_name}': {e}")
                # Continue stopping other services
        
        self.logger.info("All services stopped")
    
    def _calculate_startup_order(self) -> None:
        """Calculate service startup order based on dependencies and priorities"""
        # Topological sort with priority ordering
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(name: str):
            if name in temp_visited:
                raise CircularDependencyError(f"Circular dependency detected involving '{name}'")
            if name in visited:
                return
            
            temp_visited.add(name)
            
            # Visit dependencies first
            if name in self._definitions:
                for dep in self._definitions[name].dependencies:
                    visit(dep)
            
            temp_visited.remove(name)
            visited.add(name)
            order.append(name)
        
        # Visit all registered services
        for service_name in self._definitions:
            visit(service_name)
        
        # Sort by priority within dependency constraints
        # Services with same dependency level are sorted by priority
        self._startup_order = sorted(order, key=lambda name: self._definitions[name].priority)
        self._shutdown_order = self._startup_order.copy()
        
        self.logger.debug(f"Service startup order: {self._startup_order}")
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services"""
        status = {
            "total_services": len(self._definitions),
            "running_services": sum(1 for state in self._states.values() if state == ServiceState.RUNNING),
            "services": {}
        }
        
        for name, state in self._states.items():
            status["services"][name] = {
                "state": state.value,
                "dependencies": self._definitions.get(name, ServiceDefinition("", None, [])).dependencies
            }
        
        return status
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of all services"""
        health_status = {
            "container": "healthy",
            "services": {},
            "summary": {
                "total": len(self._instances),
                "healthy": 0,
                "unhealthy": 0
            }
        }
        
        for name, instance in self._instances.items():
            try:
                if isinstance(instance, BaseService):
                    service_health = await instance.health_check()
                else:
                    # Basic health check for non-BaseService instances
                    service_health = {
                        "name": name,
                        "state": self._states.get(name, ServiceState.REGISTERED).value,
                        "healthy": self._states.get(name) == ServiceState.RUNNING
                    }
                
                health_status["services"][name] = service_health
                
                if service_health.get("healthy", False):
                    health_status["summary"]["healthy"] += 1
                else:
                    health_status["summary"]["unhealthy"] += 1
                    
            except Exception as e:
                health_status["services"][name] = {
                    "name": name,
                    "healthy": False,
                    "error": str(e)
                }
                health_status["summary"]["unhealthy"] += 1
        
        # Overall container health
        if health_status["summary"]["unhealthy"] > 0:
            health_status["container"] = "degraded"
        
        return health_status
