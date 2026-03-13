import asyncio
import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.core.paths import AICOPaths
from aico.data.postgres.connection import get_connection
from aico.security.key_manager import AICOKeyManager

logger = get_logger("core.services.backup_sets_service")

_POSTGRES_PRIMARY_CONTAINER = "aico-postgres"
_POSTGRES_SHADOW_CONTAINER = "aico-postgres-shadow"
_INFLUX_CONTAINER = "aico-influxdb"
_BACKUP_ARCHIVE_OBJECT_PREFIX = "backups/backup_sets"
_BACKUP_TRASH_OBJECT_PREFIX = "backups/trash/backup_sets"
_backup_lock = asyncio.Lock()


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _backup_root() -> Path:
    root = AICOPaths.get_data_directory() / "tmp" / "backup_sets"
    root.mkdir(parents=True, exist_ok=True)
    return root


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


def _backup_archive_object_key(backup_id: str) -> str:
    return f"{_BACKUP_ARCHIVE_OBJECT_PREFIX}/{backup_id}.tar.gz"


def _backup_trash_object_key(backup_id: str) -> str:
    return f"{_BACKUP_TRASH_OBJECT_PREFIX}/{backup_id}.tar.gz"


def _run_cmd(cmd: list[str], env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(cmd, capture_output=True, text=True, env=merged_env)


async def _run_cmd_async(cmd: list[str], env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess:
    return await asyncio.to_thread(_run_cmd, cmd, env)


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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="PostgreSQL password not configured")

    return db_name, db_user, db_password


def _get_pg_host_port() -> tuple[str, str]:
    host = os.environ.get("AICO_PG_HOST") or "postgres"
    port = os.environ.get("AICO_PG_PORT") or "5432"
    return host, port


async def _postgres_dump(backup_dir: Path) -> dict:
    db_name, db_user, db_password = _get_pg_connection_info()
    host, port = _get_pg_host_port()
    host_dest = backup_dir / "postgres" / "pgdump.dump"
    host_dest.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "pg_dump", "-Fc", "-Z", "6", "-f", str(host_dest), "-U", db_user, "-d", db_name, "-h", host, "-p", str(port),
    ]
    result = await _run_cmd_async(cmd, env={"PGPASSWORD": db_password})
    if result.returncode != 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=(result.stderr or "").strip())

    return {
        "path": str(host_dest.relative_to(backup_dir)),
        "sha256": _sha256_file(host_dest),
        "size_bytes": host_dest.stat().st_size,
        "format": "pg_dump_custom",
    }


async def _postgres_restore_to(container: str, dump_path: Path) -> None:
    db_name, db_user, db_password = _get_pg_connection_info()
    host = "postgres" if container == _POSTGRES_PRIMARY_CONTAINER else "postgres-shadow"
    cmd = [
        "pg_restore", "--clean", "--if-exists", "--no-owner", "--no-privileges", "-U", db_user, "-d", db_name,
        "-h", host, "-p", "5432", str(dump_path),
    ]
    result = await _run_cmd_async(cmd, env={"PGPASSWORD": db_password})
    if result.returncode != 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=(result.stderr or "").strip())


async def _verify_postgres_container(container: str) -> None:
    db_name, db_user, db_password = _get_pg_connection_info()
    host = "postgres" if container == _POSTGRES_PRIMARY_CONTAINER else "postgres-shadow"
    cmd = ["psql", "-U", db_user, "-d", db_name, "-h", host, "-p", "5432", "-t", "-c", "SELECT 1;"]
    result = await _run_cmd_async(cmd, env={"PGPASSWORD": db_password})
    if result.returncode != 0 or "1" not in (result.stdout or ""):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="PostgreSQL verification failed")


def _create_manifest_base(backup_id: str, include_influx: bool) -> dict:
    return {
        "backup_id": backup_id,
        "created_at": _utc_now_iso(),
        "completed_at": None,
        "included": {"postgres": True, "influxdb": bool(include_influx)},
        "containers": {
            "postgres_primary": _POSTGRES_PRIMARY_CONTAINER,
            "postgres_shadow": _POSTGRES_SHADOW_CONTAINER,
            "influxdb": _INFLUX_CONTAINER,
        },
        "artifacts": {},
        "restore_order": ["postgres", "influxdb"],
    }


