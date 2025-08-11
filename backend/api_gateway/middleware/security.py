"""
Security Middleware for AICO API Gateway

Provides request sanitization, IP filtering, and attack prevention.
Integrates with existing AICO security infrastructure.
"""

import re
import ipaddress
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass

from aico.core.logging import get_logger

# Logger will be initialized in classes


@dataclass
class SecurityConfig:
    """Security middleware configuration"""
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    allowed_ips: Optional[List[str]] = None
    blocked_ips: Optional[List[str]] = None
    rate_limit_enabled: bool = True
    sanitize_input: bool = True
    block_suspicious_patterns: bool = True


class SecurityMiddleware:
    """
    Security middleware for request sanitization and protection
    
    Provides:
    - Input sanitization
    - IP allow/block lists
    - Request size limits
    - Attack pattern detection
    """
    
    def __init__(self, config: dict):
        self.config = config
        
        # Compile IP networks for efficient checking
        self.allowed_networks = []
        self.blocked_networks = []
        
        allowed_ips = config.get("allowed_ips", [])
        if allowed_ips:
            for ip in allowed_ips:
                try:
                    self.allowed_networks.append(ipaddress.ip_network(ip, strict=False))
                except ValueError as e:
                    logger.warning(f"Invalid allowed IP pattern: {ip}", extra={
                        "module": "api_gateway",
                        "function": "__init__",
                        "topic": "security.ip_config_error",
                        "error": str(e)
                    })
        
        blocked_ips = config.get("blocked_ips", [])
        if blocked_ips:
            for ip in blocked_ips:
                try:
                    self.blocked_networks.append(ipaddress.ip_network(ip, strict=False))
                except ValueError as e:
                    logger.warning(f"Invalid blocked IP pattern: {ip}", extra={
                        "module": "api_gateway", 
                        "function": "__init__",
                        "topic": "security.ip_config_error",
                        "error": str(e)
                    })
        
        # Suspicious patterns for attack detection
        self.suspicious_patterns = [
            re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'on\w+\s*=', re.IGNORECASE),
            re.compile(r'union\s+select', re.IGNORECASE),
            re.compile(r'drop\s+table', re.IGNORECASE),
            re.compile(r'insert\s+into', re.IGNORECASE),
            re.compile(r'delete\s+from', re.IGNORECASE),
            re.compile(r'\.\./.*\.\./'),  # Path traversal
            re.compile(r'%2e%2e%2f', re.IGNORECASE),  # URL encoded path traversal
        ]
    
    async def process_request(self, request_data: Dict[str, Any], client_ip: str) -> Dict[str, Any]:
        """
        Process and sanitize incoming request
        
        Args:
            request_data: Request data to process
            client_ip: Client IP address
            
        Returns:
            Processed request data
            
        Raises:
            SecurityError: If request is blocked or suspicious
        """
        # Check IP restrictions
        self._check_ip_restrictions(client_ip)
        
        # Check request size
        self._check_request_size(request_data)
        
        # Sanitize input if enabled
        if self.config.get("sanitize_input", True):
            request_data = self._sanitize_request(request_data)
        
        # Check for suspicious patterns
        if self.config.get("block_suspicious_patterns", True):
            self._check_suspicious_patterns(request_data)
        
        logger.debug("Request passed security checks", extra={
            "module": "api_gateway",
            "function": "process_request", 
            "topic": "security.request_processed",
            "client_ip": client_ip
        })
        
        return request_data
    
    def _check_ip_restrictions(self, client_ip: str) -> None:
        """Check if client IP is allowed"""
        try:
            client_addr = ipaddress.ip_address(client_ip)
        except ValueError:
            logger.warning(f"Invalid client IP address: {client_ip}", extra={
                "module": "api_gateway",
                "function": "_check_ip_restrictions",
                "topic": "security.invalid_ip"
            })
            raise SecurityError(f"Invalid IP address: {client_ip}")
        
        # Check blocked IPs first
        for network in self.blocked_networks:
            if client_addr in network:
                logger.warning(f"Blocked IP attempted access: {client_ip}", extra={
                    "module": "api_gateway",
                    "function": "_check_ip_restrictions", 
                    "topic": "security.ip_blocked",
                    "client_ip": client_ip
                })
                raise SecurityError(f"IP address blocked: {client_ip}")
        
        # Check allowed IPs (if configured)
        if self.allowed_networks:
            allowed = any(client_addr in network for network in self.allowed_networks)
            if not allowed:
                logger.warning(f"Non-allowed IP attempted access: {client_ip}", extra={
                    "module": "api_gateway",
                    "function": "_check_ip_restrictions",
                    "topic": "security.ip_not_allowed", 
                    "client_ip": client_ip
                })
                raise SecurityError(f"IP address not in allow list: {client_ip}")
    
    def _check_request_size(self, request_data: Dict[str, Any]) -> None:
        """Check request size limits"""
        import json
        
        try:
            request_size = len(json.dumps(request_data).encode('utf-8'))
            if request_size > self.config.get("max_request_size", 10485760):
                logger.warning(f"Request size exceeded limit: {request_size} bytes", extra={
                    "module": "api_gateway",
                    "function": "_check_request_size",
                    "topic": "security.request_too_large",
                    "size": request_size,
                    "limit": self.config.get("max_request_size", 10485760)
                })
                raise SecurityError(f"Request too large: {request_size} bytes")
        except Exception as e:
            logger.error(f"Error checking request size: {e}", extra={
                "module": "api_gateway", 
                "function": "_check_request_size",
                "topic": "security.size_check_error",
                "error": str(e)
            })
    
    def _sanitize_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize request data"""
        if isinstance(request_data, dict):
            return {k: self._sanitize_value(v) for k, v in request_data.items()}
        elif isinstance(request_data, list):
            return [self._sanitize_value(item) for item in request_data]
        else:
            return self._sanitize_value(request_data)
    
    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize individual value"""
        if isinstance(value, str):
            # Basic HTML/script sanitization
            value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
            value = re.sub(r'<[^>]+>', '', value)  # Strip HTML tags
            value = value.replace('javascript:', '')
            value = value.replace('vbscript:', '')
            return value
        elif isinstance(value, dict):
            return {k: self._sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        else:
            return value
    
    def _check_suspicious_patterns(self, request_data: Dict[str, Any]) -> None:
        """Check for suspicious attack patterns"""
        request_str = str(request_data).lower()
        
        for pattern in self.suspicious_patterns:
            if pattern.search(request_str):
                logger.warning("Suspicious pattern detected in request", extra={
                    "module": "api_gateway",
                    "function": "_check_suspicious_patterns",
                    "topic": "security.suspicious_pattern",
                    "pattern": pattern.pattern
                })
                raise SecurityError("Suspicious request pattern detected")


class SecurityError(Exception):
    """Security-related error"""
    pass
