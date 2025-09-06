#!/usr/bin/env python3
"""
Test script to verify AICO logging buffer workflow
"""
import sys
import asyncio
sys.path.insert(0, '.')

# Fix Windows event loop for ZMQ
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test_buffering_workflow():
    print('=== Testing AICO Logging Buffer Workflow ===')
    
    # Step 1: Initialize logging WITHOUT ZMQ ready
    from aico.core.config import ConfigurationManager
    from aico.core.logging import initialize_logging, get_logger, _logger_factory
    
    config_manager = ConfigurationManager()
    config_manager.initialize()
    initialize_logging(config_manager)
    
    print(f'Logger factory created: {_logger_factory is not None}')
    print(f'Transport exists: {_logger_factory._transport is not None if _logger_factory else False}')
    print(f'Buffer exists: {_logger_factory._log_buffer is not None if _logger_factory else False}')
    print(f'Initial buffer size: {len(_logger_factory._log_buffer._buffer) if _logger_factory and _logger_factory._log_buffer else 0}')
    
    # Check transport readiness BEFORE marking ready
    if _logger_factory and _logger_factory._transport:
        transport = _logger_factory._transport
        broker_available = getattr(transport, '_broker_available', False)
        client_connected = getattr(transport, '_message_bus_client', None) and getattr(transport._message_bus_client, 'connected', False)
        print(f'Transport broker_available: {broker_available}')
        print(f'Transport client_connected: {client_connected}')
        print(f'Transport ready check: {broker_available and client_connected}')
    
    # Step 2: Create logger and log BEFORE ZMQ is ready
    logger = get_logger('test', 'buffering')
    print('\n--- Logging BEFORE ZMQ ready ---')
    logger.info('Test log 1 - should be buffered')
    logger.warning('Test log 2 - should be buffered') 
    logger.error('Test log 3 - should be buffered')
    
    buffer_size_after_logs = len(_logger_factory._log_buffer._buffer) if _logger_factory and _logger_factory._log_buffer else 0
    print(f'Buffer size after logging: {buffer_size_after_logs}')
    
    # Step 3: Mark broker ready
    print('\n--- Marking broker ready ---')
    if _logger_factory and _logger_factory._transport:
        _logger_factory._transport.mark_broker_ready()
        await asyncio.sleep(0.1)  # Give time for async operations
        
        # Check transport readiness AFTER marking ready
        transport = _logger_factory._transport
        broker_available = getattr(transport, '_broker_available', False)
        client_connected = getattr(transport, '_message_bus_client', None) and getattr(transport._message_bus_client, 'connected', False)
        print(f'After mark_broker_ready - broker_available: {broker_available}')
        print(f'After mark_broker_ready - client_connected: {client_connected}')
        print(f'After mark_broker_ready - transport ready: {broker_available and client_connected}')
        
        buffer_size_after_flush = len(_logger_factory._log_buffer._buffer) if _logger_factory and _logger_factory._log_buffer else 0
        print(f'Buffer size after flush: {buffer_size_after_flush}')
    
    # Step 4: Log AFTER marking ready
    print('\n--- Logging AFTER marking ready ---')
    logger.info('Test log 4 - should go direct or buffer?')
    logger.warning('Test log 5 - should go direct or buffer?')
    
    final_buffer_size = len(_logger_factory._log_buffer._buffer) if _logger_factory and _logger_factory._log_buffer else 0
    print(f'Final buffer size: {final_buffer_size}')

if __name__ == "__main__":
    asyncio.run(test_buffering_workflow())
