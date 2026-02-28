"""
Modelservice main application entry point - NATS Message Bus Implementation.

This module implements a pure NATS message bus service.
"""

import sys
import os
import asyncio
import signal
import warnings
from pathlib import Path

# Disable tokenizers parallelism to avoid fork issues
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Suppress harmless SyntaxWarnings from third-party dependencies (Python 3.13)
# These are from jsonlines, pysbd (used by Coqui TTS) - not our code
warnings.filterwarnings('ignore', category=SyntaxWarning)

# Fix Windows asyncio event loop compatibility
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Initialize configuration before any imports that get loggers
from aico.core.config import ConfigurationManager
from aico.core.config_validation import validate_startup_config, print_config_summary
from aico.core.logging import get_logger
from aico.core.fs_guard import enable_fs_guard
config_manager = ConfigurationManager()
# Use lightweight initialization in modelservice to avoid starting file watchers.
# IMPORTANT: This means modelservice no longer hot-reloads configuration files.
# Any changes under /config that should affect modelservice now require a
# modelservice restart to take effect. This avoids macOS FSEvents
# "already scheduled" errors when multiple processes watch the same
# config directory.
config_manager.initialize(lightweight=True)
# Logging will be initialized service-specifically in initialize_modelservice()
from aico.core.version import get_modelservice_version
from .core.nats_service import ModelserviceNATSService

# Get version from VERSIONS file
__version__ = get_modelservice_version()

# Logger will be initialized after logging setup in initialize_modelservice()

# Global service instance for signal handling
_service = None

# Track service start time for uptime calculation
import time
_start_time = time.time()


