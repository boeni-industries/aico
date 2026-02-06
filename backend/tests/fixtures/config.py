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

    for subdir, pattern in (
        ("defaults", "*.yaml"),
        ("environments", "*.yaml"),
        ("schemas", "*.schema.json"),
        ("modelfiles", "Modelfile.*"),
    ):
        src = project_config_dir / subdir
        dst = config_root / subdir
        if not src.exists():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for p in src.glob(pattern):
            shutil.copy2(p, dst / p.name)
    
    # Create config manager
    config = ConfigurationManager()
    
    # Override any test-specific settings here if needed
    # config.set("test.mode", True)
    
    return config
