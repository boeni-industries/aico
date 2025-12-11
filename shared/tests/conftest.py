"""
Shared test configuration for pytest.

Mocks logging to avoid initialization requirements during testing.
"""

import sys
from unittest.mock import MagicMock

# Create a mock logger
mock_logger = MagicMock()

# Mock the entire logging module before AICO imports
sys.modules['aico.core.logging'] = MagicMock(
    get_logger=lambda *args, **kwargs: mock_logger,
    initialize_logging=MagicMock(),
    initialize_cli_logging=MagicMock()
)

# Reset ConfigurationManager singleton before tests to prevent pollution
def pytest_sessionstart(session):
    """Reset configuration singleton at test session start."""
    import os
    # Set environment variable to prevent config persistence during tests
    os.environ['AICO_TEST_MODE'] = '1'
    
    from aico.core.config import ConfigurationManager
    ConfigurationManager._instance = None
    ConfigurationManager._initialized = False
    ConfigurationManager._watchers_started = False

def pytest_sessionfinish(session, exitstatus):
    """Clean up after test session."""
    import os
    os.environ.pop('AICO_TEST_MODE', None)