async def create_backup_set(*, output_path: str | None, include_influx: bool, created_by_user_uuid: str | None) -> dict:
    async with _backup_lock:
        backup_id = str(uuid.uuid4())
        artifact_store = _get_artifact_store_client_or_none()
        if artifact_store is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Artifact store not configured")

        staging_root = _backup_root()
        manifest = _create_manifest_base(backup_id, include_influx=include_influx)
        key = _backup_archive_object_key(backup_id)
        await _db_execute(
            """
            INSERT INTO aico_core.backup_sets (
                backup_id, created_at, completed_at, status, included_json, manifest_json,
                object_key, size_bytes, sha256, created_by_user_uuid, deleted_at
            ) VALUES (
                $1, NOW(), NULL, 'creating', $2::jsonb, NULL,
                $3, NULL, NULL, $4, NULL
            );
            """,
            backup_id,
            json.dumps(manifest.get("included") or {}),
            key,
            created_by_user_uuid,
        )

        try:
            with tempfile.TemporaryDirectory(dir=str(staging_root)) as td:
                backup_dir = Path(td) / backup_id
                backup_dir.mkdir(parents=True, exist_ok=True)
                manifest["artifacts"]["postgres"] = await _postgres_dump(backup_dir)

                if include_influx:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="InfluxDB backup is not supported yet")

                manifest["completed_at"] = _utc_now_iso()
                (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
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
            return {
                "success": True,
                "backup_set": {
                    "backup_id": backup_id,
                    "created_at": manifest["created_at"],
                    "path": key,
                    "included": manifest["included"],
                    "status": "available",
                    "deleted_at": None,
                    "deleted_by_user_uuid": None,
                },
                "message": "Backup set created",
            }
        except Exception:
            try:
                await _db_execute("UPDATE aico_core.backup_sets SET status = 'error' WHERE backup_id = $1;", backup_id)
            except Exception:
                pass
            raise


async def list_backup_sets_async_with_options(*, include_deleted: bool) -> dict:
    rows = await _db_fetch(
        """
        SELECT backup_id, created_at, included_json, object_key, status, deleted_at, deleted_by_user_uuid
        FROM aico_core.backup_sets
        WHERE ($1::boolean = TRUE) OR deleted_at IS NULL
        ORDER BY created_at DESC;
        """,
        bool(include_deleted),
    )
    sets = []
    for r in rows:
        included = r.get("included_json")
        if isinstance(included, str):
            try:
                included = json.loads(included)
            except Exception:
                included = {}
        sets.append({
            "backup_id": r["backup_id"],
            "created_at": r["created_at"].isoformat(),
            "path": str(r["object_key"]),
            "included": included or {},
            "status": str(r.get("status")) if r.get("status") is not None else None,
            "deleted_at": r["deleted_at"].isoformat() if isinstance(r.get("deleted_at"), datetime) else (str(r.get("deleted_at")) if r.get("deleted_at") else None),
            "deleted_by_user_uuid": str(r.get("deleted_by_user_uuid")) if r.get("deleted_by_user_uuid") else None,
        })
    return {"backup_sets": sets, "total_count": len(sets)}


async def get_backup_set_status_async(backup_id: str) -> dict:
    row = await _db_fetchrow(
        """
        SELECT backup_id, created_at, included_json, manifest_json, object_key, status, deleted_at, deleted_by_user_uuid
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
    return {
        "backup_set": {
            "backup_id": row["backup_id"],
            "created_at": row["created_at"].isoformat(),
            "path": str(row["object_key"]),
            "included": included or {},
            "status": str(row.get("status")) if row.get("status") is not None else None,
            "deleted_at": None,
            "deleted_by_user_uuid": None,
        },
        "manifest": manifest,
    }


async def get_backup_set_download_url_async(backup_id: str, *, expires_seconds: int = 300) -> str:
    row = await _db_fetchrow(
        """
        SELECT backup_id, object_key, deleted_at
        FROM aico_core.backup_sets
        WHERE backup_id = $1 AND deleted_at IS NULL
        LIMIT 1;
        """,
        backup_id,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup set not found")
    artifact_store = _get_artifact_store_client_or_none()
    if artifact_store is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Artifact store not configured")
    key = str(row.get("object_key") or _backup_archive_object_key(backup_id))
    if not artifact_store.object_exists(key=key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup archive not found")
    return artifact_store.generate_presigned_get_url(key=key, expires_seconds=int(expires_seconds))


async def delete_backup_set_async(backup_id: str, *, deleted_by_user_uuid: str | None = None) -> dict:
    row = await _db_fetchrow(
        """
        SELECT backup_id, object_key, deleted_at
        FROM aico_core.backup_sets
        WHERE backup_id = $1
        LIMIT 1;
        """,
        backup_id,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup set not found")
    if row.get("deleted_at") is not None:
        return {"success": True, "backup_id": backup_id, "deleted_dir": False, "deleted_archive": False, "freed_bytes": 0, "message": "Backup set already deleted"}
    deleted_archive = False
    freed_bytes = 0
    artifact_store = _get_artifact_store_client_or_none()
    if artifact_store is not None:
        key = str(row.get("object_key") or _backup_archive_object_key(backup_id))
        trash_key = _backup_trash_object_key(backup_id)
        try:
            if artifact_store.object_exists(key=key):
                object_size = artifact_store.get_object_size(key=key)
                artifact_store.move_object(source_key=key, dest_key=trash_key)
                deleted_archive = True
                freed_bytes = int(object_size or 0)
        except Exception:
            pass
    await _db_execute(
        """
        UPDATE aico_core.backup_sets
        SET deleted_at = NOW(),
            deleted_by_user_uuid = $2,
            status = 'deleted',
            object_key = $3
        WHERE backup_id = $1;
        """,
        backup_id,
        deleted_by_user_uuid,
        _backup_trash_object_key(backup_id),
    )
    return {"success": True, "backup_id": backup_id, "deleted_dir": False, "deleted_archive": deleted_archive, "freed_bytes": freed_bytes, "message": "Backup set deleted"}


async def purge_backup_set_async(backup_id: str) -> dict:
    row = await _db_fetchrow(
        """
        SELECT backup_id, object_key
        FROM aico_core.backup_sets
        WHERE backup_id = $1
        LIMIT 1;
        """,
        backup_id,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup set not found")
    deleted_archive = False
    freed_bytes = 0
    artifact_store = _get_artifact_store_client_or_none()
    if artifact_store is not None:
        key = str(row.get("object_key") or _backup_trash_object_key(backup_id))
        try:
            if artifact_store.object_exists(key=key):
                object_size = artifact_store.get_object_size(key=key)
                artifact_store.delete_object(key=key)
                deleted_archive = True
                freed_bytes = int(object_size or 0)
        except Exception:
            pass
    await _db_execute("DELETE FROM aico_core.backup_sets WHERE backup_id = $1;", backup_id)
    return {"success": True, "backup_id": backup_id, "deleted_dir": False, "deleted_archive": deleted_archive, "freed_bytes": freed_bytes, "message": "Backup set purged"}


async def restore_backup_set(*, backup_id: str, confirm_destroy_existing: bool, restore_to_primary: bool, restore_influx: bool) -> dict:
    async with _backup_lock:
        if not confirm_destroy_existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="confirm_destroy_existing must be true")
        artifact_store = _get_artifact_store_client_or_none()
        if artifact_store is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Artifact store not configured")
        key = _backup_archive_object_key(backup_id)
        if not artifact_store.object_exists(key=key):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup archive not found")
        staging_root = _backup_root()
        with tempfile.TemporaryDirectory(dir=str(staging_root)) as td:
            td_path = Path(td)
            tar_path = td_path / f"{backup_id}.tar.gz"
            artifact_store.get_file(key=key, destination_path=str(tar_path))
            with tarfile.open(tar_path, "r:gz") as tf:
                tf.extractall(td_path)
            backup_dir = td_path / backup_id
            manifest = json.loads((backup_dir / "manifest.json").read_text())
            pg_dump_rel = (((manifest.get("artifacts") or {}).get("postgres") or {}).get("path"))
            if not pg_dump_rel:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Backup manifest missing postgres artifact")
            dump_path = backup_dir / pg_dump_rel
            await _postgres_restore_to(_POSTGRES_SHADOW_CONTAINER, dump_path)
            await _verify_postgres_container(_POSTGRES_SHADOW_CONTAINER)
            if restore_to_primary:
                await _postgres_restore_to(_POSTGRES_PRIMARY_CONTAINER, dump_path)
                await _verify_postgres_container(_POSTGRES_PRIMARY_CONTAINER)
            if restore_influx and ((manifest.get("included") or {}).get("influxdb")):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="InfluxDB restore is not supported yet")
        return {"success": True, "message": "Backup set restored"}
