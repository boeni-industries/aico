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
import os
import shutil
import tempfile

# Add project root and shared to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared"))

if "AICO_TEST_DB_NAME" not in os.environ:
    os.environ["AICO_TEST_DB_NAME"] = "aico_test"


def pytest_sessionstart(session):
    if "AICO_TEST_DB_NAME" not in os.environ:
        os.environ["AICO_TEST_DB_NAME"] = "aico_test"

    try:
        from aico.data.postgres import connection as pg_connection

        pg_connection._pool = None
        pg_connection._engine = None
        pg_connection._session_factory = None
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_config_dir():
    if "AICO_CONFIG_DIR" in os.environ:
        try:
            cfg_root = Path(os.environ["AICO_CONFIG_DIR"])
            user_dir = cfg_root / "user"
            user_dir.mkdir(parents=True, exist_ok=True)
            (user_dir / "agency.yaml").write_text(
                "safety_control:\n  autonomy_level: 'balanced'\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        yield
        return

    src_root = project_root / "config"
    dst_root = Path(tempfile.mkdtemp(prefix="aico_test_config_"))

    for subdir, pattern in (
        ("defaults", "*.yaml"),
        ("environments", "*.yaml"),
        ("schemas", "*.schema.json"),
        ("modelfiles", "Modelfile.*"),
    ):
        src = src_root / subdir
        dst = dst_root / subdir
        if not src.exists():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for p in src.glob(pattern):
            shutil.copy2(p, dst / p.name)

    os.environ["AICO_CONFIG_DIR"] = str(dst_root)

    user_dir = dst_root / "user"
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "agency.yaml").write_text(
        "safety_control:\n  autonomy_level: 'balanced'\n",
        encoding="utf-8",
    )

    try:
        from aico.core.config import ConfigurationManager

        ConfigurationManager._instance = None
        ConfigurationManager._initialized = False
        ConfigurationManager._watchers_started = False
    except Exception:
        pass

    yield

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
