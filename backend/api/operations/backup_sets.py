import asyncio
import hashlib
import json
import shutil
import subprocess
import tarfile
import time
import uuid
import os
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse

from aico.core.logging import get_logger
from aico.core.paths import AICOPaths
from aico.core.config import ConfigurationManager
from aico.security.key_manager import AICOKeyManager
from aico.data.postgres.connection import get_connection

from backend.api.operations.schemas import (
    BackupSetCreateRequest,
    BackupSetCreateResponse,
    BackupSetInfo,
    BackupSetListResponse,
    BackupSetDeleteResponse,
    BackupSetPruneRequest,
    BackupSetPruneResponse,
    BackupSetRestoreRequest,
    BackupSetRestoreResponse,
    BackupSetStatusResponse,
    BackupSetUploadResponse,
)

logger = get_logger("backend.api.operations.backup_sets")

_POSTGRES_PRIMARY_CONTAINER = "aico-postgres"
_POSTGRES_SHADOW_CONTAINER = "aico-postgres-shadow"
_INFLUX_CONTAINER = "aico-influxdb"

_backup_lock = asyncio.Lock()

_BACKUP_ARCHIVE_OBJECT_PREFIX = "backups/backup_sets"


def _safe_extract_tar(tf: tarfile.TarFile, dest_dir: Path) -> None:
    dest_dir = dest_dir.resolve()
    for member in tf.getmembers():
        member_path = (dest_dir / member.name).resolve()
        if dest_dir not in member_path.parents and member_path != dest_dir:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsafe archive contents (path traversal detected)",
            )
    tf.extractall(dest_dir)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _backup_root() -> Path:
    # Filesystem is not an authoritative backup store anymore.
    # We keep local disk usage strictly as ephemeral staging workspace.
    root = AICOPaths.get_data_directory() / "tmp" / "backup_sets"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _validate_output_root(output_root: Path) -> Path:
    output_root = output_root.expanduser()
    if not output_root.is_absolute():
        output_root = (Path.cwd() / output_root)
    output_root = output_root.resolve(strict=False)

    data_root = AICOPaths.get_data_directory().resolve(strict=False)
    allowed_roots = (
        data_root / "runtime",
        data_root / "cache",
        data_root / "logs",
        data_root / "tmp",
        data_root / "artifacts",
    )

    try:
        if any(output_root.is_relative_to(r) for r in allowed_roots):
            return output_root
    except Exception:
        # Fallback for Python < 3.9 or unusual path behavior
        if any(str(output_root).startswith(str(r)) for r in allowed_roots):
            return output_root

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=(
            "output_path is outside allowed roots. "
            "Writes are only allowed under AICO_DATA_DIR/{runtime,cache,logs,tmp,artifacts}."
        ),
    )


def _get_host_runtime_dir() -> Optional[Path]:
    value = os.environ.get("AICO_HOST_RUNTIME_DIR")
    if not value:
        return None
    p = Path(value)
    return p if p.exists() else None


def _archives_root() -> Path:
    # Archives are no longer persisted locally; returned path is only for temporary files.
    root = _backup_root() / "archives"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _backup_archive_object_key(backup_id: str) -> str:
    return f"{_BACKUP_ARCHIVE_OBJECT_PREFIX}/{backup_id}.tar.gz"


def _get_artifact_store_client_or_none():
    try:
        from aico.data.artifact_store import get_artifact_store_client

        return get_artifact_store_client()
    except Exception:
        return None


async def _db_execute(query: str, *args) -> None:
    async with get_connection() as conn:
        await conn.execute(query, *args)


async def _db_fetchrow(query: str, *args) -> dict | None:
    async with get_connection() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def _db_fetch(query: str, *args) -> list[dict]:
    async with get_connection() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_dir_size_bytes(path: Path) -> int:
    try:
        if not path.exists():
            return 0
        if path.is_file():
            return path.stat().st_size
        total = 0
        for p in path.rglob("*"):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except Exception:
                continue
        return total
    except Exception:
        return 0


