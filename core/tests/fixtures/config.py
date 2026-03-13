"""
Configuration Test Fixtures

Provides test configuration instances.
"""

import pytest
import os
import shutil
from pathlib import Path


@pytest.fixture
def test_config(tmp_path):
    """Provide a test configuration manager.
    
    Uses default configuration from config/defaults/core.yaml
    """
    from aico.core.config import ConfigurationManager
    
    project_root = Path(__file__).parent.parent.parent.parent
    project_config_dir = project_root / "config"

    config_root = tmp_path / "config"
    os.environ["AICO_CONFIG_DIR"] = str(config_root)

    data_root = tmp_path / "data"
    os.environ["AICO_DATA_DIR"] = str(data_root)

    for subdir, pattern in (
        ("defaults", "*.yaml"),
        ("environments", "*.yaml"),
        ("schemas", "*.schema.json"),
    ):
        src = project_config_dir / subdir
        dst = config_root / subdir
        if not src.exists():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for p in src.glob(pattern):
            shutil.copy2(p, dst / p.name)

    # ConfigurationManager reads user overrides from AICO_DATA_DIR/runtime/config/user/*.yaml
    runtime_cfg_dir = data_root / "runtime" / "config" / "user"
    runtime_cfg_dir.mkdir(parents=True, exist_ok=True)
    (runtime_cfg_dir / "agency.yaml").write_text(
        "safety_control:\n  autonomy_level: 'balanced'\n",
        encoding="utf-8",
    )

    try:
        ConfigurationManager._instance = None
        ConfigurationManager._initialized = False
        ConfigurationManager._watchers_started = False
    except Exception:
        pass

    config = ConfigurationManager()
    config.initialize(lightweight=True)
    
    # Override any test-specific settings here if needed
    # config.set("test.mode", True)
    
    return config
