"""
Admin Endpoints for AICO API Gateway

Provides administrative interface with:
- System status and monitoring
- Configuration management
- User and session management
- Security controls
- Gateway statistics
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional, List
import sys
from pathlib import Path
import jwt

# Shared modules now installed via UV editable install

from aico.core.logging import get_logger
from ..models.session import SessionInfo

security = HTTPBearer()


def create_admin_app(auth_manager, authz_manager, message_router, gateway) -> FastAPI:
    """Create admin FastAPI application"""
    
    logger = get_logger("api_gateway", "admin")
    
    app = FastAPI(
        title="AICO API Gateway Admin",
        description="Administrative interface for AICO API Gateway",
        version="1.0.0",
        docs_url="/admin/docs",
        redoc_url="/admin/redoc"
    )
    
    async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Verify admin authentication with proper JWT validation"""
        try:
            token = credentials.credentials
            
            # Decode and validate JWT token
            try:
                payload = jwt.decode(
                    token,
                    auth_manager._get_jwt_secret(),
                    algorithms=[auth_manager.jwt_algorithm]
                )
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Token has expired")
            except jwt.InvalidTokenError:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            # Check if token is revoked
            if token in auth_manager.revoked_tokens:
                raise HTTPException(status_code=401, detail="Token has been revoked")
            
            # Extract user information
            user_id = payload.get("sub")
            username = payload.get("username", user_id)
            roles = payload.get("roles", [])
            
            # Verify admin role
            if "admin" not in roles:
                raise HTTPException(status_code=403, detail="Admin access required")
            
            return {
                "user_id": user_id,
                "username": username,
                "roles": roles,
                "token": token
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Admin token verification failed: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    @app.get("/health")
    async def admin_health():
        """Admin health check"""
        return {"status": "healthy", "service": "aico-api-gateway-admin"}
    
    @app.get("/gateway/status")
    async def gateway_status(user = Depends(verify_admin_token)):
        """Get gateway status"""
        return gateway.get_health_status()
    
    @app.get("/gateway/stats")
    async def gateway_stats(user = Depends(verify_admin_token)):
        """Get gateway statistics"""
        stats = {
            "routing": message_router.get_routing_stats(),
            "adapters": {}
        }
        
        # Get adapter-specific stats
        for name, adapter in gateway.adapters.items():
            if hasattr(adapter, 'get_stats'):
                stats["adapters"][name] = adapter.get_stats()
            elif hasattr(adapter, 'get_connection_stats'):
                stats["adapters"][name] = adapter.get_connection_stats()
        
        return stats
    
    @app.get("/auth/sessions")
    async def list_sessions(
        user_id: Optional[str] = None,
        admin_only: bool = False,
        include_stats: bool = True,
        user = Depends(verify_admin_token)
    ):
        """
        List sessions with comprehensive information
        
        Query Parameters:
        - user_id: Filter sessions by specific user ID
        - admin_only: Show only admin sessions
        - include_stats: Include session statistics
        """
        try:
            # Get sessions from auth manager
            sessions = auth_manager.list_sessions(user_id=user_id, admin_only=admin_only)
            
            # Convert to API response format
            session_data = []
            for session in sessions:
                session_dict = session.to_dict()
                # Remove sensitive information for API response
                session_dict.pop('metadata', None)
                session_data.append(session_dict)
            
            response = {
                "sessions": session_data,
                "total": len(session_data)
            }
            
            # Include statistics if requested
            if include_stats:
                response["stats"] = auth_manager.get_session_stats()
            
            logger.info("Sessions listed", extra={
                "admin_user": user["username"],
                "filter_user_id": user_id,
                "admin_only": admin_only,
                "total_returned": len(session_data)
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve sessions")
    
    @app.delete("/auth/sessions/{session_id}")
    async def revoke_session(session_id: str, user = Depends(verify_admin_token)):
        """Revoke user session"""
        auth_manager.revoke_session(session_id)
        return {"message": f"Session {session_id} revoked"}
    
    @app.post("/auth/tokens/revoke")
    async def revoke_token(token_data: Dict[str, str], user = Depends(verify_admin_token)):
        """Revoke JWT token"""
        token = token_data.get("token")
        if not token:
            raise HTTPException(status_code=400, detail="Token required")
        
        auth_manager.revoke_token(token)
        return {"message": "Token revoked"}
    
    @app.get("/security/stats")
    async def security_stats(user = Depends(verify_admin_token)):
        """Get security statistics"""
        return gateway.security_middleware.get_security_stats()
    
    @app.post("/security/block-ip")
    async def block_ip(ip_data: Dict[str, str], user = Depends(verify_admin_token)):
        """Block IP address"""
        ip = ip_data.get("ip")
        if not ip:
            raise HTTPException(status_code=400, detail="IP address required")
        
        gateway.security_middleware.add_blocked_ip(ip)
        return {"message": f"IP {ip} blocked"}
    
    @app.delete("/security/block-ip/{ip}")
    async def unblock_ip(ip: str, user = Depends(verify_admin_token)):
        """Unblock IP address"""
        gateway.security_middleware.remove_blocked_ip(ip)
        return {"message": f"IP {ip} unblocked"}
    
    @app.get("/config")
    async def get_config(user = Depends(verify_admin_token)):
        """Get gateway configuration"""
        return {
            "protocols": gateway.config.protocols,
            "security": gateway.config.security,
            "performance": gateway.config.performance
        }
    
    @app.post("/routing/mapping")
    async def add_route_mapping(mapping_data: Dict[str, str], user = Depends(verify_admin_token)):
        """Add topic route mapping"""
        external_topic = mapping_data.get("external_topic")
        internal_topic = mapping_data.get("internal_topic")
        
        if not external_topic or not internal_topic:
            raise HTTPException(status_code=400, detail="Both external_topic and internal_topic required")
        
        message_router.add_topic_mapping(external_topic, internal_topic)
        return {"message": f"Route mapping added: {external_topic} → {internal_topic}"}
    
    @app.delete("/routing/mapping/{external_topic}")
    async def remove_route_mapping(external_topic: str, user = Depends(verify_admin_token)):
        """Remove topic route mapping"""
        message_router.remove_topic_mapping(external_topic)
        return {"message": f"Route mapping removed: {external_topic}"}
    
    logger.info("Admin interface created")
    return app
