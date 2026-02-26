import asyncio
import hashlib
import json
import shutil
import subprocess
import tarfile
import time
import uuid
import os
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from aico.core.logging import get_logger
from aico.core.paths import AICOPaths
from aico.core.config import ConfigurationManager
from aico.security.key_manager import AICOKeyManager

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
    root = AICOPaths.get_data_directory() / "backups" / "backup_sets"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _get_host_runtime_dir() -> Optional[Path]:
    value = os.environ.get("AICO_HOST_RUNTIME_DIR")
    if not value:
        return None
    p = Path(value)
    return p if p.exists() else None


def _registry_path() -> Path:
    return _backup_root() / "backup_sets_registry.json"


def _load_registry() -> dict:
    path = _registry_path()
    if not path.exists():
        return {"backup_sets": []}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {"backup_sets": []}


def _save_registry(registry: dict) -> None:
    path = _registry_path()
    path.write_text(json.dumps(registry, indent=2))


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

    db_name = pg_cfg.get("db_name", "aico")
    db_user = pg_cfg.get("user", "postgres")

    # In containers, the system keyring may not be available.
    # Prefer env var injection via docker-compose and fall back to keyring for local dev.
    db_password = os.environ.get("AICO_PG_PASSWORD") or ""
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

    # Prefer env var injection in containers, fall back to keyring for local dev.
    token = os.environ.get("AICO_INFLUX_ADMIN_TOKEN") or ""
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
            "chromadb": True,
            "lmdb": True,
            "influxdb": bool(include_influx),
        },
        "containers": {
            "postgres_primary": _POSTGRES_PRIMARY_CONTAINER,
            "postgres_shadow": _POSTGRES_SHADOW_CONTAINER,
            "influxdb": _INFLUX_CONTAINER,
        },
        "artifacts": {},
        "restore_order": ["postgres", "chromadb", "lmdb", "influxdb"],
    }


