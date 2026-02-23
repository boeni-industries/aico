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
    os.environ.pop('AICO_TEST_MODE', None)
    
    # Clean up any remaining test users from the database
    try:
        from aico.core.paths import AICOPaths
        from aico.core.config import ConfigurationManager
        from aico.security import AICOKeyManager
        import keyring
        
        db_path = AICOPaths.resolve_database_path("aico.db", "auto")
        config = ConfigurationManager()
        key_manager = AICOKeyManager(config)
        
        # Try to get cached session key
        cached_key = key_manager._get_cached_session()
        if cached_key:
            master_key = cached_key
        else:
            # Try keyring
            stored_key = keyring.get_password(key_manager.service_name, "master_key")
            if stored_key:
                master_key = bytes.fromhex(stored_key)
            else:
                # No key available, skip cleanup
                return
        
        encryption_key = key_manager.derive_database_key(master_key, "postgres", str(db_path))
        db = None          
        # Delete all test users (nickname='pytest')
        cursor = db.execute("SELECT COUNT(*) FROM user_profiles WHERE nickname = 'pytest'")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"\n🧹 Cleaning up {count} test users from database...")
            db.execute("DELETE FROM user_profiles WHERE nickname = 'pytest'")
            db.commit()
            print(f"✅ Deleted {count} test users")
    except Exception as e:
        # Don't fail the test session if cleanup fails
        print(f"⚠️  Warning: Could not clean up test users: {e}")
