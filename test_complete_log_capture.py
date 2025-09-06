#!/usr/bin/env python3
"""
Test script to verify complete log capture during modelservice startup
"""
import sys
import asyncio
import time
sys.path.insert(0, '.')

# Fix Windows event loop for ZMQ
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test_complete_log_capture():
    print('=== Testing Complete Modelservice Log Capture ===')
    
    # Initialize logging and get initial state
    from aico.core.config import ConfigurationManager
    from aico.core.logging import initialize_logging, get_logger, _logger_factory
    
    config_manager = ConfigurationManager()
    config_manager.initialize()
    initialize_logging(config_manager)
    
    print(f'Initial buffer size: {len(_logger_factory._log_buffer._buffer) if _logger_factory and _logger_factory._log_buffer else 0}')
    
    # Simulate the exact modelservice startup sequence
    logger = get_logger("modelservice", "main")
    
    # Phase 1: Early startup logs (should be buffered)
    print('\n--- Phase 1: Early Startup (Pre-ZMQ) ---')
    logger.info("AICO Modelservice starting up")
    logger.info("Server configuration - Communication: ZMQ, Environment: development, Version: v0.0.2, Encryption: CurveZMQ")
    logger.info("Backend confirmed available at startup")
    logger.info("Starting ZMQ service early for log capture")
    
    buffer_after_early = len(_logger_factory._log_buffer._buffer) if _logger_factory and _logger_factory._log_buffer else 0
    print(f'Buffer size after early startup logs: {buffer_after_early}')
    
    # Phase 2: ZMQ startup logs (should be buffered)
    print('\n--- Phase 2: ZMQ Service Startup ---')
    zmq_logger = get_logger("modelservice", "zmq_service")
    zmq_logger.info("Starting modelservice ZMQ service (early mode)...")
    zmq_logger.info("Subscribed to topic (early): modelservice/health/request")
    zmq_logger.info("Modelservice ZMQ service started (early mode)")
    zmq_logger.info("Ollama manager injected into ZMQ service")
    
    buffer_after_zmq = len(_logger_factory._log_buffer._buffer) if _logger_factory and _logger_factory._log_buffer else 0
    print(f'Buffer size after ZMQ startup logs: {buffer_after_zmq}')
    
    # Phase 3: Simulate ZMQ transport becoming ready
    print('\n--- Phase 3: ZMQ Transport Ready ---')
    if _logger_factory and _logger_factory._transport:
        _logger_factory._transport.mark_broker_ready()
        await asyncio.sleep(0.2)  # Wait for connection
        
        # Check if client connected
        client = getattr(_logger_factory._transport, '_message_bus_client', None)
        connected = client and getattr(client, 'connected', False)
        print(f'ZMQ client connected: {connected}')
        
        # Flush buffer
        if hasattr(_logger_factory, '_log_buffer'):
            buffer_size = len(_logger_factory._log_buffer._buffer)
            print(f'Flushing {buffer_size} buffered logs...')
            _logger_factory._log_buffer.flush_to_transport(_logger_factory._transport)
            
        buffer_after_flush = len(_logger_factory._log_buffer._buffer) if _logger_factory and _logger_factory._log_buffer else 0
        print(f'Buffer size after flush: {buffer_after_flush}')
    
    # Phase 4: Post-ZMQ logs (should go direct to ZMQ)
    print('\n--- Phase 4: Post-ZMQ Logs (Direct Transport) ---')
    logger.info("ZMQ logging transport initialized and ready")
    logger.info("Starting Ollama initialization")
    logger.info("Ollama binary installation verified")
    logger.info("Ollama server started successfully")
    logger.info("Ollama v0.11.8 ready at http://127.0.0.1:11434")
    logger.info("Started 1 model(s): hermes3:8b")
    
    final_buffer_size = len(_logger_factory._log_buffer._buffer) if _logger_factory and _logger_factory._log_buffer else 0
    print(f'Final buffer size: {final_buffer_size}')
    
    # Summary
    print('\n=== Log Capture Summary ===')
    print(f'Early startup logs captured: {buffer_after_early > 0}')
    print(f'ZMQ startup logs captured: {buffer_after_zmq > buffer_after_early}')
    print(f'Buffer successfully flushed: {buffer_after_flush == 0}')
    print(f'Post-ZMQ logs bypass buffer: {final_buffer_size == 0}')
    
    total_logs_captured = buffer_after_zmq  # Total logs that went through buffer
    print(f'Total startup logs captured and persisted: {total_logs_captured}')

if __name__ == "__main__":
    asyncio.run(test_complete_log_capture())
