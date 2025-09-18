"""
Logs API Router

Public logging endpoints for frontend log submissions.
Following AICO domain-based API organization patterns.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from datetime import datetime
import gzip
import base64
import json

from aico.core.logging import get_logger
from .schemas import (
    LogEntryRequest,
    LogBatchRequest, 
    LogSubmissionResponse
)
from .dependencies import (
    validate_log_level,
    validate_module_name,
    validate_topic,
    validate_message,
    sanitize_log_entry
)
from .exceptions import (
    LogSubmissionError,
    LogValidationError,
    LogServiceUnavailableError,
    LogBatchTooLargeError,
    handle_log_service_exceptions
)

router = APIRouter()
logger = get_logger("api", "logs_router")


@router.post("/", response_model=LogSubmissionResponse)
@handle_log_service_exceptions
async def submit_log(
    log_entry: LogEntryRequest,
    background_tasks: BackgroundTasks
) -> LogSubmissionResponse:
    """
    Submit a single log entry from frontend
    
    This endpoint accepts log entries from the frontend application
    and forwards them to the AICO logging infrastructure via the message bus.
    """
    # Process log entry through the logging infrastructure
    try:
        # Validate required fields
        validate_module_name(log_entry.module)
        validate_topic(log_entry.topic)
        validate_message(log_entry.message)
        
        # Convert to dict and sanitize
        log_data = log_entry.dict()
        log_data = sanitize_log_entry(log_data)
        
        # Add server-side metadata
        log_data['received_at'] = datetime.utcnow().isoformat()
        log_data['source'] = 'frontend_api'
        
        # Add subsystem field for AICO logging
        if 'subsystem' not in log_data:
            log_data['subsystem'] = 'frontend'
        
        # Process log entry in background to avoid blocking response
        background_tasks.add_task(process_log_entry, log_data)
        
        return LogSubmissionResponse(
            success=True,
            message="Log entry accepted for processing"
        )
        
    except ValueError as e:
        raise LogValidationError(str(e))
    except Exception as e:
        logger.error(f"Failed to process log entry: {e}")
        raise LogServiceUnavailableError()


@router.post("/batch", response_model=LogSubmissionResponse)
@handle_log_service_exceptions
async def submit_log_batch(
    log_batch: LogBatchRequest,
    background_tasks: BackgroundTasks
) -> LogSubmissionResponse:
    """
    Submit multiple log entries in a batch from frontend
    
    This endpoint accepts batches of log entries for efficient processing.
    Useful for frontend applications that buffer logs locally.
    Supports both raw log entries and compressed log data.
    """
    try:
        # Handle compressed logs if present
        if log_batch.compressed_logs:
            try:
                # Decode base64 and decompress
                compressed_data = base64.b64decode(log_batch.compressed_logs)
                decompressed_data = gzip.decompress(compressed_data)
                logs_data = json.loads(decompressed_data.decode('utf-8'))
                
                # Convert to LogEntryRequest objects
                log_entries = []
                for log_data in logs_data:
                    log_entries.append(LogEntryRequest(**log_data))
                    
            except Exception as e:
                logger.error(f"Failed to decompress log batch: {e}")
                raise LogValidationError(f"Invalid compressed log data: {e}")
        else:
            # Use regular logs field
            log_entries = log_batch.logs
        
        if len(log_entries) > 1000:
            raise LogBatchTooLargeError()
        
        accepted_logs = []
        rejected_logs = []
        errors = []
        
        # Validate each log entry
        for i, log_entry in enumerate(log_entries):
            try:
                validate_module_name(log_entry.module)
                validate_topic(log_entry.topic)
                validate_message(log_entry.message)
                
                # Convert to dict and sanitize
                log_data = log_entry.dict()
                log_data = sanitize_log_entry(log_data)
                
                # Add server-side metadata
                log_data['received_at'] = datetime.utcnow().isoformat()
                log_data['source'] = 'frontend_api'
                log_data['batch_index'] = i
                
                accepted_logs.append(log_data)
                
            except ValueError as e:
                rejected_logs.append(log_entry)
                errors.append(f"Entry {i}: {str(e)}")
        
        # Process accepted logs in background
        if accepted_logs:
            background_tasks.add_task(process_log_batch, accepted_logs)
        
        
        total_entries = len(log_entries)
        return LogSubmissionResponse(
            success=len(accepted_logs) > 0,
            message=f"Processed {len(accepted_logs)} of {total_entries} log entries",
            accepted_count=len(accepted_logs),
            rejected_count=len(rejected_logs),
            errors=errors if errors else None
        )
        
    except LogBatchTooLargeError:
        raise
    except Exception as e:
        logger.error(f"Failed to process log batch: {e}")
        raise LogServiceUnavailableError()




async def process_log_entry(log_data: dict):
    """
    Process a single log entry by forwarding to AICO logging infrastructure
    
    This function integrates with the existing AICO logging system
    to ensure logs from any subsystem are properly stored and processed.
    """
    try:
        # Create logger for the specified subsystem (frontend, mobile, cli, etc.)
        # This ensures logs are properly attributed to the originating system
        # Use 'origin' field as the subsystem as per schema definition
        subsystem = log_data.get('origin', 'frontend')
        module = log_data.get('module', 'unknown')
        
        # Parse module to extract the actual module name (e.g., 'mobile.auth' -> 'auth')
        if '.' in module:
            module_parts = module.split('.')
            if len(module_parts) >= 2:
                module = module_parts[1]  # Use the second part as the module name
        
        subsystem_logger = get_logger(subsystem, module)
        
        # Map log levels to Python logging levels
        level_mapping = {
            'DEBUG': 'debug',
            'INFO': 'info', 
            'WARNING': 'warning',
            'ERROR': 'error'
        }
        
        # Handle enum objects from frontend (convert to string)
        log_level = log_data.get('level', 'INFO')
        if hasattr(log_level, 'value'):
            log_level = log_level.value
        elif not isinstance(log_level, str):
            log_level = str(log_level)
        
        log_method = getattr(subsystem_logger, level_mapping.get(log_level, 'info'))
        
        # Handle severity enum objects from frontend
        severity = log_data.get('severity')
        if hasattr(severity, 'value'):
            severity = severity.value
        elif severity is not None and not isinstance(severity, str):
            severity = str(severity)
        
        # Create extra context for structured logging with correct field names for database
        extra_context = {
            'topic': log_data.get('topic'),
            'function_name': log_data.get('function'),  # Database expects function_name
            'user_uuid': log_data.get('user_id'),       # Database expects user_uuid
            'session_id': log_data.get('session_id'),
            'trace_id': log_data.get('trace_id'),
            'frontend_timestamp': log_data.get('timestamp'),
            'source': log_data.get('source'),
            'severity': severity,
            'environment': log_data.get('environment'),
            'origin': log_data.get('origin'),
            'file': log_data.get('file'),
            'line': log_data.get('line')
        }
        
        # Add extra fields if present
        if log_data.get('extra'):
            extra_context.update(log_data['extra'])
        
        # Add error details if present
        if log_data.get('error_details'):
            extra_context['error_details'] = log_data['error_details']
        
        # Remove None values
        extra_context = {k: v for k, v in extra_context.items() if v is not None}
        
        # Log the message using AICO logging infrastructure
        log_method(log_data.get('message', 'No message'), extra=extra_context)
        
    except Exception as e:
        # Fallback logging if something goes wrong
        import traceback
        logger.debug(f"Exception in process_log_entry: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        logger.error(f"Failed to process frontend log entry: {e}", extra={'log_data': log_data})


async def process_log_batch(log_entries: List[dict]):
    """
    Process a batch of log entries
    
    Efficiently processes multiple log entries while maintaining
    the same integration with AICO logging infrastructure.
    """
    try:
        for log_data in log_entries:
            await process_log_entry(log_data)
            
    except Exception as e:
        logger.error(f"Failed to process log batch: {e}", extra={'batch_size': len(log_entries)})