def _run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def _run_cmd_with_env(cmd: list[str], env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(cmd, capture_output=True, text=True, env=merged_env)


async def _run_cmd_async(cmd: list[str]) -> subprocess.CompletedProcess:
    return await asyncio.to_thread(_run_cmd, cmd)


async def _run_cmd_async_with_env(cmd: list[str], env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess:
    return await asyncio.to_thread(_run_cmd_with_env, cmd, env)


def _get_pg_connection_info() -> tuple[str, str, str]:
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    pg_cfg = config.get("postgres", {}) or {}

    from aico.security.credential_provider import CredentialProvider

    db_name = pg_cfg.get("db_name", "aico")
    db_user = pg_cfg.get("user", "postgres")

    provider = CredentialProvider()
    db_password = provider.get("pg_password") or ""
    if not db_password:
        key_manager = AICOKeyManager(config)
        db_password = key_manager.get_database_password("postgres", username=db_user) or ""

    if not db_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PostgreSQL password not configured (AICOKeyManager returned empty password)",
        )

    return db_name, db_user, db_password


def _get_pg_host_port() -> tuple[str, str]:
    # In docker-compose.local.yml the postgres service is reachable via the service name.
    host = os.environ.get("AICO_PG_HOST") or "postgres"
    port = os.environ.get("AICO_PG_PORT") or "5432"
    return host, port


def _get_influx_connection_info() -> tuple[str, str, str, str]:
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    influx_cfg = config.get("influx", {}) or {}

    url = influx_cfg.get("url", "http://127.0.0.1:8086")
    org = influx_cfg.get("org", "aico")
    bucket = influx_cfg.get("bucket", "aico_telemetry")

    provider = CredentialProvider()
    token = provider.get("influx_admin_token") or ""
    if not token:
        key_manager = AICOKeyManager(config)
        token = key_manager.get_database_password("influx", username="admin_token") or ""

    if not token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="InfluxDB admin token not configured (AICOKeyManager returned empty token)",
        )

    return url, org, bucket, token


async def _docker_exec(container: str, args: list[str], env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess:
    cmd: list[str] = ["docker", "exec"]
    if env:
        for k, v in env.items():
            cmd.extend(["-e", f"{k}={v}"])
    cmd.append(container)
    cmd.extend(args)

    result = await _run_cmd_async(cmd)
    if result.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command failed: {' '.join(cmd)}\n{result.stderr.strip()}",
        )
    return result


async def _docker_cp_from(container: str, container_path: str, host_path: Path) -> None:
    host_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["docker", "cp", f"{container}:{container_path}", str(host_path)]
    result = await _run_cmd_async(cmd)
    if result.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command failed: {' '.join(cmd)}\n{result.stderr.strip()}",
        )


async def _docker_cp_to(container: str, host_path: Path, container_path: str) -> None:
    cmd = ["docker", "cp", str(host_path), f"{container}:{container_path}"]
    result = await _run_cmd_async(cmd)
    if result.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command failed: {' '.join(cmd)}\n{result.stderr.strip()}",
        )


async def _postgres_dump(backup_dir: Path) -> dict:
    db_name, db_user, db_password = _get_pg_connection_info()

    host, port = _get_pg_host_port()
    host_dest = backup_dir / "postgres" / "pgdump.dump"
    host_dest.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "pg_dump",
        "-Fc",
        "-Z",
        "6",
        "-f",
        str(host_dest),
        "-U",
        db_user,
        "-d",
        db_name,
        "-h",
        host,
        "-p",
        str(port),
    ]

    result = await _run_cmd_async_with_env(cmd, env={"PGPASSWORD": db_password})
    if result.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command failed: {' '.join(cmd)}\n{(result.stderr or '').strip()}",
        )

    return {
        "path": str(host_dest.relative_to(backup_dir)),
        "sha256": _sha256_file(host_dest),
        "size_bytes": host_dest.stat().st_size,
        "format": "pg_dump_custom",
    }


async def _postgres_restore_to(container: str, dump_path: Path) -> None:
    # Dockerized setup: restore via TCP to the target Postgres service.
    db_name, db_user, db_password = _get_pg_connection_info()

    # `container` parameter historically was a container name; keep the signature but
    # interpret it as a host selector.
    host = "postgres" if container == _POSTGRES_PRIMARY_CONTAINER else "postgres-shadow"
    port = "5432"

    cmd = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "-U",
        db_user,
        "-d",
        db_name,
        "-h",
        host,
        "-p",
        port,
        str(dump_path),
    ]

    result = await _run_cmd_async_with_env(cmd, env={"PGPASSWORD": db_password})
    if result.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command failed: {' '.join(cmd)}\n{(result.stderr or '').strip()}",
        )


