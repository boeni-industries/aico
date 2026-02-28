import os

import pytest
import yaml

from aico.core.config import ConfigurationManager
from aico.core.fs_guard import disable_fs_guard, enable_fs_guard


@pytest.mark.asyncio
async def test_runtime_config_persists_under_aico_data_dir_runtime(tmp_path, monkeypatch):
    disable_fs_guard()

    monkeypatch.setenv("AICO_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("AICO_RUNTIME_CONFIG_DIR", raising=False)
    monkeypatch.setenv("AICO_TEST_MODE", "0")

    enable_fs_guard()

    cfg = ConfigurationManager()
    cfg.initialize(lightweight=True)

    cfg.set("system.fs_guard_test_key", "ok", persist=True)

    runtime_file = tmp_path / "runtime" / "runtime.yaml"
    assert runtime_file.exists()

    data = yaml.safe_load(runtime_file.read_text()) or {}
    assert (data.get("system") or {}).get("fs_guard_test_key") == "ok"

    disable_fs_guard()
