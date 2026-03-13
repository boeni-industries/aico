import pytest

from aico.core.fs_guard import FsGuardError, disable_fs_guard, enable_fs_guard


@pytest.mark.asyncio
async def test_fs_guard_blocks_writes_outside_allowed_roots(tmp_path):
    disable_fs_guard()
    import os

    os.environ["AICO_DATA_DIR"] = str(tmp_path)
    enable_fs_guard()

    allowed_file = tmp_path / "runtime" / "ok.txt"
    allowed_file.write_text("ok")
    assert allowed_file.read_text() == "ok"

    disallowed_file = tmp_path / "nope.txt"
    with pytest.raises(FsGuardError):
        disallowed_file.write_text("nope")

    disable_fs_guard()