async def _verify_postgres_container(container: str) -> None:
    db_name, db_user, db_password = _get_pg_connection_info()

    host = "postgres" if container == _POSTGRES_PRIMARY_CONTAINER else "postgres-shadow"
    port = "5432"

    cmd = [
        "psql",
        "-U",
        db_user,
        "-d",
        db_name,
        "-h",
        host,
        "-p",
        port,
        "-t",
        "-c",
        "SELECT 1;",
    ]

    result = await _run_cmd_async_with_env(cmd, env={"PGPASSWORD": db_password})
    if result.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command failed: {' '.join(cmd)}\n{(result.stderr or '').strip()}",
        )

    if "1" not in (result.stdout or ""):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PostgreSQL verification failed (expected SELECT 1 to return 1)",
        )


async def _backup_directory_to_tar(source_dir: Path, dest_tar: Path) -> dict:
    dest_tar.parent.mkdir(parents=True, exist_ok=True)
    if not source_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Directory not found: {source_dir}",
        )

    with tarfile.open(dest_tar, "w:gz") as tf:
        tf.add(source_dir, arcname=source_dir.name)

    return {
        "path": str(dest_tar),
        "sha256": _sha256_file(dest_tar),
        "size_bytes": dest_tar.stat().st_size,
    }


def _create_manifest_base(backup_id: str, include_influx: bool) -> dict:
    return {
        "backup_id": backup_id,
        "created_at": _utc_now_iso(),
        "completed_at": None,
        "included": {
            "postgres": True,
            "influxdb": bool(include_influx),
        },
        "containers": {
            "postgres_primary": _POSTGRES_PRIMARY_CONTAINER,
            "postgres_shadow": _POSTGRES_SHADOW_CONTAINER,
            "influxdb": _INFLUX_CONTAINER,
        },
        "artifacts": {},
        "restore_order": ["postgres", "influxdb"],
    }