async def create_backup_set(request: BackupSetCreateRequest) -> BackupSetCreateResponse:
    async with _backup_lock:
        backup_id = str(uuid.uuid4())
        root = _backup_root()

        target_root = Path(request.output_path) if request.output_path else root
        target_root.mkdir(parents=True, exist_ok=True)

        backup_dir = target_root / backup_id
        backup_dir.mkdir(parents=True, exist_ok=True)

        manifest = _create_manifest_base(backup_id, include_influx=request.include_influx)

        try:
            manifest["artifacts"]["postgres"] = await _postgres_dump(backup_dir)

            host_runtime = _get_host_runtime_dir()

            # In dockerized mode, Chroma/LMDB may still live on the host runtime directory.
            # Prefer that mounted location when present so backups reflect the actual live data.
            chroma_src = (
                (host_runtime / "data" / "memory" / "semantic")
                if host_runtime is not None
                else AICOPaths.get_semantic_memory_path()
            )
            chroma_tar = backup_dir / "chromadb" / "chromadb.tar.gz"
            chroma_meta = await _backup_directory_to_tar(chroma_src, chroma_tar)
            manifest["artifacts"]["chromadb"] = {
                "path": str(chroma_tar.relative_to(backup_dir)),
                "sha256": chroma_meta["sha256"],
                "size_bytes": chroma_meta["size_bytes"],
            }

            lmdb_src = (
                (host_runtime / "data" / "memory" / "working")
                if host_runtime is not None
                else AICOPaths.get_working_memory_path()
            )
            lmdb_tar = backup_dir / "lmdb" / "lmdb.tar.gz"
            lmdb_meta = await _backup_directory_to_tar(lmdb_src, lmdb_tar)
            manifest["artifacts"]["lmdb"] = {
                "path": str(lmdb_tar.relative_to(backup_dir)),
                "sha256": lmdb_meta["sha256"],
                "size_bytes": lmdb_meta["size_bytes"],
            }

            if request.include_influx:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="InfluxDB backup is not supported in the dockerized setup yet",
                )

            manifest["completed_at"] = _utc_now_iso()
            (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

            registry = _load_registry()
            registry["backup_sets"].append(
                {
                    "backup_id": backup_id,
                    "created_at": manifest["created_at"],
                    "path": str(backup_dir),
                    "included": manifest["included"],
                }
            )
            _save_registry(registry)

            info = BackupSetInfo(
                backup_id=backup_id,
                created_at=manifest["created_at"],
                path=str(backup_dir),
                included=manifest["included"],
            )

            return BackupSetCreateResponse(
                success=True,
                backup_set=info,
                message="Backup set created",
            )

        except Exception as e:
            logger.error(f"Backup set creation failed: {e}")
            try:
                shutil.rmtree(backup_dir)
            except Exception:
                pass
            raise


def list_backup_sets() -> BackupSetListResponse:
    registry = _load_registry()
    sets = [BackupSetInfo(**b) for b in registry.get("backup_sets", [])]
    sets.sort(key=lambda s: s.created_at, reverse=True)
    return BackupSetListResponse(backup_sets=sets, total_count=len(sets))


def get_backup_set_status(backup_id: str) -> BackupSetStatusResponse:
    registry = _load_registry()
    match = next((b for b in registry.get("backup_sets", []) if b.get("backup_id") == backup_id), None)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup set not found")

    manifest_path = Path(match["path"]) / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None

    return BackupSetStatusResponse(
        backup_set=BackupSetInfo(**match),
        manifest=manifest,
    )


def download_backup_set(backup_id: str) -> FileResponse:
    registry = _load_registry()
    match = next((b for b in registry.get("backup_sets", []) if b.get("backup_id") == backup_id), None)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup set not found")

    backup_dir = Path(match["path"])
    if not backup_dir.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup set directory missing")

    tar_path = backup_dir.parent / f"{backup_id}.tar.gz"

    with tarfile.open(tar_path, "w:gz") as tf:
        tf.add(backup_dir, arcname=backup_dir.name)

    return FileResponse(
        path=str(tar_path),
        filename=tar_path.name,
        media_type="application/gzip",
    )


def delete_backup_set(backup_id: str) -> BackupSetDeleteResponse:
    registry = _load_registry()
    backup_sets = list(registry.get("backup_sets", []))

    match = next((b for b in backup_sets if b.get("backup_id") == backup_id), None)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup set not found")

    backup_dir = Path(match["path"])
    tar_path = backup_dir.parent / f"{backup_id}.tar.gz"

    freed_bytes = _safe_dir_size_bytes(backup_dir) + _safe_dir_size_bytes(tar_path)

    deleted_dir = False
    deleted_archive = False

    if backup_dir.exists():
        shutil.rmtree(backup_dir)
        deleted_dir = True

    if tar_path.exists():
        tar_path.unlink()
        deleted_archive = True

    registry["backup_sets"] = [b for b in backup_sets if b.get("backup_id") != backup_id]
    _save_registry(registry)

    return BackupSetDeleteResponse(
        success=True,
        backup_id=backup_id,
        deleted_dir=deleted_dir,
        deleted_archive=deleted_archive,
        freed_bytes=freed_bytes,
        message="Backup set deleted",
    )


def prune_backup_sets(request: BackupSetPruneRequest) -> BackupSetPruneResponse:
    registry = _load_registry()
    backup_sets = list(registry.get("backup_sets", []))
    considered_count = len(backup_sets)

    if request.keep_last_n is None and request.older_than_days is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one of keep_last_n or older_than_days",
        )

    # Sort newest first using created_at (ISO-8601 string)
    def _parse_created_at(entry: dict) -> datetime:
        created_at = entry.get("created_at")
        if not created_at:
            return datetime.min
        try:
            # Accept both 'Z' and offset-aware strings
            return datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except Exception:
            return datetime.min

    sorted_sets = sorted(backup_sets, key=_parse_created_at, reverse=True)

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
            created = _parse_created_at(entry)
            if created is datetime.min:
                continue
            if created.timestamp() < cutoff:
                bid = entry.get("backup_id")
                if bid:
                    to_delete_ids.add(bid)

    would_delete_backup_ids = sorted(to_delete_ids)
    freed_bytes = 0
    deleted_count = 0

    if not request.dry_run:
        for bid in would_delete_backup_ids:
            # Reuse delete logic and sum bytes
            resp = delete_backup_set(bid)
            deleted_count += 1
            freed_bytes += int(resp.freed_bytes)
    else:
        # Estimate bytes without deleting
        id_to_entry = {b.get("backup_id"): b for b in backup_sets if b.get("backup_id")}
        for bid in would_delete_backup_ids:
            entry = id_to_entry.get(bid)
            if not entry:
                continue
            backup_dir = Path(entry["path"])
            tar_path = backup_dir.parent / f"{bid}.tar.gz"
            freed_bytes += _safe_dir_size_bytes(backup_dir) + _safe_dir_size_bytes(tar_path)

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
        import_id = str(uuid.uuid4())
        root = Path(output_path) if output_path else _backup_root()
        root.mkdir(parents=True, exist_ok=True)

        staging_dir = root / f".upload_{import_id}"
        staging_dir.mkdir(parents=True, exist_ok=True)

        tar_path = staging_dir / "upload.tar.gz"
        with open(tar_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)

        with tarfile.open(tar_path, "r:gz") as tf:
            _safe_extract_tar(tf, staging_dir)

        extracted_dir = None
        for p in staging_dir.iterdir():
            if p.is_dir() and (p / "manifest.json").exists():
                extracted_dir = p
                break

        if extracted_dir is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded archive did not contain a manifest.json")

        manifest = json.loads((extracted_dir / "manifest.json").read_text())
        included = manifest.get("included", {})
        imported_backup_id = manifest.get("backup_id") or extracted_dir.name

        final_dir = root / imported_backup_id
        if final_dir.exists():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Backup set already exists")
        shutil.move(str(extracted_dir), str(final_dir))
        shutil.rmtree(staging_dir, ignore_errors=True)

        registry = _load_registry()
        registry["backup_sets"].append(
            {
                "backup_id": imported_backup_id,
                "created_at": manifest.get("created_at") or _utc_now_iso(),
                "path": str(final_dir),
                "included": included,
            }
        )
        _save_registry(registry)

        return BackupSetUploadResponse(
            success=True,
            backup_id=imported_backup_id,
            message="Backup set uploaded",
        )


