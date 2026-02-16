"""
Pytest configuration for AICO backend tests.

This file is automatically loaded by pytest and provides:
- Global fixtures
- Test configuration
- Plugins and hooks
"""

import pytest
import sys
from pathlib import Path

# Add project root and shared to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared"))

# Mock AICO logging before any imports (prevents logging conflicts in tests)
from unittest.mock import MagicMock
import sys

# Create a mock logger that properly handles extra parameters
mock_logger = MagicMock()
# Make the mock logger silently accept any method calls
mock_logger.debug = MagicMock()
mock_logger.info = MagicMock()
mock_logger.warning = MagicMock()
mock_logger.error = MagicMock()
mock_logger.critical = MagicMock()

# Mock the entire logging module before AICO imports
sys.modules['aico.core.logging'] = MagicMock(
    get_logger=lambda *args, **kwargs: mock_logger,
    initialize_logging=MagicMock(),
    initialize_cli_logging=MagicMock()
)

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for async tests."""
    import asyncio
    return asyncio.get_event_loop_policy()


# Import all fixtures so pytest can discover them
# These must be imported AFTER sys.path is set up above
from backend.tests.fixtures.database import (
    test_db,
    test_db_file,
    test_db_empty,
    test_user,
    session_factory,
)
from backend.tests.fixtures.config import test_config
from backend.tests.fixtures.agency import (
    sample_goal,
    sample_hobby_goal,
    sample_goals,
    sample_plan,
    sample_plan_with_shape,
    sample_agency_event,
    mock_llm_plan_response,
    mock_llm_plan_response_failure,
    seeded_goals,
    seeded_goal_with_plan,
    permissive_value_profile,
    mock_message_bus,
    agency_engine,
)

# Make fixtures available to all tests
__all__ = [
    "test_db",
    "test_db_file",
    "test_db_empty",
    "test_user",
    "session_factory",
    "test_config",
    "sample_goal",
    "sample_hobby_goal",
    "sample_goals",
    "sample_plan",
    "sample_plan_with_shape",
    "sample_agency_event",
    "mock_llm_plan_response",
    "mock_llm_plan_response_failure",
    "seeded_goals",
    "seeded_goal_with_plan",
    "permissive_value_profile",
    "mock_message_bus",
    "agency_engine",
]