async def create_backup_set(request: BackupSetCreateRequest) -> BackupSetCreateResponse:
    async with _backup_lock:
        backup_id = str(uuid.uuid4())
        artifact_store = _get_artifact_store_client_or_none()
        if artifact_store is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Artifact store not configured; cannot upload backup archive",
            )

        # Enforce single-path behavior: MinIO is the only artifact store.
        # Local filesystem is used for staging only and is always cleaned up.
        staging_root = _backup_root()

        manifest = _create_manifest_base(backup_id, include_influx=request.include_influx)

        key = _backup_archive_object_key(backup_id)
        await _db_execute(
            """
            INSERT INTO aico_core.backup_sets (
                backup_id, created_at, completed_at, status, included_json, manifest_json,
                object_key, size_bytes, sha256, created_by_user_uuid, deleted_at
            ) VALUES (
                $1, NOW(), NULL, 'creating', $2::jsonb, NULL,
                $3, NULL, NULL, NULL, NULL
            );
            """,
            backup_id,
            json.dumps(manifest.get("included") or {}),
            key,
        )

        try:
            with tempfile.TemporaryDirectory(dir=str(staging_root)) as td:
                backup_dir = Path(td) / backup_id
                backup_dir.mkdir(parents=True, exist_ok=True)

                manifest["artifacts"]["postgres"] = await _postgres_dump(backup_dir)

                if request.include_influx:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="InfluxDB backup is not supported in the dockerized setup yet",
                    )

                manifest["completed_at"] = _utc_now_iso()
                (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

                info = BackupSetInfo(
                    backup_id=backup_id,
                    created_at=manifest["created_at"],
                    path=key,
                    included=manifest["included"],
                )

                try:
                    # Create archive and upload to artifact store (MinIO).
                    tar_path = Path(td) / f"{backup_id}.tar.gz"
                    with tarfile.open(tar_path, "w:gz") as tf:
                        tf.add(backup_dir, arcname=backup_dir.name)

                    artifact_store.put_file(key=key, file_path=str(tar_path), content_type="application/gzip")
                    await _db_execute(
                        """
                        UPDATE aico_core.backup_sets
                        SET completed_at = NOW(),
                            status = 'available',
                            included_json = $2::jsonb,
                            manifest_json = $3::jsonb,
                            size_bytes = $4,
                            sha256 = $5
                        WHERE backup_id = $1 AND deleted_at IS NULL;
                        """,
                        backup_id,
                        json.dumps(manifest.get("included") or {}),
                        json.dumps(manifest),
                        int(tar_path.stat().st_size),
                        _sha256_file(tar_path),
                    )
                finally:
                    try:
                        if tar_path.exists():
                            tar_path.unlink()
                    except Exception:
                        pass

            return BackupSetCreateResponse(
                success=True,
                backup_set=info,
                message="Backup set created",
            )

        except Exception as e:
            logger.error(f"Backup set creation failed: {e}")
            try:
                await _db_execute(
                    "UPDATE aico_core.backup_sets SET status = 'error' WHERE backup_id = $1;",
                    backup_id,
                )
            except Exception:
                pass
            raise


def list_backup_sets() -> BackupSetListResponse:
    raise RuntimeError("list_backup_sets must be called via list_backup_sets_async")


async def list_backup_sets_async() -> BackupSetListResponse:
    rows = await _db_fetch(
        """
        SELECT backup_id, created_at, included_json, object_key
        FROM aico_core.backup_sets
        WHERE deleted_at IS NULL
        ORDER BY created_at DESC;
        """
    )
    sets: list[BackupSetInfo] = []
    for r in rows:
        included = r.get("included_json")
        if isinstance(included, str):
            try:
                included = json.loads(included)
            except Exception:
                included = {}

        sets.append(
            BackupSetInfo(
                backup_id=r["backup_id"],
                created_at=r["created_at"].isoformat(),
                path=str(r["object_key"]),
                included=included or {},
            )
        )
    return BackupSetListResponse(backup_sets=sets, total_count=len(sets))


def get_backup_set_status(backup_id: str) -> BackupSetStatusResponse:
    raise RuntimeError("get_backup_set_status must be called via get_backup_set_status_async")


async def get_backup_set_status_async(backup_id: str) -> BackupSetStatusResponse:
    row = await _db_fetchrow(
        """
        SELECT backup_id, created_at, included_json, manifest_json, object_key
        FROM aico_core.backup_sets
        WHERE backup_id = $1 AND deleted_at IS NULL
        LIMIT 1;
        """,
        backup_id,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup set not found")

    included = row.get("included_json")
    if isinstance(included, str):
        try:
            included = json.loads(included)
        except Exception:
            included = {}

    manifest = row.get("manifest_json")
    if isinstance(manifest, str):
        try:
            manifest = json.loads(manifest)
        except Exception:
            manifest = None

    info = BackupSetInfo(
        backup_id=row["backup_id"],
        created_at=row["created_at"].isoformat(),
        path=str(row["object_key"]),
        included=included or {},
    )
    return BackupSetStatusResponse(backup_set=info, manifest=manifest)


def download_backup_set(backup_id: str) -> FileResponse:
    artifact_store = _get_artifact_store_client_or_none()
    if artifact_store is not None:
        key = _backup_archive_object_key(backup_id)
        if artifact_store.object_exists(key=key):
            return StreamingResponse(
                artifact_store.get_object_iter(key=key),
                media_type="application/gzip",
                headers={"Content-Disposition": f"attachment; filename={backup_id}.tar.gz"},
            )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup archive not found")


def delete_backup_set(backup_id: str) -> BackupSetDeleteResponse:
    raise RuntimeError("delete_backup_set must be called via delete_backup_set_async")


async def delete_backup_set_async(backup_id: str) -> BackupSetDeleteResponse:
    row = await _db_fetchrow(
        """
        SELECT backup_id, object_key
        FROM aico_core.backup_sets
        WHERE backup_id = $1 AND deleted_at IS NULL
        LIMIT 1;
        """,
        backup_id,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup set not found")

    deleted_dir = False
    deleted_archive = False

    # Best-effort: delete remote archive from artifact store (MinIO) so we don't
    # accumulate orphaned objects.
    artifact_store = _get_artifact_store_client_or_none()
    if artifact_store is not None:
        key = _backup_archive_object_key(backup_id)
        try:
            if artifact_store.object_exists(key=key):
                artifact_store.delete_object(key=key)
        except Exception:
            pass

    freed_bytes = 0

    await _db_execute(
        "UPDATE aico_core.backup_sets SET deleted_at = NOW(), status = 'deleted' WHERE backup_id = $1;",
        backup_id,
    )

    return BackupSetDeleteResponse(
        success=True,
        backup_id=backup_id,
        deleted_dir=deleted_dir,
        deleted_archive=deleted_archive,
        freed_bytes=freed_bytes,
        message="Backup set deleted",
    )


def prune_backup_sets(request: BackupSetPruneRequest) -> BackupSetPruneResponse:
    raise RuntimeError("prune_backup_sets must be called via prune_backup_sets_async")


async def prune_backup_sets_async(request: BackupSetPruneRequest) -> BackupSetPruneResponse:
    rows = await _db_fetch(
        """
        SELECT backup_id, created_at
        FROM aico_core.backup_sets
        WHERE deleted_at IS NULL
        ORDER BY created_at DESC;
        """
    )
    considered_count = len(rows)

    if request.keep_last_n is None and request.older_than_days is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one of keep_last_n or older_than_days",
        )

    # Sort newest first using created_at (ISO-8601 string)
    sorted_sets = rows

    to_delete_ids: set[str] = set()

    if request.keep_last_n is not None:
        if request.keep_last_n < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="keep_last_n must be >= 0")
        for entry in sorted_sets[request.keep_last_n :]:
            bid = entry.get("backup_id")
            if bid:
                to_delete_ids.add(bid)

    if request.older_than_days is not None:
        if request.older_than_days < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="older_than_days must be >= 0")
        cutoff = datetime.now(UTC).timestamp() - (request.older_than_days * 86400)
        for entry in sorted_sets:
            created = entry.get("created_at")
            if isinstance(created, datetime) and created.timestamp() < cutoff:
                bid = entry.get("backup_id")
                if bid:
                    to_delete_ids.add(bid)

    would_delete_backup_ids = sorted(to_delete_ids)
    freed_bytes = 0
    deleted_count = 0

    if not request.dry_run:
        for bid in would_delete_backup_ids:
            resp = await delete_backup_set_async(bid)
            deleted_count += 1
            freed_bytes += int(resp.freed_bytes)
    else:
        freed_bytes = 0

    return BackupSetPruneResponse(
        success=True,
        dry_run=bool(request.dry_run),
        considered_count=considered_count,
        deleted_count=deleted_count,
        would_delete_backup_ids=would_delete_backup_ids,
        freed_bytes=freed_bytes,
        message="Backup sets pruned" if not request.dry_run else "Backup sets prune dry-run",
    )


