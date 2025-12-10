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