async def restore_backup_set(request: BackupSetRestoreRequest) -> BackupSetRestoreResponse:
    async with _backup_lock:
        registry = _load_registry()
        match = next((b for b in registry.get("backup_sets", []) if b.get("backup_id") == request.backup_id), None)
        if not match:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup set not found")

        backup_dir = Path(match["path"])
        manifest_path = backup_dir / "manifest.json"
        if not manifest_path.exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup set missing manifest.json")

        manifest = json.loads(manifest_path.read_text())

        if not request.confirm_destroy_existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="confirm_destroy_existing must be true for restore operations",
            )

        artifacts = manifest.get("artifacts", {})

        pg_dump_rel = artifacts.get("postgres", {}).get("path")
        if not pg_dump_rel:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup set missing postgres artifact")

        pg_dump_path = backup_dir / pg_dump_rel

        restore_primary = bool(request.restore_to_primary)

        await _postgres_restore_to(_POSTGRES_SHADOW_CONTAINER, pg_dump_path)
        await _verify_postgres_container(_POSTGRES_SHADOW_CONTAINER)

        if restore_primary:
            await _postgres_restore_to(_POSTGRES_PRIMARY_CONTAINER, pg_dump_path)
            await _verify_postgres_container(_POSTGRES_PRIMARY_CONTAINER)

        chroma_rel = artifacts.get("chromadb", {}).get("path")
        if chroma_rel:
            chroma_tar = backup_dir / chroma_rel
            target = AICOPaths.get_semantic_memory_path()
            pre = target.parent / f"{target.name}.pre_restore_{int(time.time())}"
            if target.exists():
                shutil.copytree(target, pre)
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)
            with tarfile.open(chroma_tar, "r:gz") as tf:
                _safe_extract_tar(tf, target.parent)

        lmdb_rel = artifacts.get("lmdb", {}).get("path")
        if lmdb_rel:
            lmdb_tar = backup_dir / lmdb_rel
            target = AICOPaths.get_working_memory_path()
            pre = target.parent / f"{target.name}.pre_restore_{int(time.time())}"
            if target.exists():
                shutil.copytree(target, pre)
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)
            with tarfile.open(lmdb_tar, "r:gz") as tf:
                _safe_extract_tar(tf, target.parent)

        if manifest.get("included", {}).get("influxdb"):
            if request.restore_influx:
                url, org, bucket, token = _get_influx_connection_info()

                influx_dir_rel = artifacts.get("influxdb", {}).get("path")
                if influx_dir_rel:
                    influx_host_dir = backup_dir / influx_dir_rel
                    container_tmp_dir = "/tmp/aico_influx_restore"
                    container_backup_dir = f"{container_tmp_dir}/backup"

                    await _docker_exec(_INFLUX_CONTAINER, ["rm", "-rf", container_tmp_dir])
                    await _docker_exec(_INFLUX_CONTAINER, ["mkdir", "-p", container_tmp_dir])
                    # docker cp copies the source directory into the destination directory
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

        return BackupSetRestoreResponse(
            success=True,
            message="Backup set restored",
        )