async def initialize_modelservice():
    """Initialize modelservice and return configuration."""
    # CRITICAL: Validate configuration before proceeding.
    # Validate the already-initialized global config manager to avoid starting file
    # watchers (and to avoid validating a different initialization mode).
    cfg = config_manager
    try:
        validate_startup_config(cfg, service="modelservice", fail_fast=True)
        print_config_summary(cfg)
    except Exception as e:
        print(f"❌ FATAL: Configuration validation failed: {e}")
        print("Modelservice cannot start with invalid configuration.")
        raise SystemExit(1)
    
    # Initialize service-specific logging first to capture all subsequent logs
    from aico.core.logging import initialize_logging
    initialize_logging(service_name="modelservice", enable_loki=True, enable_console=True)

    enable_fs_guard()
    
    # Now we can get a logger
    logger = get_logger("modelservice.main")
    
    # Get modelservice config from new domain structure
    # NOTE: Config is validated at startup - if missing, startup fails
    modelservice_config = cfg.get("modelservice", {})
    env = os.getenv("AICO_ENV", "development")

    # Startup: Display initial info and use standard AICO logging
    startup_msg = "\n" + "=" * 60 + "\n[*] AICO Modelservice (NATS)\n" + "=" * 60
    print(startup_msg)
    logger.info("AICO Modelservice starting up")
    
    server_info = f"[>] Communication: NATS Message Bus\n[>] Environment: {env}\n[>] Version: v{__version__}"
    print(server_info)
    logger.info(f"Server configuration - Communication: NATS, Environment: {env}, Version: {__version__}")
    
    print("=" * 60)
    
    # Check if backend is running before starting NATS service
    print("🔍 Checking backend availability...")
    backend_available = await _check_backend_health(cfg)
    if not backend_available:
        print("⚠️  Backend not available - logs will use fallback storage")
        logger.warning("Backend not available at startup - using fallback logging")
    else:
        print("✅ Backend is available")
        logger.info("Backend confirmed available at startup")
    
    # Initialize NATS service EARLY to capture all subsequent logs
    print("🔌 Starting NATS service...")
    logger.info("Starting NATS service early for message handling")
    
    service = ModelserviceNATSService(cfg, None)
    await service.start_early()
    
    # Initialize InfluxDB metrics exporter (honor instrumentation flag)
    instrumentation_config = cfg.get("instrumentation", {})
    if instrumentation_config.get("enabled", False):
        print("📊 Initializing InfluxDB metrics exporter...")
        logger.info("Initializing InfluxDB metrics exporter (instrumentation enabled)")
        try:
            from opentelemetry import metrics as otel_metrics
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
            from opentelemetry.sdk.resources import Resource
            from backend.core.otel_influx_exporter import OTelInfluxExporter
            import socket
            
            # Get InfluxDB config
            influx_config = cfg.get("influx", {})
            influx_url = influx_config.get("url", "http://127.0.0.1:8086")
            influx_org = influx_config.get("org", "aico")
            influx_bucket = influx_config.get("bucket", "aico_telemetry")
            
            # Retrieve token from keyring
            influx_token = None
            try:
                from aico.security.key_manager import AICOKeyManager
                
                # Use the global config_manager (already initialized at module level)
                key_manager = AICOKeyManager(config_manager)
                influx_token = os.getenv("AICO_INFLUX_ADMIN_TOKEN") or key_manager.get_database_password(
                    "influx", username="admin_token"
                )
                
                if not influx_token:
                    logger.warning("InfluxDB token not found in keyring; metrics may not be exported. Run 'aico deploy influx' to set up credentials.")
            except Exception as e:
                logger.warning(f"Failed to retrieve InfluxDB token from keyring: {e}")
                influx_token = None

            if not influx_token:
                print("⏹️  No InfluxDB token configured; skipping metrics exporter")
                logger.warning("No InfluxDB token configured; skipping modelservice metrics exporter")
                raise RuntimeError("InfluxDB token not configured")
            
            # Create resource for modelservice
            resource = Resource.create({
                "service.name": "modelservice",
                "service.version": __version__,
                "deployment.environment": instrumentation_config.get("mode", "casual"),
                "host.name": socket.gethostname(),
            })
            
            # Create InfluxDB exporter
            influx_exporter = OTelInfluxExporter(
                influx_url=influx_url,
                org=influx_org,
                bucket=influx_bucket,
                token=influx_token,
                resource_attributes=dict(resource.attributes),
            )
            
            # Wrap exporter in periodic reader (exports every 60 seconds, matching backend)
            influx_reader = PeriodicExportingMetricReader(
                exporter=influx_exporter,
                export_interval_millis=60000,  # 60 seconds (as per schema.lp)
            )
            
            # Create and set meter provider
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[influx_reader]
            )
            otel_metrics.set_meter_provider(meter_provider)
            
            print("✅ InfluxDB metrics exporter ready")
            logger.info("InfluxDB metrics exporter initialized successfully")
        except Exception as e:
            print(f"⚠️  Metrics initialization failed: {e}")
            logger.warning(f"Metrics initialization failed: {e}")
    else:
        print("⏹️  Instrumentation disabled in config; skipping metrics setup")
        logger.info("Instrumentation disabled in config; skipping modelservice metrics initialization")
    
    # Logs now go directly to InfluxDB
    logger.info("Modelservice logging initialized with InfluxDB")
    
    # Initialize process management for graceful shutdown
    process_manager = None
    if os.getenv("AICO_DETACH_MODE") == "true":
        from aico.core.process import ProcessManager
        process_manager = ProcessManager("modelservice")
        process_manager.write_pid(os.getpid())
    
    # vLLM is now deployed separately via 'aico vllm' CLI commands
    
    # Initialize and preload TransformersManager
    from .core.transformers_manager import TransformersManager
    transformers_manager = TransformersManager(cfg)
    
    # Initialize models (download + preload into memory)
    await transformers_manager.initialize_models()
    
    # Inject the preloaded TransformersManager into service
    service.set_transformers_manager(transformers_manager)
    
    # Initialize TTS system (blocking - must complete before service is ready)
    print("🎤 Initializing TTS system...")
    print("⏳ First run will download ~1.8GB model from HuggingFace...")
    logger.info("Starting TTS system initialization")
    
    try:
        await service.handlers.initialize_tts_system()
        print("✅ TTS system ready")
        logger.info("TTS system initialized successfully")
    except Exception as e:
        print(f"\n❌ FATAL: TTS initialization failed: {e}")
        logger.error(f"TTS initialization failed: {e}")
        print("\nModelservice cannot start without TTS support.")
        print("Please check:")
        print("  - Internet connection (for model download)")
        print("  - Disk space (~2GB required)")
        print("  - HuggingFace access")
        raise SystemExit(1)
    
    print("=" * 60)
    print("[+] NATS service ready... (Press Ctrl+C to stop)\n")
    logger.info("Modelservice startup complete, NATS service ready")

    # Logging will be handled after full NATS service initialization in main()

    return cfg, None, process_manager, service


