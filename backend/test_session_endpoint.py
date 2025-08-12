#!/usr/bin/env python3
"""
Test script for the admin session list endpoint

This script tests the JWT authentication and session management functionality
by creating test sessions and calling the admin endpoint.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from api_gateway.core.auth import AuthenticationManager, User
from api_gateway.admin.endpoints import create_admin_app
from aico.core.config import ConfigurationManager
from aico.core.logging import initialize_logging, get_logger


async def test_session_endpoint():
    """Test the session list endpoint with JWT authentication"""
    
    # Initialize configuration and logging
    config_manager = ConfigurationManager()
    config_manager.initialize(lightweight=True)
    initialize_logging(config_manager)
    
    logger = get_logger("test", "session_endpoint")
    logger.info("Starting session endpoint test")
    
    try:
        # Create auth manager
        auth_manager = AuthenticationManager(config_manager)
        logger.info("Auth manager created")
        
        # Create some test users and sessions
        test_users = [
            User(
                user_id="user1",
                username="alice",
                roles=["user"],
                permissions={"conversation.start", "profile.read"},
                metadata={"test": True}
            ),
            User(
                user_id="admin1", 
                username="admin_bob",
                roles=["admin", "user"],
                permissions={"*"},
                metadata={"test": True}
            ),
            User(
                user_id="user2",
                username="charlie", 
                roles=["user"],
                permissions={"conversation.start"},
                metadata={"test": True}
            )
        ]
        
        # Create sessions for test users
        session_ids = []
        for user in test_users:
            session_id = auth_manager.create_session(
                user, 
                ip_address="127.0.0.1",
                user_agent="Test-Agent/1.0"
            )
            session_ids.append(session_id)
            logger.info(f"Created session for {user.username}: {session_id}")
        
        # Generate admin JWT token for testing
        admin_token = auth_manager.generate_jwt_token(
            user_id="admin1",
            username="admin_bob", 
            roles=["admin", "user"],
            permissions={"*"}
        )
        logger.info(f"Generated admin JWT token: {admin_token[:20]}...")
        
        # Test session listing
        sessions = auth_manager.list_sessions()
        logger.info(f"Total sessions: {len(sessions)}")
        
        for session in sessions:
            logger.info(f"Session: {session.username} ({session.user_id}) - "
                       f"Admin: {session.is_admin} - Status: {session.status.value}")
        
        # Test session stats
        stats = auth_manager.get_session_stats()
        logger.info(f"Session stats: {stats}")
        
        # Test filtering
        admin_sessions = auth_manager.list_sessions(admin_only=True)
        logger.info(f"Admin sessions: {len(admin_sessions)}")
        
        user_sessions = auth_manager.list_sessions(user_id="user1")
        logger.info(f"User1 sessions: {len(user_sessions)}")
        
        logger.info("✅ Session endpoint test completed successfully!")
        
        print("\n" + "="*60)
        print("SESSION ENDPOINT TEST RESULTS")
        print("="*60)
        print(f"Total sessions created: {len(session_ids)}")
        print(f"Active sessions: {stats['active_sessions']}")
        print(f"Admin sessions: {stats['admin_sessions']}")
        print(f"Admin JWT token: {admin_token[:20]}...")
        print("\nTo test the endpoint manually:")
        print("1. Start the backend server: uvicorn main:app --reload --port 8700")
        print("2. Use the admin token in Authorization header: Bearer <token>")
        print("3. Call: GET http://localhost:8700/admin/auth/sessions")
        print("4. Check admin docs: http://localhost:8700/admin/docs")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_session_endpoint())
    sys.exit(0 if success else 1)
