"""
AICO Test Client

HTTP client for interacting with AICO backend API during memory evaluation tests.
Handles authentication, message sending, and response parsing.
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class MessageResponse:
    """Response from AICO conversation API"""
    success: bool
    message_id: str
    conversation_id: str
    conversation_action: str
    conversation_reasoning: str
    status: str
    ai_response: str = ""
    timestamp: str = ""
    error: str = ""
    response_time_ms: float = 0.0


@dataclass
class AuthResponse:
    """Authentication response"""
    success: bool
    token: str
    user_id: str
    expires_at: Optional[datetime] = None
    error: Optional[str] = None


class AICOTestClient:
    """
    HTTP client for AICO backend API testing.
    
    Provides methods for authentication, message sending, and conversation management
    specifically designed for memory evaluation testing scenarios.
    """
    
    def __init__(self, 
                 backend_url: str = "http://localhost:8000",
                 auth_token: Optional[str] = None,
                 timeout_seconds: int = 30):
        """
        Initialize AICO test client.
        
        Args:
            backend_url: Base URL for AICO backend API
            auth_token: Pre-existing auth token (if None, will attempt login)
            timeout_seconds: Request timeout
        """
        self.backend_url = backend_url.rstrip('/')
        self.auth_token = auth_token
        self.timeout_seconds = timeout_seconds
        
        # Session management
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_id: Optional[str] = None
        self.authenticated = False
        
        # Test user credentials for evaluation
        self.test_username = "memory_evaluator"
        self.test_password = "eval_test_2024"
        
    async def connect(self) -> bool:
        """
        Connect to AICO backend and authenticate.
        
        Returns:
            True if connection and authentication successful
        """
        try:
            # Create HTTP session
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # Test basic connectivity
            health_url = f"{self.backend_url}/api/v1/health"
            async with self.session.get(health_url) as response:
                if response.status != 200:
                    raise Exception(f"Backend health check failed: {response.status}")
                    
            # Authenticate if no token provided
            if not self.auth_token:
                auth_result = await self._authenticate()
                if not auth_result.success:
                    raise Exception(f"Authentication failed: {auth_result.error}")
                    
                self.auth_token = auth_result.token
                self.user_id = auth_result.user_id
                
            self.authenticated = True
            return True
            
        except Exception as e:
            print(f"Failed to connect to AICO backend: {e}")
            if self.session:
                await self.session.close()
                self.session = None
            return False
            
    async def disconnect(self):
        """Close connection to AICO backend"""
        if self.session:
            await self.session.close()
            self.session = None
        self.authenticated = False
        
    async def send_message(self, 
                          message: str,
                          context: Optional[Dict[str, Any]] = None,
                          conversation_id: Optional[str] = None) -> MessageResponse:
        """
        Send a message to AICO and get response.
        
        Args:
            message: User message text
            context: Optional context hints for the conversation
            conversation_id: Optional conversation ID for context (semantic memory handles continuity)
            
        Returns:
            MessageResponse with AI response and metadata
        """
        if not self.authenticated or not self.session:
            raise Exception("Not connected to AICO backend")
            
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Prepare request data
            request_data = {
                "message": message,
                "message_type": "text",
                "context": context or {}
            }
            
            # Add conversation_id to context if provided (semantic memory will handle continuity)
            if conversation_id:
                request_data["context"]["conversation_id"] = conversation_id
            
            # Use user-scoped messages endpoint (no thread-specific endpoints needed)
            url = f"{self.backend_url}/api/v1/conversation/messages"
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            # Send message
            async with self.session.post(url, json=request_data, headers=headers) as response:
                end_time = asyncio.get_event_loop().time()
                response_time_ms = (end_time - start_time) * 1000
                if response.status != 200:
                    error_text = await response.text()
                    return MessageResponse(
                        success=False,
                        message_id="",
                        conversation_id="",
                        conversation_action="",
                        conversation_reasoning="",
                        status="error",
                        error=f"HTTP {response.status}: {error_text}",
                        response_time_ms=response_time_ms,
                        timestamp=datetime.now()
                    )
                    
                response_data = await response.json()
                
                return MessageResponse(
                    success=response_data.get("success", False),
                    message_id=response_data.get("message_id", ""),
                    conversation_id=response_data.get("conversation_id", ""),
                    conversation_action=response_data.get("conversation_action", ""),
                    conversation_reasoning=response_data.get("conversation_reasoning", ""),
                    status=response_data.get("status", ""),
                    ai_response=response_data.get("ai_response", ""),
                    timestamp=response_data.get("timestamp", ""),
                    response_time_ms=response_time_ms
                )
                
        except Exception as e:
            response_time_ms = (end_time - start_time) * 1000
            
            return MessageResponse(
                success=False,
                message_id="",
                conversation_id="",
                conversation_action="",
                conversation_reasoning="",
                status="error",
                ai_response="",
                timestamp=datetime.now().isoformat(),
                response_time_ms=response_time_ms,
                error=str(e)
            )
            
    async def get_conversation_status(self) -> Dict[str, Any]:
        """Get my conversation status (user-scoped)"""
        if not self.authenticated or not self.session:
            raise Exception("Not connected to AICO backend")
            
        url = f"{self.backend_url}/api/v1/conversation/status"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with self.session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to get conversation status: HTTP {response.status}: {error_text}")
                
    async def list_threads(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """List conversation threads for the current user"""
        if not self.authenticated or not self.session:
            raise Exception("Not connected to AICO backend")
            
        url = f"{self.backend_url}/api/v1/conversation/threads"
        params = {"page": page, "page_size": page_size}
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with self.session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to list threads: HTTP {response.status}: {error_text}")
                
    async def get_message_history(self, page: int = 1, page_size: int = 50, since: Optional[str] = None) -> Dict[str, Any]:
        """Get my message history (user-scoped)"""
        if not self.authenticated or not self.session:
            raise Exception("Not connected to AICO backend")
            
        url = f"{self.backend_url}/api/v1/conversation/messages"
        params = {"page": page, "page_size": page_size}
        if since:
            params["since"] = since
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with self.session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to get message history: HTTP {response.status}: {error_text}")
                
    async def create_explicit_thread(self, 
                                   thread_type: str = "conversation",
                                   initial_message: Optional[str] = None,
                                   context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create an explicit conversation thread"""
        if not self.authenticated or not self.session:
            raise Exception("Not connected to AICO backend")
            
        payload = {
            "thread_type": thread_type,
            "initial_message": initial_message,
            "context": context or {}
        }
        
        url = f"{self.backend_url}/api/v1/conversation/threads"
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        async with self.session.post(url, json=payload, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to create thread: HTTP {response.status}: {error_text}")
                
    async def _authenticate(self) -> AuthResponse:
        """
        Authenticate with AICO backend using test credentials.
        
        Returns:
            AuthResponse with authentication result
        """
        try:
            # Try to register test user first (in case it doesn't exist)
            await self._register_test_user()
            
            # Login with test credentials
            login_url = f"{self.backend_url}/api/v1/auth/login"
            login_payload = {
                "username": self.test_username,
                "password": self.test_password
            }
            
            async with self.session.post(login_url, json=login_payload) as response:
                if response.status == 200:
                    auth_data = await response.json()
                    return AuthResponse(
                        success=True,
                        token=auth_data.get("access_token", ""),
                        user_id=auth_data.get("user_id", ""),
                        expires_at=None  # Parse from auth_data if available
                    )
                else:
                    error_text = await response.text()
                    return AuthResponse(
                        success=False,
                        token="",
                        user_id="",
                        error=f"Login failed: HTTP {response.status}: {error_text}"
                    )
                    
        except Exception as e:
            return AuthResponse(
                success=False,
                token="",
                user_id="",
                error=f"Authentication error: {str(e)}"
            )
            
    async def _register_test_user(self):
        """Register test user for evaluation (ignore errors if already exists)"""
        try:
            register_url = f"{self.backend_url}/api/v1/auth/register"
            register_payload = {
                "username": self.test_username,
                "password": self.test_password,
                "email": f"{self.test_username}@aico-eval.test"
            }
            
            async with self.session.post(register_url, json=register_payload) as response:
                # Ignore response - user might already exist
                pass
                
        except Exception:
            # Ignore registration errors - user might already exist
            pass
            
    async def check_backend_health(self) -> Dict[str, Any]:
        """Check AICO backend health status"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
        try:
            health_url = f"{self.backend_url}/api/v1/health"
            async with self.session.get(health_url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status}",
                        "details": await response.text()
                    }
                    
        except Exception as e:
            return {
                "status": "unreachable",
                "error": str(e)
            }
            
    async def wait_for_backend_ready(self, max_wait_seconds: int = 60, check_interval: float = 2.0) -> bool:
        """
        Wait for AICO backend to be ready and responsive.
        
        Args:
            max_wait_seconds: Maximum time to wait
            check_interval: Seconds between health checks
            
        Returns:
            True if backend becomes ready, False if timeout
        """
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < max_wait_seconds:
            health_status = await self.check_backend_health()
            
            if health_status.get("status") == "healthy":
                return True
                
            print(f"Backend not ready: {health_status.get('status', 'unknown')} - waiting...")
            await asyncio.sleep(check_interval)
            
        return False
