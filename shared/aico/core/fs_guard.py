from __future__ import annotations

import builtins
import logging
import os
from pathlib import Path
from typing import Callable, Iterable


class FsGuardError(RuntimeError):
    pass


_ORIG_OPEN = builtins.open
_ORIG_OS_OPEN = os.open
_ORIG_PATH_OPEN = Path.open

_ENABLED = False
_ALLOWED_ROOTS: tuple[Path, ...] = ()
_LOGGER = logging.getLogger("aico.core.fs_guard")


def _normalize_path(path: str | os.PathLike[str]) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (Path.cwd() / p)
    return p.resolve(strict=False)


def _is_allowed(path: Path) -> bool:
    # Allow /tmp for system libraries (e.g., keyring backend detection)
    if str(path).startswith("/tmp/"):
        return True
    
    for root in _ALLOWED_ROOTS:
        try:
            if path.is_relative_to(root):
                return True
        except Exception:
            try:
                if str(path).startswith(str(root)):
                    return True
            except Exception:
                continue
    return False


def _is_write_mode(mode: str) -> bool:
    if not mode:
        return False
    return any(ch in mode for ch in ("w", "a", "x", "+"))


def _is_write_flags(flags: int) -> bool:
    accmode = flags & os.O_ACCMODE
    if accmode in (os.O_WRONLY, os.O_RDWR):
        return True
    if flags & (getattr(os, "O_CREAT", 0) | getattr(os, "O_TRUNC", 0) | getattr(os, "O_APPEND", 0)):
        return True
    return False


def _deny(path: Path, *, op: str) -> None:
    msg = (
        "fs_guard blocked file write outside allowed roots. "
        f"op={op} path={path} allowed_roots={[str(r) for r in _ALLOWED_ROOTS]} "
        "Writes are only allowed under AICO_DATA_DIR/{runtime,cache,logs,tmp,artifacts}."
    )
    _LOGGER.critical(msg, stack_info=True)
    raise FsGuardError(msg)


def _guard_path_for_write(path: str | os.PathLike[str], *, op: str) -> None:
    p = _normalize_path(path)

    if str(p) == os.devnull:
        return

    if not _is_allowed(p):
        _deny(p, op=op)


def _default_allowed_roots() -> list[Path]:
    try:
        from aico.core.paths import AICOPaths

        data_root = Path(os.getenv("AICO_DATA_DIR") or AICOPaths.get_data_directory())
    except Exception:
        data_root = Path(os.getenv("AICO_DATA_DIR") or Path.cwd())

    data_root = _normalize_path(data_root)
    roots = [
        data_root / "runtime",
        data_root / "cache",
        data_root / "logs",
        data_root / "tmp",
        data_root / "artifacts",
    ]

    for r in roots:
        try:
            r.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    return roots


def enable_fs_guard(*, allowed_roots: Iterable[str | os.PathLike[str]] | None = None) -> None:
    global _ENABLED, _ALLOWED_ROOTS

    if _ENABLED:
        return

    roots: list[Path] = []
    if allowed_roots is not None:
        roots = [_normalize_path(r) for r in allowed_roots]
    else:
        roots = _default_allowed_roots()

    _ALLOWED_ROOTS = tuple(roots)

    def _open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        if _is_write_mode(str(mode)):
            _guard_path_for_write(file, op="open")
        return _ORIG_OPEN(file, mode, buffering, encoding, errors, newline, closefd, opener)

    def _path_open(self: Path, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        if _is_write_mode(str(mode)):
            _guard_path_for_write(self, op="Path.open")
        return _ORIG_PATH_OPEN(self, mode=mode, buffering=buffering, encoding=encoding, errors=errors, newline=newline)

    def _os_open(path, flags, mode=0o777, *, dir_fd=None):
        if _is_write_flags(int(flags)):
            _guard_path_for_write(path, op="os.open")
        return _ORIG_OS_OPEN(path, flags, mode, dir_fd=dir_fd)

    builtins.open = _open
    Path.open = _path_open  # type: ignore[assignment]
    os.open = _os_open  # type: ignore[assignment]

    _ENABLED = True
    _LOGGER.critical(
        "fs_guard enabled (strict). allowed_roots=%s",
        [str(r) for r in _ALLOWED_ROOTS],
    )


def disable_fs_guard() -> None:
    global _ENABLED
    if not _ENABLED:
        return

    builtins.open = _ORIG_OPEN
    Path.open = _ORIG_PATH_OPEN  # type: ignore[assignment]
    os.open = _ORIG_OS_OPEN  # type: ignore[assignment]

    _ENABLED = False
    _LOGGER.critical("fs_guard disabled")


def with_fs_guard(*, allowed_roots: Iterable[str | os.PathLike[str]] | None = None) -> Callable:
    def _decorator(fn: Callable):
        def _wrapped(*args, **kwargs):
            enable_fs_guard(allowed_roots=allowed_roots)
            try:
                return fn(*args, **kwargs)
            finally:
                disable_fs_guard()

        return _wrapped

    return _decorator