async def upload_backup_set(file: UploadFile, output_path: Optional[str]) -> BackupSetUploadResponse:
    async with _backup_lock:
        artifact_store = _get_artifact_store_client_or_none()
        if artifact_store is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Artifact store not configured")

        tmp_root = AICOPaths.get_data_directory() / "tmp" / "uploads"
        tmp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=str(tmp_root)) as td:
            td_path = Path(td)
            tar_path = td_path / "upload.tar.gz"
            with open(tar_path, "wb") as f:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)

            with tarfile.open(tar_path, "r:gz") as tf:
                members = tf.getmembers()
                manifest_member = next((m for m in members if m.name.endswith("/manifest.json") or m.name == "manifest.json"), None)
                if manifest_member is None:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded archive did not contain a manifest.json")
                manifest_bytes = tf.extractfile(manifest_member).read()  # type: ignore[union-attr]
                manifest = json.loads(manifest_bytes.decode("utf-8"))

            included = manifest.get("included", {})
            imported_backup_id = manifest.get("backup_id")
            if not imported_backup_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="manifest.json missing backup_id")

            key = _backup_archive_object_key(imported_backup_id)
            await _db_execute(
                """
                INSERT INTO aico_core.backup_sets (
                    backup_id, created_at, completed_at, status, included_json, manifest_json,
                    object_key, size_bytes, sha256, created_by_user_uuid, deleted_at
                ) VALUES (
                    $1, NOW(), NOW(), 'available', $2::jsonb, $3::jsonb,
                    $4, $5, $6, NULL, NULL
                );
                """,
                imported_backup_id,
                json.dumps(included),
                json.dumps(manifest),
                key,
                int(tar_path.stat().st_size),
                _sha256_file(tar_path),
            )
            artifact_store.put_file(key=key, file_path=str(tar_path), content_type="application/gzip")

            return BackupSetUploadResponse(success=True, backup_id=imported_backup_id, message="Backup set uploaded")


