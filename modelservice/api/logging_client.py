"""
API Gateway Logging Client for Modelservice

Provides HTTP client for submitting logs to API Gateway logs endpoints
with service-to-service authentication.
"""

import httpx
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import Depends

from aico.core.logging import get_logger
from aico.core.topics import AICOTopics
from .dependencies import get_modelservice_config, get_service_auth_manager
from aico.security.service_auth import ServiceAuthManager


class APIGatewayLoggingClient:
    """HTTP client for submitting logs to API Gateway"""
    
    def __init__(self, config: Dict[str, Any], service_auth: ServiceAuthManager):
        self.config = config
        self.service_auth = service_auth
        # Uses "modelservice" subsystem log level from config
        self.logger = get_logger("modelservice", "logging_client")
        
        # Get API Gateway configuration
        api_gateway_config = config.get("api_gateway", {})
        rest_config = api_gateway_config.get("rest", {})
        self.api_gateway_host = rest_config.get("host", "127.0.0.1")
        self.api_gateway_port = rest_config.get("port", 8771)
        self.base_url = f"http://{self.api_gateway_host}:{self.api_gateway_port}"
        
        # HTTP client configuration
        self.timeout = 2.0
        self.max_retries = 3
        
        # Service token cache
        self._service_token: Optional[str] = None
    
    async def _get_service_token(self) -> str:
        """Get or generate service authentication token"""
        if not self._service_token:
            try:
                self._service_token = self.service_auth.ensure_service_token("modelservice")
                self.logger.info("Modelservice authenticated to API Gateway successfully", extra={
                    "connection_status": "established",
                    "auth_method": "JWT_EdDSA", 
                    "target": "api-gateway",
                    "service_name": "modelservice",
                    "gateway_host": self.api_gateway_host,
                    "gateway_port": self.api_gateway_port
                })
                # Print statement for successful authentication
                print(f"[+] Successfully authenticated to API Gateway with service token")
            except Exception as e:
                self.logger.error(f"Failed to obtain service token: {e}")
                print(f"[!] Failed to authenticate to API Gateway: {e}")
                raise
        
        return self._service_token
    
    async def _make_authenticated_request(self, method: str, endpoint: str, 
                                        data: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """Make authenticated HTTP request to API Gateway"""
        token = await self._get_service_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "AICO-Modelservice/1.0"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if method.upper() == "POST":
                response = await client.post(url, json=data, headers=headers)
            elif method.upper() == "GET":
                response = await client.get(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            return response
    
    async def submit_log(self, level: str, message: str, module: str = "api_router", 
                        topic: Optional[str] = None, **extra) -> bool:
        """Submit single log entry to API Gateway"""
        try:
            log_entry = {
                "level": level.upper(),
                "message": message,
                "module": f"modelservice.{module}",
                "topic": topic or AICOTopics.LOGS_ENTRY,
                "timestamp": datetime.utcnow().isoformat(),
                "origin": "modelservice",
                "subsystem": "modelservice"
            }
            
            # Add extra fields
            if extra:
                log_entry["extra"] = extra
            
            response = await self._make_authenticated_request(
                "POST", 
                "/api/v1/logs/",
                log_entry
            )
            
            if response.status_code == 200:
                self.logger.debug("Log submitted successfully to API Gateway")
                return True
            else:
                self.logger.warning(f"Log submission failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to submit log to API Gateway: {e}")
            return False
    
    async def submit_log_batch(self, log_entries: List[Dict[str, Any]]) -> bool:
        """Submit batch of log entries to API Gateway"""
        try:
            # Format log entries for API Gateway
            formatted_logs = []
            for entry in log_entries:
                formatted_entry = {
                    "level": entry.get("level", "INFO").upper(),
                    "message": entry.get("message", ""),
                    "module": f"modelservice.{entry.get('module', 'unknown')}",
                    "topic": entry.get("topic", AICOTopics.LOGS_ENTRY),
                    "timestamp": entry.get("timestamp", datetime.utcnow().isoformat()),
                    "origin": "modelservice",
                    "subsystem": "modelservice"
                }
                
                if entry.get("extra"):
                    formatted_entry["extra"] = entry["extra"]
                
                formatted_logs.append(formatted_entry)
            
            batch_data = {"logs": formatted_logs}
            
            response = await self._make_authenticated_request(
                "POST",
                "/api/v1/logs/batch",
                batch_data
            )
            
            if response.status_code == 200:
                self.logger.debug(f"Log batch submitted successfully: {len(formatted_logs)} entries")
                return True
            else:
                self.logger.warning(f"Log batch submission failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to submit log batch to API Gateway: {e}")
            return False
    
    async def check_api_gateway_health(self) -> Dict[str, Any]:
        """Check API Gateway connectivity and health"""
        try:
            # Health endpoint doesn't require authentication - call directly for speed
            url = f"{self.base_url}/api/v1/health"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
            
            if response.status_code == 200:
                health_data = response.json()
                return {
                    "status": "healthy",
                    "reachable": True,
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                    "api_gateway_status": health_data.get("status", "unknown")
                }
            else:
                return {
                    "status": "unhealthy",
                    "reachable": True,
                    "error": f"HTTP {response.status_code}",
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000)
                }
                
        except httpx.ConnectError:
            return {
                "status": "unhealthy",
                "reachable": False,
                "error": "connection_refused"
            }
        except httpx.TimeoutException:
            return {
                "status": "unhealthy", 
                "reachable": False,
                "error": "timeout"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "reachable": False,
                "error": str(e)
            }


# Dependency injection for logging client
def get_logging_client(
    config: Dict[str, Any] = Depends(get_modelservice_config),
    service_auth: ServiceAuthManager = Depends(get_service_auth_manager)
) -> APIGatewayLoggingClient:
    """Get API Gateway logging client instance."""
    return APIGatewayLoggingClient(config, service_auth)
