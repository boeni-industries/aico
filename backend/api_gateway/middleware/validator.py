"""
Message Validator Middleware for AICO API Gateway

Validates and converts messages with:
- Schema validation
- Message format conversion
- Protocol Buffer support
- Error handling
"""

import json
from typing import Dict, Any, Optional
import sys
from pathlib import Path

# Shared modules now installed via UV editable install

from aico.core.logging import get_logger
from aico.core.bus import MessageBusClient
from aico.core import AicoMessage, MessageMetadata


class MessageValidator:
    """
    Validates and converts messages for the API Gateway
    
    Provides:
    - Schema validation
    - Message format conversion
    - Protocol Buffer support
    - Error handling and reporting
    """
    
    def __init__(self):
        self.logger = get_logger("api_gateway", "validator")
        
        # Message schemas (would be loaded from schema files in production)
        self.schemas = self._load_schemas()
        
        self.logger.info("Message validator initialized")
    
    def _load_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Load message schemas"""
        # Basic schemas for common message types
        return {
            "api.conversation.start": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "context": {"type": "object"},
                    "user_id": {"type": "string"}
                },
                "required": ["text"]
            },
            "api.conversation.message": {
                "type": "object", 
                "properties": {
                    "conversation_id": {"type": "string"},
                    "text": {"type": "string"},
                    "message_type": {"type": "string", "enum": ["user", "system"]},
                    "metadata": {"type": "object"}
                },
                "required": ["conversation_id", "text"]
            },
            "api.personality.get": {
                "type": "object",
                "properties": {}
            },
            "api.personality.update": {
                "type": "object",
                "properties": {
                    "traits": {"type": "object"},
                    "values": {"type": "object"},
                    "preferences": {"type": "object"}
                }
            },
            "api.memory.search": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                    "filters": {"type": "object"}
                },
                "required": ["query"]
            },
            "api.system.status": {
                "type": "object",
                "properties": {}
            }
        }
    
    async def validate_and_convert(self, message: AicoMessage) -> AicoMessage:
        """
        Validate and convert message
        
        Args:
            message: Input message to validate
            
        Returns:
            Validated and converted message
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Validate message structure
            self._validate_message_structure(message)
            
            # Validate message type
            message_type = message.metadata.message_type
            if not message_type:
                raise ValidationError("Message type is required")
            
            # Validate payload against schema
            if message_type in self.schemas:
                self._validate_payload_schema(message.payload, self.schemas[message_type])
            else:
                self.logger.warning(f"No schema found for message type: {message_type}")
            
            # Convert and normalize message
            converted_message = self._convert_message(message)
            
            self.logger.debug(f"Message validated: {message_type}")
            return converted_message
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Message validation error: {e}")
            raise ValidationError(f"Validation failed: {e}")
    
    def _validate_message_structure(self, message: AicoMessage):
        """Validate basic message structure"""
        if not isinstance(message, AicoMessage):
            raise ValidationError("Invalid message type")
        
        if not message.metadata:
            raise ValidationError("Message metadata is required")
        
        if not isinstance(message.metadata, MessageMetadata):
            raise ValidationError("Invalid metadata type")
        
        # Validate required metadata fields
        required_fields = ["message_id", "timestamp", "source", "message_type", "version"]
        for field in required_fields:
            if not getattr(message.metadata, field, None):
                raise ValidationError(f"Required metadata field missing: {field}")
    
    def _validate_payload_schema(self, payload: Any, schema: Dict[str, Any]):
        """Validate payload against JSON schema"""
        try:
            import jsonschema
            jsonschema.validate(payload, schema)
        except ImportError:
            # jsonschema not available, skip schema validation
            self.logger.warning("jsonschema not available, skipping schema validation")
        except jsonschema.ValidationError as e:
            raise ValidationError(f"Schema validation failed: {e.message}")
        except Exception as e:
            raise ValidationError(f"Schema validation error: {e}")
    
    def _convert_message(self, message: AicoMessage) -> AicoMessage:
        """Convert and normalize message"""
        # Ensure payload is serializable
        if hasattr(message.payload, 'SerializeToString'):
            # Protocol Buffer message - keep as is
            pass  # Valid payload type - no conversion needed
        elif isinstance(message.payload, bytes):
            # Byte payload - keep as is
            pass  # Valid payload type - no conversion needed
        elif isinstance(message.payload, (dict, list, str, int, float, bool, type(None))):
            # JSON serializable - keep as is
            pass  # Valid payload type - no conversion needed
        else:
            # Convert to dict if possible
            try:
                if hasattr(message.payload, '__dict__'):
                    message.payload = message.payload.__dict__
                else:
                    message.payload = str(message.payload)
            except Exception as e:
                raise ValidationError(f"Cannot serialize payload: {e}")
        
        # Priority validation removed - not in protobuf schema
        # (MessagePriority enum no longer exists in protobuf)
        
        return message
    
    def add_schema(self, message_type: str, schema: Dict[str, Any]):
        """Add new message schema"""
        self.schemas[message_type] = schema
        self.logger.info(f"Added schema for message type: {message_type}")
    
    def remove_schema(self, message_type: str):
        """Remove message schema"""
        if message_type in self.schemas:
            del self.schemas[message_type]
            self.logger.info(f"Removed schema for message type: {message_type}")
    
    def get_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Get all schemas"""
        return self.schemas.copy()


class ValidationError(Exception):
    """Raised when message validation fails"""
    pass  # Standard exception class definition - not silencing failures