async def restore_backup_set(request: BackupSetRestoreRequest) -> BackupSetRestoreResponse:
    async with _backup_lock:
        if not request.confirm_destroy_existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="confirm_destroy_existing must be true for restore operations",
            )

        backup_dir: Path | None = None
        manifest: dict | None = None

        artifact_store = _get_artifact_store_client_or_none()
        if artifact_store is not None:
            key = _backup_archive_object_key(request.backup_id)
            if artifact_store.object_exists(key=key):
                tmp_root = AICOPaths.get_data_directory() / "tmp" / "restore"
                tmp_root.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(dir=str(tmp_root)) as td:
                    td_path = Path(td)
                    tar_path = td_path / f"{request.backup_id}.tar.gz"
                    with open(tar_path, "wb") as f:
                        for chunk in artifact_store.get_object_iter(key=key):
                            f.write(chunk)

                    with tarfile.open(tar_path, "r:gz") as tf:
                        _safe_extract_tar(tf, td_path)

                    extracted = None
                    for p in td_path.iterdir():
                        if p.is_dir() and (p / "manifest.json").exists():
                            extracted = p
                            break

                    if extracted is None:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Backup archive did not contain a manifest.json",
                        )

                    backup_dir = extracted
                    manifest = json.loads((backup_dir / "manifest.json").read_text())

                    # Proceed with restore while the temp dir exists.
                    artifacts = manifest.get("artifacts", {})
                    pg_dump_rel = artifacts.get("postgres", {}).get("path")
                    if not pg_dump_rel:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Backup set missing postgres artifact",
                        )

                    pg_dump_path = backup_dir / pg_dump_rel
                    restore_primary = bool(request.restore_to_primary)

                    await _postgres_restore_to(_POSTGRES_SHADOW_CONTAINER, pg_dump_path)
                    await _verify_postgres_container(_POSTGRES_SHADOW_CONTAINER)

                    if restore_primary:
                        await _postgres_restore_to(_POSTGRES_PRIMARY_CONTAINER, pg_dump_path)
                        await _verify_postgres_container(_POSTGRES_PRIMARY_CONTAINER)

                    if manifest.get("included", {}).get("influxdb") and request.restore_influx:
                        url, org, bucket, token = _get_influx_connection_info()

                        influx_dir_rel = artifacts.get("influxdb", {}).get("path")
                        if influx_dir_rel:
                            influx_host_dir = backup_dir / influx_dir_rel
                            container_tmp_dir = "/tmp/aico_influx_restore"
                            container_backup_dir = f"{container_tmp_dir}/backup"

                            await _docker_exec(_INFLUX_CONTAINER, ["rm", "-rf", container_tmp_dir])
                            await _docker_exec(_INFLUX_CONTAINER, ["mkdir", "-p", container_tmp_dir])
                            await _docker_cp_to(_INFLUX_CONTAINER, influx_host_dir, container_backup_dir)

                            await _docker_exec(
                                _INFLUX_CONTAINER,
                                [
                                    "sh",
                                    "-lc",
                                    f"influx restore {container_backup_dir} --org {org} --host http://127.0.0.1:8086 --token $INFLUX_TOKEN",
                                ],
                                env={"INFLUX_TOKEN": token},
                            )

                    return BackupSetRestoreResponse(success=True, message="Backup set restored")

        # Legacy fallback (restore from local filesystem)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup archive not found")
