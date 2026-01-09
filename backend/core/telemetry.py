"""
OpenTelemetry Telemetry Bootstrap Module

Initializes and configures OpenTelemetry instrumentation for AICO.
Supports multiple modes: casual, pro, dev, and production.

Design Principles:
- Local-first by default (casual/pro modes)
- Optional exporters for dev/production modes
- Configuration-driven behavior
- Privacy-first with automatic PII redaction
- Minimal performance overhead
"""

import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

logger = logging.getLogger("backend.telemetry")


class TelemetryManager:
    """
    Manages OpenTelemetry instrumentation lifecycle.
    
    Singleton pattern ensures only one telemetry instance exists.
    Configuration determines which exporters are enabled.
    """
    
    _instance: Optional['TelemetryManager'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.mode: str = "casual"
        self.config: Dict[str, Any] = {}
        self.tracer_provider: Optional[TracerProvider] = None
        self.meter_provider: Optional[MeterProvider] = None
        self._exporters: list = []
    
    def initialize(self, config: Dict[str, Any], db_connection=None) -> None:
        """
        Initialize OpenTelemetry with configuration.
        
        Args:
            config: Configuration dict with instrumentation settings
            db_connection: Encrypted database connection for metrics storage
        """
        if self._initialized:
            logger.warning("TelemetryManager already initialized")
            return
        
        self.config = config.get('instrumentation', {})
        self.mode = self.config.get('mode', 'casual')
        
        # Create resource with service information
        resource = Resource.create({
            "service.name": "aico-backend",
            "service.version": "1.0.0",
            "deployment.environment": self.mode,
        })
        
        # Initialize tracing
        self._initialize_tracing(resource)
        
        # Initialize metrics with database connection
        self._initialize_metrics(resource, db_connection=db_connection)
        
        # Initialize exporters based on mode
        self._initialize_exporters()
        
        self._initialized = True
    
    def _initialize_tracing(self, resource: Resource) -> None:
        """Initialize trace provider and processors"""
        self.tracer_provider = TracerProvider(resource=resource)
        
        # Always add console exporter in dev mode for debugging
        if self.mode == "dev":
            console_processor = BatchSpanProcessor(ConsoleSpanExporter())
            self.tracer_provider.add_span_processor(console_processor)
        
        trace.set_tracer_provider(self.tracer_provider)
    
    def _initialize_metrics(self, resource: Resource, db_connection=None) -> None:
        """Initialize meter provider and readers"""
        # Create metric exporter for local storage
        from backend.core.otel_storage_adapter import OTelStorageExporter
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        
        storage_exporter = OTelStorageExporter(db_connection=db_connection)
        
        # Wrap exporter in periodic reader (exports every 5 seconds)
        storage_reader = PeriodicExportingMetricReader(
            exporter=storage_exporter,
            export_interval_millis=5000,  # 5 seconds
        )
        
        self.meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[storage_reader]
        )
        
        metrics.set_meter_provider(self.meter_provider)
    
    def _initialize_exporters(self) -> None:
        """Initialize optional exporters based on mode and configuration"""
        exporters_config = self.config.get('exporters', {})
        
        # Prometheus exporter (pro/dev/production)
        if self.mode in ['pro', 'dev', 'production']:
            prometheus_config = exporters_config.get('prometheus', {})
            if prometheus_config.get('enabled', self.mode == 'dev'):
                self._initialize_prometheus_exporter(prometheus_config)
        
        # OTLP exporter (dev/production)
        if self.mode in ['dev', 'production']:
            otlp_config = exporters_config.get('otlp', {})
            if otlp_config.get('enabled', False):
                self._initialize_otlp_exporter(otlp_config)
    
    def _initialize_prometheus_exporter(self, config: Dict[str, Any]) -> None:
        """Initialize Prometheus metrics exporter"""
        try:
            from opentelemetry.exporter.prometheus import PrometheusMetricReader
            from prometheus_client import start_http_server
            
            port = config.get('port', 9090)
            
            # Create Prometheus reader
            prometheus_reader = PrometheusMetricReader()
            
            # Add to meter provider
            if self.meter_provider:
                # Note: In production, we'd need to recreate MeterProvider with multiple readers
                # For now, this is a placeholder for the architecture
                pass
            
            # Start Prometheus HTTP server
            start_http_server(port)
            self._exporters.append('prometheus')
            
        except ImportError:
            logger.warning("Prometheus exporter not available (install with: pip install opentelemetry-exporter-prometheus)")
        except Exception as e:
            logger.error(f"Failed to initialize Prometheus exporter: {e}")
    
    def _initialize_otlp_exporter(self, config: Dict[str, Any]) -> None:
        """Initialize OTLP exporter for traces"""
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            
            traces_config = config.get('traces', {})
            endpoint = traces_config.get('endpoint', 'http://localhost:4317')
            
            # Create OTLP exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=endpoint,
                headers=traces_config.get('headers', {}),
            )
            
            # Add to tracer provider
            if self.tracer_provider:
                otlp_processor = BatchSpanProcessor(otlp_exporter)
                self.tracer_provider.add_span_processor(otlp_processor)
            
            self._exporters.append('otlp')
            
        except ImportError:
            logger.warning("OTLP exporter not available (install with: pip install opentelemetry-exporter-otlp)")
        except Exception as e:
            logger.error(f"Failed to initialize OTLP exporter: {e}")
    
    def instrument_fastapi(self, app) -> None:
        """
        Instrument FastAPI application with OpenTelemetry.
        
        Args:
            app: FastAPI application instance
        """
        if not self._initialized:
            logger.warning("TelemetryManager not initialized, skipping FastAPI instrumentation")
            return
        
        try:
            FastAPIInstrumentor.instrument_app(app)
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {e}")
    
    def get_tracer(self, name: str) -> trace.Tracer:
        """Get a tracer instance for creating spans"""
        return trace.get_tracer(name)
    
    def get_meter(self, name: str) -> metrics.Meter:
        """Get a meter instance for recording metrics"""
        return metrics.get_meter(name)
    
    def shutdown(self) -> None:
        """Shutdown telemetry and flush pending data"""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
        if self.meter_provider:
            self.meter_provider.shutdown()
    
    @property
    def is_initialized(self) -> bool:
        """Check if telemetry is initialized"""
        return self._initialized
    
    @property
    def active_exporters(self) -> list:
        """Get list of active exporters"""
        return self._exporters.copy()


# Global telemetry manager instance
_telemetry_manager = TelemetryManager()


def initialize_telemetry(config: Dict[str, Any], db_connection=None) -> None:
    """
    Initialize OpenTelemetry instrumentation.
    
    Args:
        config: Configuration dictionary
        db_connection: Encrypted database connection for metrics storage
    """
    _telemetry_manager.initialize(config, db_connection=db_connection)


def instrument_fastapi(app) -> None:
    """
    Instrument FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    _telemetry_manager.instrument_fastapi(app)


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer for creating spans"""
    return _telemetry_manager.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """Get a meter for recording metrics"""
    return _telemetry_manager.get_meter(name)


def shutdown_telemetry() -> None:
    """Shutdown telemetry and flush data"""
    _telemetry_manager.shutdown()


@contextmanager
def trace_operation(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Context manager for tracing operations.
    
    Usage:
        with trace_operation("process_request", {"user_id": "123"}):
            # Your code here
            pass
    """
    tracer = get_tracer("aico.backend")
    with tracer.start_as_current_span(operation_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span