async def _check_backend_health(cfg: ConfigurationManager) -> bool:
    """Check if the backend is running and accessible."""
    try:
        import httpx
        
        # Get backend configuration
        host = cfg.get("api_gateway.rest.host", "localhost")
        port = cfg.get("api_gateway.rest.port", 8771)
        
        # Try to connect to backend health endpoint
        async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
            response = await client.get(f"http://{host}:{port}/api/v1/health/")
            return response.status_code == 200
            
    except Exception as e:
        return False


async def shutdown_modelservice(ollama_manager, process_manager):
    """Gracefully shutdown modelservice."""
    # Get logger safely
    try:
        logger = get_logger("modelservice.main")
    except:
        logger = None
    
    print("\n[-] Graceful shutdown initiated...")
    if logger:
        logger.info("Graceful shutdown initiated")
    
    # Signal global shutdown to semantic memory components (if any)
    try:
        from aico.ai.memory.request_queue import _set_global_shutdown
        _set_global_shutdown()
        if logger:
            logger.info("Global shutdown signal sent to semantic memory components")
    except ImportError:
        # Semantic memory not available in modelservice, that's OK
        pass
    
    print("[~] Stopping services...")
    if logger:
        logger.info("Stopping services")
    
    # Stop Ollama gracefully
    try:
        await ollama_manager.stop_ollama()
        print("[+] Ollama stopped")
        if logger:
            logger.info("Ollama stopped successfully")
    except Exception as e:
        print(f"[!] Error stopping Ollama: {e}")
        if logger:
            logger.error(f"Error stopping Ollama: {e}")
        
    if process_manager:
        process_manager.cleanup_pid_files()
    print("[+] Shutdown complete.")
    if logger:
        logger.info("Shutdown complete")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    # Get logger (it should be initialized by now)
    try:
        logger = get_logger("modelservice.main")
        logger.info(f"Received signal {signum}, initiating shutdown")
    except:
        print(f"Received signal {signum}, initiating shutdown")
    global _service
    if _service is not None:
        try:
            asyncio.create_task(_service.stop())
        except RuntimeError:
            # No running loop in this thread/context
            pass


async def main():
    """Main entry point for the modelservice NATS service."""
    global _service
    
    # Initialize these to None so they're always defined for cleanup
    ollama_manager = None
    process_manager = None
    
    try:
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Initialize modelservice and Ollama (service started early)
        config, ollama_manager, process_manager, _service = await initialize_modelservice()
        
        # Complete the full service initialization (subscribe to all topics)
        await _service.start()
        
        # Logs now go directly to InfluxDB
        
        # Keep the service running (both foreground and background modes)
        # Entering service loop
        while _service and _service.running:
            await asyncio.sleep(1.0)
        # Service loop ended
        
    except KeyboardInterrupt:
        try:
            logger = get_logger("modelservice.main")
            logger.info("Received keyboard interrupt")
        except:
            print("Received keyboard interrupt")
    except Exception as e:
        try:
            logger = get_logger("modelservice.main")
            logger.error(f"Modelservice error: {str(e)}")
        except:
            print(f"Modelservice error: {str(e)}")
        raise
    finally:
        # Cleanup - ollama_manager and process_manager are always defined (may be None)
        if _service:
            await _service.stop()
        if ollama_manager is not None:
            await shutdown_modelservice(ollama_manager, process_manager)


def run_main():
    """Synchronous wrapper for the async main function."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        try:
            logger = get_logger("modelservice.main")
            logger.info("Modelservice stopped by user")
        except:
            print("Modelservice stopped by user")
    except Exception as e:
        try:
            logger = get_logger("modelservice.main")
            logger.error(f"Fatal error: {str(e)}")
        except:
            print(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run_main()