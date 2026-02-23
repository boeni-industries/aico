"""
Shared test configuration for pytest.

Mocks logging to avoid initialization requirements during testing.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock
import os
import shutil
import tempfile


project_root = Path(__file__).resolve().parents[2]
shared_root = project_root / "shared"
if str(shared_root) not in sys.path:
    sys.path.insert(0, str(shared_root))

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
    # Set environment variable to prevent config persistence during tests
    os.environ['AICO_TEST_MODE'] = '1'

    if 'AICO_TEST_DB_NAME' not in os.environ:
        os.environ['AICO_TEST_DB_NAME'] = 'aico_test'

    # Ensure tests load configuration from a deterministic, isolated config dir.
    # This avoids pulling in OS user config and makes defaults stable for tests.
    if 'AICO_CONFIG_DIR' not in os.environ:
        project_root = Path(__file__).resolve().parents[2]
        src_root = project_root / 'config'
        dst_root = Path(tempfile.mkdtemp(prefix='aico_test_config_'))

        for subdir, pattern in (
            ('defaults', '*.yaml'),
            ('environments', '*.yaml'),
            ('schemas', '*.schema.json'),
            ('modelfiles', 'Modelfile.*'),
        ):
            src = src_root / subdir
            dst = dst_root / subdir
            if not src.exists():
                continue
            dst.mkdir(parents=True, exist_ok=True)
            for p in src.glob(pattern):
                shutil.copy2(p, dst / p.name)

        user_dir = dst_root / 'user'
        user_dir.mkdir(parents=True, exist_ok=True)
        (user_dir / 'agency.yaml').write_text(
            "safety_control:\n  autonomy_level: 'balanced'\n",
            encoding='utf-8',
        )

        os.environ['AICO_CONFIG_DIR'] = str(dst_root)
    
    from aico.core.config import ConfigurationManager
    ConfigurationManager._instance = None
    ConfigurationManager._initialized = False
    ConfigurationManager._watchers_started = False

    try:
        from aico.data.postgres import connection as pg_connection

        pg_connection._pool = None
        pg_connection._engine = None
        pg_connection._session_factory = None
    except Exception:
        pass

def pytest_sessionfinish(session, exitstatus):
    """Clean up after test session."""
    import os
    os.environ.pop('AICO_TEST_MODE', None)
    
    # Clean up any remaining test users from the database
    try:
        from aico.core.config import ConfigurationManager
        from aico.security import AICOKeyManager
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        key_manager = AICOKeyManager(config)

        pg_cfg = config.get("postgres", {})
        if not pg_cfg:
            return

        expected_db_name = os.environ.get("AICO_TEST_DB_NAME", "aico_test")
        password = key_manager.get_database_password("postgres", username=pg_cfg.get("user", "postgres"))
        if not password:
            return

        db = psycopg2.connect(
            host=pg_cfg.get("host", "127.0.0.1"),
            port=int(pg_cfg.get("port", 5432)),
            dbname=expected_db_name,
            user=pg_cfg.get("user", "postgres"),
            password=password,
            cursor_factory=RealDictCursor,
        )

        cursor = db.cursor()
        cursor.execute("SET search_path TO aico_core,public")
        cursor.execute("SELECT COUNT(*) AS count FROM user_profiles WHERE nickname = 'pytest'")
        row = cursor.fetchone() or {}
        count = int(row.get("count", 0) or 0)

        if count > 0:
            cursor.execute("DELETE FROM user_profiles WHERE nickname = 'pytest'")
            db.commit()

        cursor.close()
        db.close()
    except Exception as e:
        # Don't fail the test session if cleanup fails
        return
