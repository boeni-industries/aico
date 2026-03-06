"""AICO CLI Deploy Commands

High-level orchestration for deploying and bootstrapping infrastructure
backends (Postgres, InfluxDB, Loki, and Grafana). These commands are intended to be used
in CI/CD pipelines or for one-shot local provisioning.
"""

import sys
import subprocess
import secrets
import os
import asyncio
import stat
from pathlib import Path
from typing import Tuple
import uuid
import yaml
import json

import typer
from rich.console import Console


# Add shared module to path for CLI usage (mirrors other CLI modules)
if getattr(sys, "frozen", False):
    shared_path = Path(sys._MEIPASS) / "shared"  # type: ignore[attr-defined]
else:
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from cli.utils.formatting import format_error, format_success, format_info, format_warning
from aico.core.config import ConfigurationManager
from aico.security.key_manager import AICOKeyManager


console = Console()


def _get_aico_repo_root() -> Path:
    """Resolve the AICO repo root by walking upwards from this file.

    Note: This repo contains multiple Python projects (backend/cli/shared/modelservice)
    with their own pyproject.toml files. For deploy commands we need the *git root*
    (the top-level AICO repo), otherwise relative component paths resolve incorrectly.
    """

    current = Path(__file__).resolve()

    # Prefer git root if available (most reliable in a multi-pyproject monorepo).
    for parent in [current.parent, *current.parents]:
        if (parent / ".git").exists():
            return parent

    # Fallback: look for repo-level marker files.
    for parent in [current.parent, *current.parents]:
        if (parent / "aico.code-workspace").exists() or (parent / "VERSIONS").exists() or (parent / "Makefile").exists():
            return parent

    # Last resort: assume cli/commands/deploy.py => repo root is three levels up
    return Path(__file__).parent.parent.parent.resolve()


def _resolve_component_path(component_name: str) -> Path:
    """Resolve external component path.

    Resolution order:
    1) Env var override: AICO_COMPONENT_<NAME>_DIR
    2) Config: system.components.<name>.path
    3) Convention default: ../aico-<name> relative to AICO repo root
    """

    env_key = f"AICO_COMPONENT_{component_name.upper()}_DIR"
    if override := os.getenv(env_key):
        return Path(override).expanduser().resolve()

    repo_root = _get_aico_repo_root()

    # Use runtime config (created by `uv run aico config init`).
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    cfg_path = config.get_optional(f"system.components.{component_name}.path", default="")
    if not (isinstance(cfg_path, str) and cfg_path.strip()):
        # Backwards/alternate layout: components.<name>.path at root.
        cfg_path = config.get_optional(f"components.{component_name}.path", default="")

    if isinstance(cfg_path, str) and cfg_path.strip():
        candidate = Path(os.path.expanduser(cfg_path.strip()))
        if not candidate.is_absolute():
            candidate = (repo_root / candidate)
        return candidate.resolve()

    # Convention default
    return (repo_root / f"../aico-{component_name}").resolve()


def _run_compose_file(compose_file: Path, args: list[str], env: dict | None = None, cwd: Path | None = None) -> int:
    """Run docker compose against a specific compose file."""

    if not compose_file.exists():
        console.print(format_error(f"Docker compose file not found: {compose_file}"))
        return 1

    cmd = [
        "docker",
        "compose",
        "-f",
        str(compose_file),
    ] + args

    run_env = os.environ.copy()
    run_env.pop("AICO_MASTER_PASSWORD", None)
    if env:
        run_env.update(env)

    try:
        result = subprocess.run(cmd, check=False, env=run_env, cwd=str(cwd) if cwd else None)
        if result.returncode != 0:
            console.print(
                format_error(
                    f"docker compose command failed with exit code {result.returncode}:\n" + " ".join(cmd)
                )
            )
        return result.returncode
    except FileNotFoundError:
        console.print(format_error("'docker' command not found. Install Docker and ensure it is on your PATH."))
        return 1


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        data[key] = value
    return data


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in sorted(values.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def _get_secrets_dir() -> Path:
    compose_file = _get_compose_file()
    return (compose_file.parent / "secrets").resolve()


def _read_secret_file(path: Path) -> str:
    value = path.read_text(encoding="utf-8").strip()
    if "\n" in value:
        value = value.splitlines()[0].strip()
    return value


def _write_secret_file(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.strip() + "\n", encoding="utf-8")
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def _generate_secure_password(length: int = 32) -> str:
    """Generate a cryptographically secure password."""
    # Use URL-safe base64 encoding for compatibility
    return secrets.token_urlsafe(length)


def _ensure_all_secrets() -> dict[str, str]:
    """
    Ensure ALL required secrets exist before any service starts.

    This is the unified mechanism for dev + prod:
    - Secrets are stored as files under docker/secrets/*
    - docker-compose mounts them into containers as /run/secrets/*
    """
    secrets_dir = _get_secrets_dir()

    # If this environment already ran with docker/.env based credentials (legacy),
    # bootstrap secrets from there to avoid breaking authentication against
    # existing volumes (e.g., Postgres/Influx already initialized).
    compose_file = _get_compose_file()
    legacy_env_file = compose_file.parent / ".env"
    legacy_env = _load_env_file(legacy_env_file) if legacy_env_file.exists() else {}
    legacy_map = {
        "pg_password": "AICO_PG_PASSWORD",
        "influx_admin_password": "AICO_INFLUX_ADMIN_PASSWORD",
        "influx_admin_token": "AICO_INFLUX_ADMIN_TOKEN",
        "api_gateway_jwt_secret": "AICO_API_GATEWAY_JWT_SECRET",
    }

    required = {
        "pg_password": 32,
        "influx_admin_password": 32,
        "influx_admin_token": 48,
        "api_gateway_jwt_secret": 48,
    }

    resolved: dict[str, str] = {}
    updated = False

    for name, length in required.items():
        p = secrets_dir / name
        if p.exists():
            value = _read_secret_file(p)
            if value:
                resolved[name] = value
                continue

        # Bootstrap from legacy docker/.env if available
        legacy_key = legacy_map.get(name)
        if legacy_key:
            legacy_value = legacy_env.get(legacy_key, "").strip()
            if legacy_value:
                _write_secret_file(p, legacy_value)
                resolved[name] = legacy_value
                updated = True
                console.print(format_info(f"Imported legacy secret {name} from docker/.env"))
                continue

        value = _generate_secure_password(length)
        _write_secret_file(p, value)
        resolved[name] = value
        updated = True
        console.print(format_info(f"Generated secret {name}"))

    if updated:
        console.print(format_success("✓ Secrets initialized in docker/secrets/"))

    return resolved

def _get_or_create_postgres_password() -> str:
    """
    Get or create Postgres password - FULLY AUTOMATIC.
    
    Unified mechanism:
    - docker/secrets/pg_password (file)
    
    Returns:
        Postgres password
    """
    secrets = _ensure_all_secrets()
    return secrets["pg_password"]


def _load_deploy_config(config_file: str | None) -> dict:
    if not config_file:
        return {}

    p = Path(config_file).expanduser()
    if not p.exists():
        console.print(format_error(f"Config file not found: {p}"))
        raise typer.Exit(1)

    try:
        raw = p.read_text(encoding="utf-8")
        if p.suffix.lower() == ".json":
            data = json.loads(raw)
        else:
            data = yaml.safe_load(raw)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        console.print(format_error(f"Failed to parse config file {p}: {e}"))
        raise typer.Exit(1)


def _read_master_password_from_file(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        raise ValueError(f"master password file not found: {p}")
    value = p.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"master password file is empty: {p}")
    return value


def _get_master_password(*, master_password_file: str | None, non_interactive: bool) -> str | None:
    if master_password_file:
        return _read_master_password_from_file(master_password_file)

    if pw := os.getenv("AICO_MASTER_PASSWORD"):
        return pw

    if non_interactive:
        return None

    return None


def _authenticate_for_deploy(*, non_interactive: bool, master_password_file: str | None) -> None:
    """Ensure master key + JWT secret exist.

    Supports headless bootstrap via master-password file or AICO_MASTER_PASSWORD.
    """

    config = ConfigurationManager()
    key_manager = AICOKeyManager(config)

    password = _get_master_password(master_password_file=master_password_file, non_interactive=non_interactive)

    if not password and non_interactive and not key_manager.has_stored_key():
        console.print(
            format_error(
                "Non-interactive deploy requires either --master-password-file or AICO_MASTER_PASSWORD "
                "(unless master key already exists in keyring)."
            )
        )
        raise typer.Exit(1)

    try:
        key_manager.authenticate(password=password, interactive=not non_interactive)
    finally:
        if "AICO_MASTER_PASSWORD" in os.environ:
            os.environ.pop("AICO_MASTER_PASSWORD", None)

    try:
        key_manager.get_jwt_secret("api_gateway")
    except Exception as e:
        console.print(format_warning(f"Warning: failed to ensure JWT secret: {e}"))


def _validate_admin_passcode(passcode: str, *, min_length: int) -> None:
    value = passcode.strip()
    if not value:
        raise ValueError("Admin passcode cannot be empty")
    if any(ch.isspace() for ch in value):
        raise ValueError("Admin passcode must not contain whitespace")
    if len(value) < min_length:
        raise ValueError(f"Admin passcode must be at least {min_length} characters")

    has_lower = any(ch.islower() for ch in value)
    has_upper = any(ch.isupper() for ch in value)
    has_digit = any(ch.isdigit() for ch in value)
    has_symbol = any((not ch.isalnum()) for ch in value)

    if not (has_lower and has_upper and has_digit and has_symbol):
        raise ValueError("Admin passcode must include lowercase, uppercase, digit, and symbol")


def _ensure_postgres_password_in_keyring(pg_password: str, *, non_interactive: bool) -> None:
    """Persist the Postgres password into the keyring when available.

    This is required for CLI helpers that expect `AICOKeyManager.get_database_password()` to work.
    """

    config = ConfigurationManager()
    config.initialize(lightweight=True)
    pg_cfg = config.get("postgres", {}) or {}
    user = pg_cfg.get("user", "postgres")

    key_manager = AICOKeyManager(config)

    try:
        existing = key_manager.get_database_password("postgres", username=user)
        if existing:
            return
        key_manager.store_database_password(pg_password, "postgres", username=user)
    except Exception as e:
        if non_interactive:
            console.print(format_warning(f"Warning: could not store Postgres password in keyring: {e}"))
        else:
            console.print(format_warning(f"Warning: could not store Postgres password in keyring: {e}"))


def _bootstrap_postgres(
    *,
    tenant_display_name: str,
    admin_full_name: str,
    admin_pin: str | None,
    primary_language: str | None,
    non_interactive: bool,
) -> tuple[str, str]:
    """Idempotently ensure tenant + admin user + membership + admin role exist."""

    import psycopg2
    from passlib.context import CryptContext

    config = ConfigurationManager()
    config.initialize(lightweight=True)

    pg_cfg = config.get("postgres", {}) or {}
    host = pg_cfg.get("host", "127.0.0.1")
    port = int(pg_cfg.get("port", 5432))
    db_name = pg_cfg.get("db_name", "aico")
    user = pg_cfg.get("user", "postgres")

    key_manager = AICOKeyManager(config)
    pg_password = key_manager.get_database_password("postgres", username=user) or os.getenv("AICO_PG_PASSWORD")
    if not pg_password:
        raise RuntimeError("Postgres password not available; run 'aico deploy pg' first")

    conn = psycopg2.connect(host=host, port=port, dbname=db_name, user=user, password=pg_password)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO aico_core, public;")

            cur.execute(
                "SELECT tenant_id FROM tenants WHERE display_name = %s AND tenant_type = 'deployment' LIMIT 1;",
                (tenant_display_name,),
            )
            row = cur.fetchone()
            if row:
                tenant_id = str(row[0])
            else:
                tenant_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO tenants (
                        tenant_id, tenant_type, display_name, status, primary_language, metadata_json, created_at, updated_at
                    ) VALUES (
                        %s, 'deployment', %s, 'active', %s, NULL, NOW(), NOW()
                    );
                    """,
                    (tenant_id, tenant_display_name, primary_language),
                )

            cur.execute(
                "SELECT uuid FROM user_profiles WHERE full_name = %s AND is_active = TRUE ORDER BY created_at ASC LIMIT 1;",
                (admin_full_name,),
            )
            row = cur.fetchone()
            if row:
                admin_user_uuid = str(row[0])
            else:
                admin_user_uuid = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO user_profiles (uuid, full_name, nickname, user_type, is_active, primary_language, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, TRUE, %s, NOW(), NOW());
                    """,
                    (admin_user_uuid, admin_full_name, None, "person", primary_language or "en"),
                )

            # Ensure the earliest-created non-system user is the bootstrap admin/owner.
            cur.execute(
                """
                SELECT uuid
                FROM user_profiles
                WHERE uuid != %s AND is_active = TRUE
                ORDER BY created_at ASC
                LIMIT 1;
                """,
                ("system_user",),
            )
            row = cur.fetchone()
            bootstrap_user_uuid = str(row[0]) if row else admin_user_uuid

            if admin_pin:
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                pin_bytes = admin_pin.encode("utf-8")
                if len(pin_bytes) > 72:
                    pin_to_hash = pin_bytes[:72].decode("utf-8", errors="ignore")
                else:
                    pin_to_hash = admin_pin
                pin_hash = pwd_context.hash(pin_to_hash)

                cur.execute("SELECT uuid FROM auth_user_credentials WHERE user_uuid = %s;", (admin_user_uuid,))
                auth_row = cur.fetchone()
                if auth_row:
                    cur.execute(
                        "UPDATE auth_user_credentials SET password_hash = %s, updated_at = NOW() WHERE user_uuid = %s;",
                        (pin_hash, admin_user_uuid),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO auth_user_credentials (uuid, user_uuid, password_hash, failed_attempts, created_at, updated_at)
                        VALUES (%s, %s, %s, 0, NOW(), NOW());
                        """,
                        (str(uuid.uuid4()), admin_user_uuid, pin_hash),
                    )

            cur.execute(
                "SELECT membership_id FROM tenant_memberships WHERE tenant_id = %s AND user_id = %s;",
                (tenant_id, bootstrap_user_uuid),
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    """
                    INSERT INTO tenant_memberships (membership_id, tenant_id, user_id, role, created_at)
                    VALUES (%s, %s, %s, 'owner', NOW());
                    """,
                    (str(uuid.uuid4()), tenant_id, bootstrap_user_uuid),
                )

            cur.execute(
                """
                SELECT uuid FROM auth_access_policies
                WHERE user_uuid = %s AND resource_type = 'role' AND permission = 'admin' AND is_active = TRUE
                LIMIT 1;
                """,
                (bootstrap_user_uuid,),
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    """
                    INSERT INTO auth_access_policies (uuid, user_uuid, resource_type, resource_uuid, permission, is_active, created_at)
                    VALUES (%s, %s, 'role', NULL, 'admin', TRUE, NOW());
                    """,
                    (str(uuid.uuid4()), bootstrap_user_uuid),
                )

        conn.commit()
        return tenant_id, bootstrap_user_uuid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _write_deploy_state(tenant_id: str, admin_user_uuid: str) -> None:
    from aico.core.paths import AICOPaths

    runtime_dir = AICOPaths.get_runtime_path()
    path = runtime_dir / "deploy-state.yaml"
    payload = {
        "version": 1,
        "tenant_id": tenant_id,
        "admin_user_uuid": admin_user_uuid,
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")


def _load_deploy_state() -> dict:
    from aico.core.paths import AICOPaths

    runtime_dir = AICOPaths.get_runtime_path()
    path = runtime_dir / "deploy-state.yaml"
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _setup_influx_downsampling(admin_token: str) -> None:
    """
    Configure InfluxDB downsampling tasks and retention policies.
    This is idempotent - safe to run multiple times.
    """
    from influxdb_client import InfluxDBClient, BucketRetentionRules
    
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    url = config.get_optional("influx.url") or "http://127.0.0.1:8086"
    org = config.get_optional("influx.org") or "aico"
    
    try:
        with InfluxDBClient(url=url, token=admin_token, org=org) as client:
            buckets_api = client.buckets_api()
            tasks_api = client.tasks_api()
            orgs_api = client.organizations_api()
            
            # Get org object (needed for task creation)
            orgs = orgs_api.find_organizations(org=org)
            org_obj = orgs[0] if orgs else None
            if not org_obj:
                raise ValueError(f"Organization '{org}' not found")
            
            # 1. Create downsampled bucket with 30-day retention
            existing_buckets = buckets_api.find_buckets().buckets
            downsampled_bucket_name = "aico_telemetry_downsampled"
            
            bucket_exists = any(b.name == downsampled_bucket_name for b in existing_buckets)
            if not bucket_exists:
                retention_rules = BucketRetentionRules(type="expire", every_seconds=2592000)  # 30 days
                buckets_api.create_bucket(
                    bucket_name=downsampled_bucket_name,
                    org=org,
                    retention_rules=retention_rules
                )
                console.print(f"  ✓ Created downsampled bucket (30-day retention)")
            else:
                console.print(f"  ✓ Downsampled bucket already exists")
            
            # 2. Update main bucket to 7-day retention
            main_bucket = next((b for b in existing_buckets if b.name == "aico_telemetry"), None)
            if main_bucket:
                if not main_bucket.retention_rules or main_bucket.retention_rules[0].every_seconds != 604800:
                    main_bucket.retention_rules = [BucketRetentionRules(type="expire", every_seconds=604800)]
                    buckets_api.update_bucket(bucket=main_bucket)
                    console.print(f"  ✓ Updated main bucket to 7-day retention")
                else:
                    console.print(f"  ✓ Main bucket retention already configured")
            
            # 3. Create downsampling tasks (delete existing ones first to update field names)
            existing_tasks = tasks_api.find_tasks()
            # Handle both list and Tasks object response types
            if hasattr(existing_tasks, 'tasks'):
                existing_tasks_list = existing_tasks.tasks
            else:
                existing_tasks_list = existing_tasks if existing_tasks else []
            
            # Delete existing downsampling tasks to recreate with correct field names
            task_names_to_recreate = {
                "downsample_api_requests", "downsample_api_counts", "downsample_messagebus",
                "downsample_scheduler", "downsample_memory_queries", "downsample_model_inference"
            }
            for task in existing_tasks_list:
                if task.name in task_names_to_recreate:
                    try:
                        tasks_api.delete_task(task.id)
                        console.print(f"  ✓ Deleted old task '{task.name}' for recreation")
                    except Exception as e:
                        console.print(f"  ⚠ Could not delete task '{task.name}': {e}")
            
            existing_task_names = set()  # All tasks deleted, recreate all
            
            # IMPORTANT: field names must match backend/core/otel_influx_exporter.py
            # Otherwise downsampled measurements stay empty and Studio shows zeros.
            tasks_to_create = [
                # API gateway
                (
                    "downsample_api_requests",
                    f'from(bucket: "aico_telemetry")'
                    f' |> range(start: -1m)'
                    f' |> filter(fn: (r) => r._measurement == "api_request")'
                    f' |> filter(fn: (r) => r._field == "latency_ms_f" or r._field == "status_code_i")'
                    f' |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)'
                    f' |> set(key: "_measurement", value: "api_request_1m")'
                    f' |> to(bucket: "aico_telemetry_downsampled", org: "{org}")',
                ),
                (
                    "downsample_api_counts",
                    f'from(bucket: "aico_telemetry")'
                    f' |> range(start: -1m)'
                    f' |> filter(fn: (r) => r._measurement == "api_request")'
                    f' |> filter(fn: (r) => r._field == "status_code_i")'
                    f' |> aggregateWindow(every: 1m, fn: count, createEmpty: false)'
                    f' |> set(key: "_measurement", value: "api_request_counts_1m")'
                    f' |> to(bucket: "aico_telemetry_downsampled", org: "{org}")',
                ),

                # Message bus
                (
                    "downsample_messagebus",
                    f'from(bucket: "aico_telemetry")'
                    f' |> range(start: -1m)'
                    f' |> filter(fn: (r) => r._measurement == "messagebus_event")'
                    f' |> filter(fn: (r) => r._field == "message_count_i" or r._field == "processing_time_ms_f")'
                    f' |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)'
                    f' |> set(key: "_measurement", value: "messagebus_event_1m")'
                    f' |> to(bucket: "aico_telemetry_downsampled", org: "{org}")',
                ),

                # Scheduler
                (
                    "downsample_scheduler",
                    f'from(bucket: "aico_telemetry")'
                    f' |> range(start: -1m)'
                    f' |> filter(fn: (r) => r._measurement == "scheduler_job")'
                    f' |> filter(fn: (r) => r._field == "duration_ms_f" or r._field == "success_b")'
                    f' |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)'
                    f' |> set(key: "_measurement", value: "scheduler_job_1m")'
                    f' |> to(bucket: "aico_telemetry_downsampled", org: "{org}")',
                ),

                # Memory
                (
                    "downsample_memory_queries",
                    f'from(bucket: "aico_telemetry")'
                    f' |> range(start: -1m)'
                    f' |> filter(fn: (r) => r._measurement == "memory_query")'
                    f' |> filter(fn: (r) => r._field == "query_time_ms_f" or r._field == "results_count_i")'
                    f' |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)'
                    f' |> set(key: "_measurement", value: "memory_query_1m")'
                    f' |> to(bucket: "aico_telemetry_downsampled", org: "{org}")',
                ),

                # Model inference
                (
                    "downsample_model_inference",
                    f'from(bucket: "aico_telemetry")'
                    f' |> range(start: -1m)'
                    f' |> filter(fn: (r) => r._measurement == "model_inference")'
                    f' |> filter(fn: (r) => r._field == "duration_ms_f" or r._field == "tokens_generated_i" or r._field == "prompt_tokens_i" or r._field == "ttft_ms_f")'
                    f' |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)'
                    f' |> set(key: "_measurement", value: "model_inference_1m")'
                    f' |> to(bucket: "aico_telemetry_downsampled", org: "{org}")',
                ),
            ]
            
            created_count = 0
            for task_name, flux_script in tasks_to_create:
                if task_name not in existing_task_names:
                    tasks_api.create_task_every(
                        name=task_name,
                        flux=flux_script,
                        every="1m",
                        organization=org_obj
                    )
                    created_count += 1
            
            if created_count > 0:
                console.print(f"  ✓ Created {created_count} downsampling tasks")
            else:
                console.print(f"  ✓ All downsampling tasks already exist")
                
    except Exception as e:
        import traceback
        console.print(format_warning(f"⚠️  Failed to configure downsampling (non-fatal): {e}"))
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


def _get_or_create_influx_credentials() -> Tuple[str, str]:
    """
    Get or create InfluxDB credentials - FULLY AUTOMATIC.
    
    Unified mechanism:
    - docker/secrets/influx_admin_password
    - docker/secrets/influx_admin_token
    
    Returns:
        Tuple of (admin_password, admin_token)
    """
    secrets = _ensure_all_secrets()
    return secrets["influx_admin_password"], secrets["influx_admin_token"]


def _get_compose_file() -> Path:
    """Return path to the local docker-compose file for DB services."""
    root = Path(__file__).parent.parent.parent
    return root / "docker" / "docker-compose.local.yml"


async def _ensure_system_user_async() -> None:
    """Ensure the system user exists in Postgres after schema deployment.

    This creates an internal, non-interactive user profile with a stable
    UUID of 'system_user' if it does not already exist. The user is marked
    as active to keep it out of the soft-deleted cleanup path; login
    capability is governed elsewhere via authentication/authorization.
    """

    try:
        from aico.data.postgres.connection import get_postgres_pool

        pool = await get_postgres_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT uuid FROM user_profiles WHERE uuid = $1",
                "system_user",
            )
            if existing:
                return

            await conn.execute(
                """
                INSERT INTO user_profiles (
                    uuid,
                    full_name,
                    nickname,
                    user_type,
                    is_active,
                    primary_language,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                "system_user",
                "AICO System User",
                "system",
                "system",
                True,
                "en",
            )
    except Exception as exc:  # pragma: no cover - defensive; deployment should continue
        console.print(
            format_warning(
                f"Warning: Failed to ensure system_user exists in Postgres: {exc}"
            )
        )


def _run_compose(args: list[str], env: dict = None) -> int:
    """Run docker compose with the given args, handling basic errors.

    Args:
        args: Docker compose arguments
        env: Additional environment variables to inject
        
    Returns the subprocess return code.
    """

    compose_file = _get_compose_file()
    if not compose_file.exists():
        console.print(
            format_error(
                f"Docker compose file not found: {compose_file}. "
                "Ensure local docker configuration is present."
            )
        )
        return 1

    cmd = [
        "docker",
        "compose",
        "-f",
        str(compose_file),
    ] + args

    # Merge environment if provided
    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    try:
        # Use the compose file directory as the working directory so relative paths
        # inside docker-compose.local.yml resolve correctly.
        result = subprocess.run(cmd, check=False, env=run_env, cwd=str(compose_file.parent))
        if result.returncode != 0:
            console.print(format_error(f"docker compose failed with exit code {result.returncode}"))
        return result.returncode
    except FileNotFoundError:
        console.print(
            format_error(
                "'docker' command not found. Install Docker and ensure it is on your PATH."
            )
        )
        return 1


def _nuke_postgres(shadow: bool = False) -> int:
    """COMPLETE reset: force kill containers, unmount volumes, remove images, networks, credentials, cache."""

    console.print("💣 [bold yellow]NUKING Postgres - COMPLETE cleanup of ALL artifacts...[/bold yellow]")

    # 1. Force kill and remove container (multiple attempts with different methods)
    console.print("  [dim]→ Force killing and removing containers...[/dim]")
    
    # Try docker-compose first
    _run_compose(["kill", "postgres"])
    _run_compose(["rm", "-f", "-v", "postgres"])  # -v removes anonymous volumes too
    
    # Force kill by container name (in case compose doesn't find it)
    try:
        subprocess.run(
            ["docker", "kill", "aico-postgres"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["docker", "rm", "-f", "-v", "aico-postgres"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass
    
    # Remove any containers with postgres label (catch-all)
    try:
        result = subprocess.run(
            ["docker", "ps", "-aq", "--filter", "label=com.aico.component=postgres"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            container_ids = result.stdout.strip().split('\n')
            for cid in container_ids:
                subprocess.run(
                    ["docker", "rm", "-f", "-v", cid],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
    except FileNotFoundError:
        pass
    
    # Wait a moment for containers to fully stop
    import time
    time.sleep(1)

    # 2. Remove ALL possible volume naming patterns
    console.print("  [dim]→ Removing volumes (all naming patterns)...[/dim]")
    volume_patterns = [
        "aico-pgdata",           # Direct name
        "docker_aico-pgdata",    # Old compose (directory prefix)
        "aico_aico-pgdata",      # New compose with name: aico
    ]
    
    for volume_name in volume_patterns:
        try:
            subprocess.run(
                ["docker", "volume", "rm", "-f", volume_name],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass

    # 3. Remove any volumes with postgres label (catch-all)
    try:
        subprocess.run(
            ["docker", "volume", "prune", "-f", "--filter", "label=com.aico.component=postgres"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass
    
    # 3b. Prune ALL dangling/unused volumes (catches anonymous volumes)
    try:
        subprocess.run(
            ["docker", "volume", "prune", "-af"],  # -a removes all unused, -f force
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # 4. Remove Docker images (postgres and pgvector variants) and any dangling images
    console.print("  [dim]→ Removing Docker images...[/dim]")
    try:
        # Remove specific postgres images
        subprocess.run(
            ["docker", "rmi", "-f", "postgres:18.1"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["docker", "rmi", "-f", "pgvector/pgvector:0.8.1-pg18"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Remove any dangling images
        subprocess.run(
            ["docker", "image", "prune", "-f"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # 5. Remove networks created by docker-compose
    console.print("  [dim]→ Cleaning up networks...[/dim]")
    try:
        # Remove aico project networks
        subprocess.run(
            ["docker", "network", "prune", "-f", "--filter", "label=com.docker.compose.project=aico"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # 6. Clear build cache
    console.print("  [dim]→ Pruning build cache...[/dim]")
    try:
        subprocess.run(
            ["docker", "builder", "prune", "-f"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # 7. System-wide Docker cleanup
    console.print("  [dim]→ Running system-wide Docker cleanup...[/dim]")
    try:
        # Prune all stopped containers
        subprocess.run(
            ["docker", "container", "prune", "-f"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Prune all unused images (not just dangling)
        subprocess.run(
            ["docker", "image", "prune", "-af"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Prune all unused volumes (already done above, but ensure complete)
        subprocess.run(
            ["docker", "volume", "prune", "-af"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Prune all build cache
        subprocess.run(
            ["docker", "builder", "prune", "-af"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # 8. Clear credentials from keyring
    console.print("  [dim]→ Clearing credentials from keyring...[/dim]")
    non_interactive = (not sys.stdin.isatty()) or (os.getenv("AICO_NONINTERACTIVE") == "true")
    if non_interactive:
        console.print("  [dim]→ Skipping keyring cleanup in non-interactive mode[/dim]")
        console.print(format_success("✅ Postgres completely nuked - fresh slate ready"))
        return 0

    try:
        from aico.security.key_manager import AICOKeyManager
        config = ConfigurationManager()
        key_manager = AICOKeyManager(config)

        import keyring
        try:
            keyring.delete_password(key_manager.service_name, "postgres_postgres_password")
        except Exception:
            pass
    except Exception:
        pass

    console.print(format_success("✅ Postgres completely nuked - fresh slate ready"))
    return 0


def _nuke_loki() -> int:
    """COMPLETE reset: force kill containers, unmount volumes, remove images, networks, cache."""

    console.print("💣 [bold yellow]NUKING Loki - COMPLETE cleanup of ALL artifacts...[/bold yellow]")

    # 1. Force kill and remove container (multiple attempts with different methods)
    console.print("  [dim]→ Force killing and removing containers...[/dim]")
    
    # Try docker-compose first
    _run_compose(["kill", "loki"])
    _run_compose(["rm", "-f", "-v", "loki"])  # -v removes anonymous volumes too
    
    # Force kill by container name (in case compose doesn't find it)
    try:
        subprocess.run(
            ["docker", "kill", "aico-loki"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["docker", "rm", "-f", "-v", "aico-loki"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass
    
    # Remove any containers with loki label (catch-all)
    try:
        result = subprocess.run(
            ["docker", "ps", "-aq", "--filter", "label=com.aico.component=loki"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            container_ids = result.stdout.strip().split('\n')
            for cid in container_ids:
                subprocess.run(
                    ["docker", "rm", "-f", "-v", cid],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
    except FileNotFoundError:
        pass

    # 2. Remove ALL possible volume naming patterns
    console.print("  [dim]→ Removing volumes (all naming patterns)...[/dim]")
    volume_patterns = [
        "aico-lokidata",           # Direct name
        "docker_aico-lokidata",    # Old compose (directory prefix)
        "aico_aico-lokidata",      # New compose with name: aico
    ]
    
    for volume_name in volume_patterns:
        try:
            subprocess.run(
                ["docker", "volume", "rm", "-f", volume_name],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass

    # 3. Remove any volumes with loki label (catch-all)
    try:
        subprocess.run(
            ["docker", "volume", "prune", "-f", "--filter", "label=com.aico.component=loki"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass
    
    # 3b. Prune ALL dangling/unused volumes (catches anonymous volumes)
    try:
        subprocess.run(
            ["docker", "volume", "prune", "-af"],  # -a removes all unused, -f force
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # 4. Remove Docker images (grafana/loki and any dangling images)
    console.print("  [dim]→ Removing Docker images...[/dim]")
    try:
        # Remove specific loki image
        subprocess.run(
            ["docker", "rmi", "-f", "grafana/loki:2.9.0"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Remove any dangling images
        subprocess.run(
            ["docker", "image", "prune", "-f"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # 5. Remove networks created by docker-compose
    console.print("  [dim]→ Cleaning up networks...[/dim]")
    try:
        # Remove aico project networks
        subprocess.run(
            ["docker", "network", "prune", "-f", "--filter", "label=com.docker.compose.project=aico"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # 6. Clear build cache
    console.print("  [dim]→ Pruning build cache...[/dim]")
    try:
        subprocess.run(
            ["docker", "builder", "prune", "-f"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # 7. System-wide Docker cleanup
    console.print("  [dim]→ Running system-wide Docker cleanup...[/dim]")
    try:
        # Prune all stopped containers
        subprocess.run(
            ["docker", "container", "prune", "-f"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Prune all unused images (not just dangling)
        subprocess.run(
            ["docker", "image", "prune", "-af"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Prune all unused volumes (already done above, but ensure complete)
        subprocess.run(
            ["docker", "volume", "prune", "-af"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Prune all build cache
        subprocess.run(
            ["docker", "builder", "prune", "-af"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    console.print(format_success("✅ Loki completely nuked - fresh slate ready"))
    return 0


def _nuke_influx() -> int:
    """COMPLETE reset: force kill containers, unmount volumes, remove images, networks, credentials, cache."""

    console.print("💣 [bold yellow]NUKING InfluxDB - COMPLETE cleanup of ALL artifacts...[/bold yellow]")

    # 1. Force kill and remove container (multiple attempts with different methods)
    console.print("  [dim]→ Force killing and removing containers...[/dim]")
    
    # Try docker-compose first
    _run_compose(["kill", "influxdb"])
    _run_compose(["rm", "-f", "-v", "influxdb"])  # -v removes anonymous volumes too
    
    # Force kill by container name (in case compose doesn't find it)
    try:
        subprocess.run(
            ["docker", "kill", "aico-influxdb"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["docker", "rm", "-f", "-v", "aico-influxdb"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass
    
    # Remove any containers with influxdb label (catch-all)
    try:
        result = subprocess.run(
            ["docker", "ps", "-aq", "--filter", "label=com.aico.component=influxdb"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            container_ids = result.stdout.strip().split('\n')
            for cid in container_ids:
                subprocess.run(
                    ["docker", "rm", "-f", "-v", cid],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
    except FileNotFoundError:
        pass

    # 2. Remove ALL possible volume naming patterns
    console.print("  [dim]→ Removing volumes (all naming patterns)...[/dim]")
    volume_patterns = [
        "aico-influxdata",           # Direct name
        "docker_aico-influxdata",    # Old compose (directory prefix)
        "aico_aico-influxdata",      # New compose with name: aico
    ]
    
    for volume_name in volume_patterns:
        try:
            subprocess.run(
                ["docker", "volume", "rm", "-f", volume_name],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass

    # 3. Remove any volumes with influxdb label (catch-all)
    try:
        subprocess.run(
            ["docker", "volume", "prune", "-f", "--filter", "label=com.aico.component=influxdb"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass
    
    # 3b. Prune ALL dangling/unused volumes (catches anonymous volumes)
    try:
        subprocess.run(
            ["docker", "volume", "prune", "-af"],  # -a removes all unused, -f force
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # 4. Remove Docker images (influxdb:2 and any dangling images)
    console.print("  [dim]→ Removing Docker images...[/dim]")
    try:
        # Remove specific influxdb image
        subprocess.run(
            ["docker", "rmi", "-f", "influxdb:2"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Remove any dangling images
        subprocess.run(
            ["docker", "image", "prune", "-f"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # 5. Remove networks created by docker-compose
    console.print("  [dim]→ Cleaning up networks...[/dim]")
    try:
        # Remove aico project networks
        subprocess.run(
            ["docker", "network", "prune", "-f", "--filter", "label=com.docker.compose.project=aico"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # 6. Clear build cache
    console.print("  [dim]→ Pruning build cache...[/dim]")
    try:
        subprocess.run(
            ["docker", "builder", "prune", "-f"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # 7. System-wide Docker cleanup
    console.print("  [dim]→ Running system-wide Docker cleanup...[/dim]")
    try:
        # Prune all stopped containers
        subprocess.run(
            ["docker", "container", "prune", "-f"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Prune all unused images (not just dangling)
        subprocess.run(
            ["docker", "image", "prune", "-af"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Prune all unused volumes (already done above, but ensure complete)
        subprocess.run(
            ["docker", "volume", "prune", "-af"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Prune all build cache
        subprocess.run(
            ["docker", "builder", "prune", "-af"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    # 8. Clear credentials from keyring
    console.print("  [dim]→ Clearing credentials from keyring...[/dim]")
    non_interactive = (not sys.stdin.isatty()) or (os.getenv("AICO_NONINTERACTIVE") == "true")
    keyring_cleanup_enabled = os.getenv("AICO_KEYRING_CLEANUP") == "true"
    if non_interactive or not keyring_cleanup_enabled:
        console.print("  [dim]→ Skipping keyring cleanup in non-interactive mode[/dim]")
        if not non_interactive and not keyring_cleanup_enabled:
            console.print("  [dim]→ Keyring cleanup is disabled by default (set AICO_KEYRING_CLEANUP=true to enable)[/dim]")
        console.print(format_success("✅ InfluxDB completely nuked - fresh slate ready"))
        return 0
    try:
        from aico.security.key_manager import AICOKeyManager
        config = ConfigurationManager()
        key_manager = AICOKeyManager(config)
        
        import keyring
        try:
            keyring.delete_password(key_manager.service_name, "influx_admin_password")
            keyring.delete_password(key_manager.service_name, "influx_admin_token_password")
        except Exception:
            pass
    except Exception:
        pass

    console.print(format_success("✅ InfluxDB completely nuked - fresh slate ready"))
    return 0


def _nuke_studio(studio_dir: Path) -> int:
    """Reset Studio container/image artifacts."""

    console.print("💣 [bold yellow]NUKING Studio - cleanup of Docker artifacts...[/bold yellow]")

    # Best-effort removal: Studio containers + images only.
    # IMPORTANT: do NOT run `docker compose down` here because Studio shares the
    # project namespace (`name: aico`) with other components.
    # A project-level down would stop/remove unrelated containers.

    # Remove via compose (scoped to the studio service in the studio compose file)
    prod_compose = studio_dir / "docker" / "compose.prod.yml"
    dev_compose = studio_dir / "docker" / "compose.dev.yml"
    if prod_compose.exists():
        _run_compose_file(prod_compose, ["rm", "-s", "-f", "studio"], cwd=studio_dir)
    if dev_compose.exists():
        _run_compose_file(dev_compose, ["rm", "-s", "-f", "studio"], cwd=studio_dir)

    # Also remove any explicitly named containers (for older compose versions / manual runs)
    try:
        subprocess.run(
            ["docker", "rm", "-f", "aico-studio"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["docker", "rm", "-f", "aico-studio-dev"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return 1

    try:
        subprocess.run(
            ["docker", "rmi", "-f", "aico-studio:local"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["docker", "rmi", "-f", "aico-studio-dev:local"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    console.print(format_success("✅ Studio nuked"))


def _nuke_vllm() -> int:
    """Destroy the vLLM container (and any related artifacts that are safe to remove)."""
    console.print("💣 [bold yellow]NUKING vLLM - cleanup of Docker artifacts...[/bold yellow]")

    _run_compose(["--profile", "vllm", "kill", "vllm"])
    _run_compose(["--profile", "vllm", "rm", "-f", "vllm"])

    try:
        subprocess.run(
            ["docker", "rm", "-f", "aico-vllm"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return 1

    try:
        result = subprocess.run(
            ["docker", "ps", "-aq", "--filter", "label=com.aico.component=vllm"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            container_ids = result.stdout.strip().split("\n")
            subprocess.run(
                ["docker", "rm", "-f", *container_ids],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except FileNotFoundError:
        return 1

    console.print(format_success("✅ vLLM nuked"))
    return 0


app = typer.Typer(
    help="Deploy and provision AICO infrastructure",
    no_args_is_help=True,
    rich_markup_mode="rich"
)


@app.callback(invoke_without_command=True)
def deploy_help(ctx: typer.Context):
    """Deploy and provision AICO infrastructure components.
    
    Use 'aico deploy <target>' to deploy specific components.
    Run 'aico deploy <target> --help' for detailed options.
    """
    if ctx.invoked_subcommand is None:
        console.print("\n[bold cyan]AICO Deployment System[/bold cyan]")
        console.print("=" * 70)
        console.print()
        console.print("Deploy and provision AICO infrastructure components.\n")
        
        console.print("[bold yellow]📦 Available Deployment Targets:[/bold yellow]\n")
        
        # Full system deployment
        console.print("  [bold cyan]system[/bold cyan]")
        console.print("    One-command bootstrap: infrastructure + schema + tenant + admin user")
        console.print("    [dim]Example: aico deploy system --tenant-display-name \"My Company\"[/dim]\n")
        
        # Infrastructure backends
        console.print("[bold]Infrastructure Backends:[/bold]")
        console.print("  [bold cyan]pg[/bold cyan]")
        console.print("    PostgreSQL database (container + schema)")
        console.print("    [dim]Example: aico deploy pg[/dim]")
        console.print("    [dim]Reset: aico deploy pg --nuke[/dim]\n")
        
        console.print("  [bold cyan]valkey[/bold cyan]")
        console.print("    Valkey in-memory cache (Redis-compatible)")
        console.print("    [dim]Example: aico deploy valkey[/dim]\n")
        
        console.print("  [bold cyan]nats[/bold cyan]")
        console.print("    NATS message broker (event streaming)")
        console.print("    [dim]Example: aico deploy nats[/dim]\n")
        
        console.print("  [bold cyan]influx[/bold cyan]")
        console.print("    InfluxDB time-series database (container + org/bucket)")
        console.print("    [dim]Example: aico deploy influx[/dim]\n")
        
        console.print("  [bold cyan]loki[/bold cyan]")
        console.print("    Loki log aggregation (container + config)")
        console.print("    [dim]Example: aico deploy loki[/dim]\n")
        
        console.print("  [bold cyan]prometheus[/bold cyan]")
        console.print("    Prometheus metrics collection and monitoring")
        console.print("    [dim]Example: aico deploy prometheus[/dim]\n")
        
        console.print("  [bold cyan]tempo[/bold cyan]")
        console.print("    Grafana Tempo distributed tracing")
        console.print("    [dim]Example: aico deploy tempo[/dim]\n")
        
        console.print("  [bold cyan]grafana[/bold cyan]")
        console.print("    Grafana visualization (container + datasources)")
        console.print("    [dim]Example: aico deploy grafana[/dim]\n")
        
        console.print("  [bold cyan]otel-collector[/bold cyan]")
        console.print("    OpenTelemetry Collector (telemetry aggregation)")
        console.print("    [dim]Example: aico deploy otel-collector[/dim]\n")
        
        # Core services
        console.print("[bold]Core Services:[/bold]")
        console.print("  [bold cyan]gateway[/bold cyan]")
        console.print("    AICO API Gateway (REST/WebSocket/ZMQ endpoints)")
        console.print("    [dim]Example: aico deploy gateway[/dim]\n")
        
        console.print("  [bold cyan]core[/bold cyan]")
        console.print("    AICO Core backend (conversation engine, memory, agency)")
        console.print("    [dim]Example: aico deploy core[/dim]\n")
        
        console.print("  [bold cyan]modelservice[/bold cyan]")
        console.print("    AICO Modelservice (NER, embeddings, sentiment analysis)")
        console.print("    [dim]Example: aico deploy modelservice[/dim]\n")
        
        # Optional services
        console.print("[bold]Optional Services:[/bold]")
        console.print("  [bold cyan]vllm[/bold cyan]")
        console.print("    vLLM inference server (Docker with GPU support, Linux/Windows only)")
        console.print("    [dim]Example: aico deploy vllm --model Qwen/Qwen2.5-3B-Instruct[/dim]")
        console.print("    [dim]Note: Use 'aico vllm deploy' for macOS Metal GPU support[/dim]\n")
        
        console.print("  [bold cyan]studio[/bold cyan]")
        console.print("    AICO Studio web UI (React dashboard)")
        console.print("    [dim]Example: aico deploy studio[/dim]")
        console.print("    [dim]Dev mode: aico deploy studio --dev[/dim]\n")
        
        # Common options
        console.print("[bold yellow]🔧 Common Options:[/bold yellow]\n")
        console.print("  [bold]--nuke[/bold]")
        console.print("    Destroy existing container/volume before provisioning (DANGEROUS)")
        console.print("    [dim]Example: aico deploy pg --nuke[/dim]\n")
        
        console.print("  [bold]--help[/bold]")
        console.print("    Show detailed help for a specific deployment target")
        console.print("    [dim]Example: aico deploy system --help[/dim]\n")
        
        # Quick start
        console.print("[bold yellow]🚀 Quick Start:[/bold yellow]\n")
        console.print("  1. Deploy full system (recommended for first-time setup):")
        console.print("     [cyan]aico deploy system --tenant-display-name \"My Company\" --admin-full-name \"John Doe\"[/cyan]\n")
        
        console.print("  2. Deploy individual components:")
        console.print("     [cyan]aico deploy pg[/cyan]")
        console.print("     [cyan]aico deploy gateway[/cyan]")
        console.print("     [cyan]aico deploy core[/cyan]")
        console.print("     [cyan]aico deploy modelservice[/cyan]\n")
        
        console.print("  3. Deploy monitoring stack:")
        console.print("     [cyan]aico deploy influx[/cyan]")
        console.print("     [cyan]aico deploy loki[/cyan]")
        console.print("     [cyan]aico deploy grafana[/cyan]\n")
        
        console.print("[dim]For more information: https://docs.aico.ai/deployment[/dim]")
        console.print()


@app.command("system", help="Provision full AICO system (one-command bootstrap)")
def deploy_system(
    config_file: str = typer.Option(None, "--config", help="YAML/JSON config file for non-interactive bootstrap"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Fail instead of prompting for missing values"),
    services: bool = typer.Option(
        True,
        "--services/--no-services",
        help="Also deploy gateway/core/modelservice containers (recommended for zero-to-operational)",
    ),
    master_password_file: str = typer.Option(
        None,
        "--master-password-file",
        help="Path to a file containing the master password (recommended for headless/server installs)",
    ),
    tenant_display_name: str = typer.Option(None, "--tenant-display-name", help="Tenant display name"),
    admin_full_name: str = typer.Option(None, "--admin-full-name", help="Admin/owner full name"),
    admin_pin: str = typer.Option(None, "--admin-pin", help="Optional admin PIN (will be hashed and stored)"),
    primary_language: str = typer.Option(None, "--primary-language", help="Optional primary language (BCP-47 code)")
):
    """One-command bootstrap: infra + schema + tenant + admin user.

    Secrets:
    - Reads master password from --master-password-file or AICO_MASTER_PASSWORD.
    - Best-effort scrubs AICO_MASTER_PASSWORD from this process env after use.
    """

    cfg = _load_deploy_config(config_file)

    if master_password_file is None:
        master_password_file = (
            cfg.get("security", {}) if isinstance(cfg.get("security"), dict) else {}
        ).get("master_password_file")

    if isinstance(cfg.get("system"), dict) and isinstance(cfg["system"].get("services"), bool):
        services = bool(cfg["system"]["services"])

    if tenant_display_name is None:
        tenant_display_name = (
            cfg.get("tenant", {}) if isinstance(cfg.get("tenant"), dict) else {}
        ).get("display_name")
    if admin_full_name is None:
        admin_full_name = (
            cfg.get("admin", {}) if isinstance(cfg.get("admin"), dict) else {}
        ).get("full_name")
    if admin_pin is None:
        admin_pin = (
            cfg.get("admin", {}) if isinstance(cfg.get("admin"), dict) else {}
        ).get("pin")
    if primary_language is None:
        primary_language = (
            cfg.get("tenant", {}) if isinstance(cfg.get("tenant"), dict) else {}
        ).get("primary_language")

    if tenant_display_name is None:
        if non_interactive:
            console.print(format_error("Missing --tenant-display-name (or tenant.display_name in --config)"))
            raise typer.Exit(1)
        tenant_display_name = typer.prompt("Tenant display name")

    if admin_full_name is None:
        if non_interactive:
            console.print(format_error("Missing --admin-full-name (or admin.full_name in --config)"))
            raise typer.Exit(1)
        admin_full_name = typer.prompt("Admin full name")

    # Admin passcode policy (may be configured to be stricter, but never weaker).
    min_length = 12
    try:
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        configured = config.get_optional("security.authentication.admin_passcode_policy.min_length", default=None)
        if isinstance(configured, int) and configured > min_length:
            min_length = configured
    except Exception:
        pass

    if admin_pin is None:
        if non_interactive:
            console.print(format_error("Missing --admin-pin (or admin.pin in --config)"))
            raise typer.Exit(1)
        admin_pin = typer.prompt("Admin passcode", hide_input=True)

    try:
        _validate_admin_passcode(admin_pin, min_length=min_length)
    except Exception as e:
        console.print(format_error(str(e)))
        raise typer.Exit(1)

    console.rule("[bold cyan]AICO System Deployment[/bold cyan]")

    _authenticate_for_deploy(non_interactive=non_interactive, master_password_file=master_password_file)

    # Provision Postgres (container + schema). This is idempotent without --nuke.
    deploy_pg(nuke=False, shadow=False)

    # Ensure pg password is available for subsequent CLI DB operations.
    pg_password = _get_or_create_postgres_password()
    _ensure_postgres_password_in_keyring(pg_password, non_interactive=non_interactive)

    # Ensure internal system user exists (required by various subsystems)
    asyncio.run(_ensure_system_user_async())

    state = _load_deploy_state()
    if state.get("tenant_id") and state.get("admin_user_uuid"):
        console.print(format_info("Deploy state already exists; ensuring bootstrap is consistent..."))

    tenant_id, admin_user_uuid = _bootstrap_postgres(
        tenant_display_name=tenant_display_name,
        admin_full_name=admin_full_name,
        admin_pin=admin_pin,
        primary_language=primary_language,
        non_interactive=non_interactive,
    )
    _write_deploy_state(tenant_id=tenant_id, admin_user_uuid=admin_user_uuid)

    # Deploy infrastructure backends
    console.print("\n[bold cyan]Deploying Infrastructure Backends...[/bold cyan]")
    deploy_valkey(nuke=False)
    deploy_nats(nuke=False)
    deploy_influx(nuke=False)
    deploy_loki(nuke=False)
    deploy_prometheus(nuke=False)
    deploy_tempo(nuke=False)
    deploy_grafana(nuke=False)
    deploy_otel_collector(nuke=False)

    # Deploy core services
    if services:
        console.print("\n[bold cyan]Deploying Core Services...[/bold cyan]")
        deploy_gateway(nuke=False)
        deploy_core(nuke=False)
        deploy_modelservice(nuke=False)

    console.print("\n" + "=" * 70)
    console.print(format_success("✅ System bootstrap complete"))
    console.print("=" * 70)
    console.print(f"\n[bold]Tenant ID:[/bold] {tenant_id}")
    console.print(f"[bold]Admin User UUID:[/bold] {admin_user_uuid}")
    console.print("\n[bold yellow]Deployed Components:[/bold yellow]")
    console.print("  ✅ PostgreSQL (database)")
    console.print("  ✅ Valkey (cache)")
    console.print("  ✅ NATS (message broker)")
    console.print("  ✅ InfluxDB (metrics)")
    console.print("  ✅ Loki (logs)")
    console.print("  ✅ Prometheus (monitoring)")
    console.print("  ✅ Tempo (tracing)")
    console.print("  ✅ Grafana (visualization)")
    console.print("  ✅ OpenTelemetry Collector (telemetry)")
    if services:
        console.print("  ✅ Gateway (API)")
        console.print("  ✅ Core (backend)")
        console.print("  ✅ Modelservice (AI models)")
    console.print("\n[bold green]🎉 AICO is ready to use![/bold green]\n")


@app.command("pg", help="Provision Postgres (container + schema), optionally with --nuke for full reset")
def deploy_pg(
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy Postgres container + volume before provisioning (DANGEROUS).",
    ),
    shadow: bool = typer.Option(
        False,
        "--shadow",
        help="Provision the shadow Postgres instance (postgres-shadow / postgres_shadow).",
    ),
):
    """Deploy or refresh the Postgres backend on the current environment.

    This command is FULLY AUTOMATED:
    - Prompts for master password (if not already authenticated)
    - Auto-generates Postgres password from master key
    - Stores password securely in system keyring
    - Injects password into container via environment
    - Applies schema automatically
    
    Safe to run multiple times without --nuke. With --nuke it
    will wipe the Postgres volume and start from a clean slate.
    """

    from cli.commands import pg as pg_cli

    console.print("\n" + "="*60)
    console.print("🐘 [bold cyan]AICO Postgres Deployment[/bold cyan]")
    console.print("="*60 + "\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing data!"))
        # For now, --nuke always targets the primary Postgres volume/container
        # Shadow environments can be nuked manually if needed.
        _nuke_postgres()

    # Get or create Postgres password (prompts for master password if needed)
    pg_password = _get_or_create_postgres_password()
    
    # Get Postgres config for connection details
    from aico.core.config import ConfigurationManager
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    cfg_key = "postgres_shadow" if shadow else "postgres"
    pg_cfg = config.get(cfg_key, {}) or {}
    host = pg_cfg.get("host", "127.0.0.1")
    port = int(pg_cfg.get("port", 5432))
    
    # Prepare environment for container
    container_env = {
        "AICO_PG_PASSWORD": pg_password
    }

    service_name = "postgres-shadow" if shadow else "postgres"
    console.print(f"🚀 [cyan]Starting Postgres container ({service_name}) with auto-generated credentials...[/cyan]")
    code = _run_compose(["up", "-d", service_name], env=container_env)
    if code != 0:
        console.print(format_error("Failed to start Postgres container"))
        raise typer.Exit(code)

    console.print("⏳ [cyan]Waiting for Postgres to be ready...[/cyan]")
    import time
    import socket
    
    # Wait for Postgres to accept connections (up to 30 seconds)
    max_wait = 30
    wait_interval = 1
    elapsed = 0
    
    while elapsed < max_wait:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                console.print(format_success(f"Postgres ready after {elapsed} seconds"))

                # Give Postgres a moment to fully stabilize
                time.sleep(2)

                console.print("🔧 [cyan]Applying schema (idempotent)...[/cyan]")
                pg_cli.init(shadow=shadow)

                # After schema is applied, ensure the internal system user exists.
                console.print("👤 [cyan]Ensuring internal system user exists...[/cyan]")
                try:
                    asyncio.run(_ensure_system_user_async())
                except RuntimeError:
                    # Fallback in case an event loop is already running
                    console.print(
                        format_warning(
                            "Warning: Could not run system user creation in standalone event loop; "
                            "assuming it will be created at runtime if missing."
                        )
                    )

                break
        except (OSError, socket.timeout):
            time.sleep(wait_interval)
            elapsed += wait_interval
    else:
        console.print(format_warning(f"Postgres did not become ready within {max_wait} seconds, continuing anyway..."))
        console.print("🔧 [cyan]Applying schema (idempotent)...[/cyan]")
        pg_cli.init(shadow=shadow)

    console.print("🩺 [cyan]Verifying deployment health...[/cyan]")
    pg_cli.doctor(shadow=shadow)

    console.print("")
    console.print(format_success("✅ Postgres deployment completed successfully!"))
    console.print(format_info("💡 Password stored in system keyring (derived from master key)"))
    console.print(format_info("💡 Backend components will auto-retrieve credentials from keyring at runtime"))
    console.print("")


@app.command("influx", help="Provision InfluxDB (container + org/bucket), optionally with --nuke for full reset")
def deploy_influx(
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy InfluxDB container + volume before provisioning (DANGEROUS).",
    )
):
    """Deploy or refresh the InfluxDB backend on the current environment.

    This command is FULLY AUTOMATED:
    - Prompts for master password (if not already authenticated)
    - Auto-generates InfluxDB admin password and token from master key
    - Stores credentials securely in system keyring
    - Injects credentials into container via environment
    - Creates org/bucket/retention automatically
    
    Safe to run multiple times without --nuke. With --nuke it
    will wipe the InfluxDB volume and start from a clean slate.
    """

    from cli.commands import influx as influx_cli

    console.print("\n" + "="*60)
    console.print("📊 [bold cyan]AICO InfluxDB Deployment[/bold cyan]")
    console.print("="*60 + "\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing data!"))
        _nuke_influx()

    # Ensure secrets exist on disk; compose will mount them into the container.
    admin_password, admin_token = _get_or_create_influx_credentials()

    console.print("🚀 [cyan]Starting InfluxDB container with compose secrets...[/cyan]")
    code = _run_compose(["up", "-d", "influxdb"], env=None)
    if code != 0:
        console.print(format_error("Failed to start InfluxDB container"))
        raise typer.Exit(code)

    console.print("⏳ [cyan]Waiting for InfluxDB to be ready...[/cyan]")
    import time
    time.sleep(8)  # Give InfluxDB time to auto-initialize with DOCKER_INFLUXDB_INIT_* env vars

    non_interactive = (not sys.stdin.isatty()) or (os.getenv("AICO_NONINTERACTIVE") == "true")
    run_checks = os.getenv("AICO_DEPLOY_INFLUX_DOCTOR") == "true"
    disable_downsampling = os.getenv("AICO_DEPLOY_INFLUX_DOWNSAMPLING") == "false"

    if non_interactive and not run_checks:
        console.print("[dim]Skipping InfluxDB doctor in non-interactive mode (set AICO_DEPLOY_INFLUX_DOCTOR=true to enable).[/dim]")
    else:
        console.print("🩺 [cyan]Verifying deployment health...[/cyan]")
        influx_cli.doctor()

    if disable_downsampling:
        console.print("[dim]Skipping downsampling setup (AICO_DEPLOY_INFLUX_DOWNSAMPLING=false).[/dim]")
    else:
        console.print("⚙️  [cyan]Configuring downsampling tasks and retention policies...[/cyan]")
        _setup_influx_downsampling(admin_token)

    console.print("")
    console.print(format_success("✅ InfluxDB deployment completed successfully!"))
    console.print(format_info("💡 Credentials stored in system keyring (derived from master key)"))
    console.print(format_info("💡 Downsampling tasks configured for optimal dashboard performance"))
    console.print(format_info("💡 Backend components will auto-retrieve credentials from keyring at runtime"))
    console.print("")


@app.command("loki", help="Provision Loki (container + config), optionally with --nuke for full reset")
def deploy_loki(
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy Loki container + volume before provisioning (DANGEROUS).",
    )
):
    """Deploy or refresh the Loki log aggregation backend.

    This command is FULLY AUTOMATED:
    - No credentials needed (Loki is unauthenticated by default)
    - Starts Loki container with configuration
    - Creates data volume for log storage
    - Configures 30-day retention policy
    
    Safe to run multiple times without --nuke. With --nuke it
    will wipe the Loki volume and start from a clean slate.
    """

    console.print("\n" + "="*60)
    console.print("📝 [bold cyan]AICO Loki Deployment[/bold cyan]")
    console.print("="*60 + "\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing data!"))
        _nuke_loki()

    # Verify Loki config file exists
    loki_config = Path(__file__).parent.parent.parent / "docker" / "loki" / "loki-config.yaml"
    if not loki_config.exists():
        console.print(format_error(f"Loki config file not found: {loki_config}"))
        console.print(format_info("Creating default Loki configuration..."))
        
        # Create config directory if needed
        loki_config.parent.mkdir(parents=True, exist_ok=True)
        
        # Write default config
        default_config = """auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

ruler:
  alertmanager_url: http://localhost:9093

# Retention configuration - keep logs for 30 days
limits_config:
  retention_period: 720h  # 30 days
  max_query_length: 721h
  max_query_lookback: 720h

# Compactor for retention enforcement
compactor:
  working_directory: /loki/compactor
  shared_store: filesystem
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150
"""
        loki_config.write_text(default_config)
        console.print(format_success("Created Loki configuration file"))

    console.print("🚀 [cyan]Starting Loki container...[/cyan]")
    code = _run_compose(["up", "-d", "loki"])
    if code != 0:
        console.print(format_error("Failed to start Loki container"))
        raise typer.Exit(code)

    console.print("⏳ [cyan]Waiting for Loki to be ready...[/cyan]")
    import time
    import requests
    
    # Wait for Loki to accept connections (up to 30 seconds)
    max_wait = 30
    wait_interval = 1
    elapsed = 0
    
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    loki_url = config.get("loki.url", "http://127.0.0.1:3100")
    
    while elapsed < max_wait:
        try:
            response = requests.get(f"{loki_url}/ready", timeout=1.0)
            if response.status_code == 200:
                console.print(format_success(f"Loki ready after {elapsed} seconds"))
                break
        except (requests.RequestException, requests.Timeout):
            pass
        
        time.sleep(wait_interval)
        elapsed += wait_interval
    else:
        console.print(format_warning(f"Loki did not become ready within {max_wait} seconds, continuing anyway..."))

    # Verify Loki is working by querying labels
    console.print("🩺 [cyan]Verifying deployment health...[/cyan]")
    try:
        response = requests.get(f"{loki_url}/loki/api/v1/labels", timeout=5.0)
        if response.status_code == 200:
            console.print(format_success("✓ Loki API responding correctly"))
        else:
            console.print(format_warning(f"⚠ Loki API returned status {response.status_code}"))
    except Exception as e:
        console.print(format_warning(f"⚠ Could not verify Loki API: {e}"))

    console.print("")
    console.print(format_success("✅ Loki deployment completed successfully!"))
    console.print(format_info("💡 Loki is unauthenticated by default (suitable for local development)"))
    console.print(format_info("💡 Logs will be retained for 30 days (configurable in loki-config.yaml)"))
    console.print(format_info("💡 Backend components will automatically send logs to Loki at runtime"))
    console.print(format_info("💡 Query logs with: curl -G http://localhost:3100/loki/api/v1/query_range --data-urlencode 'query={service=\"backend\"}'"))
    console.print("")


@app.command("grafana", help="Provision Grafana (container + Loki datasource), optionally with --nuke for full reset")
def deploy_grafana(
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy Grafana container + volume before provisioning (DANGEROUS).",
    )
):
    """Deploy or refresh the Grafana visualization backend.

    This command is FULLY AUTOMATED:
    - Auto-generates admin password from master key
    - Starts Grafana container with Loki datasource
    - Creates data volume for dashboards/settings
    - Pre-configures Loki connection
    
    Safe to run multiple times without --nuke. With --nuke it
    will wipe the Grafana volume and start from a clean slate.
    """

    console.print("\n" + "="*60)
    console.print("📊 [bold cyan]AICO Grafana Deployment[/bold cyan]")
    console.print("="*60 + "\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing data!"))
        _nuke_grafana()

    _ensure_docker_volume("aico-grafanadata")

    # Get or create Grafana admin password
    console.print("🔐 [cyan]Managing Grafana credentials...[/cyan]")
    grafana_password = _get_or_create_grafana_password()
    
    # Set environment variables for docker-compose
    env = os.environ.copy()
    env["AICO_GRAFANA_USER"] = "admin"
    env["AICO_GRAFANA_PASSWORD"] = grafana_password

    # Verify provisioning configs exist
    grafana_provisioning = Path(__file__).parent.parent.parent / "docker" / "grafana" / "provisioning"
    if not grafana_provisioning.exists():
        console.print(format_error(f"Grafana provisioning directory not found: {grafana_provisioning}"))
        raise typer.Exit(1)

    console.print("🚀 [cyan]Starting Grafana container...[/cyan]")
    code = _run_compose(["up", "-d", "grafana"], env=env)
    if code != 0:
        console.print(format_error("Failed to start Grafana container"))
        raise typer.Exit(code)

    console.print("⏳ [cyan]Waiting for Grafana to be ready...[/cyan]")
    import time
    import requests
    
    # Wait for Grafana to accept connections (up to 60 seconds)
    max_wait = 60
    wait_interval = 2
    elapsed = 0

    config = ConfigurationManager()
    config.initialize(lightweight=True)
    grafana_url = (
        os.getenv("AICO_GRAFANA_URL")
        or config.get_optional("grafana.url")
        or "http://127.0.0.1:3001"
    )
    
    while elapsed < max_wait:
        try:
            response = requests.get(f"{grafana_url}/api/health", timeout=2.0)
            if response.status_code == 200:
                console.print(format_success(f"Grafana ready after {elapsed} seconds"))
                break
        except (requests.RequestException, requests.Timeout):
            pass
        
        time.sleep(wait_interval)
        elapsed += wait_interval
    else:
        console.print(format_warning(f"Grafana did not become ready within {max_wait} seconds, continuing anyway..."))

    # Verify Grafana is working and Loki datasource is configured
    console.print("🩺 [cyan]Verifying deployment health...[/cyan]")
    try:
        # Check Grafana API
        response = requests.get(
            f"{grafana_url}/api/datasources",
            auth=("admin", grafana_password),
            timeout=5.0
        )
        if response.status_code == 200:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "json" not in content_type:
                console.print(
                    format_warning(
                        "⚠ Grafana /api/datasources did not return JSON. "
                        f"Content-Type={response.headers.get('Content-Type')!r}."
                    )
                )
                console.print(format_warning(f"⚠ Response (first 200 chars): {response.text[:200]!r}"))
                datasources = []
            else:
                datasources = response.json()
            loki_ds = [ds for ds in datasources if ds.get("type") == "loki"]
            if loki_ds:
                console.print(format_success(f"✓ Grafana API responding correctly"))
                console.print(format_success(f"✓ Loki datasource configured: {loki_ds[0]['name']}"))
            else:
                console.print(format_warning("⚠ Loki datasource not found (may need manual configuration)"))
        else:
            console.print(format_warning(f"⚠ Grafana API returned status {response.status_code}"))
    except Exception as e:
        console.print(format_warning(f"⚠ Could not verify Grafana API: {e}"))

    console.print("")
    console.print(format_success("✅ Grafana deployment completed successfully!"))
    console.print(format_info(f"💡 Access Grafana at: {grafana_url}"))
    console.print(format_info(f"💡 Username: admin"))
    console.print(format_info(f"💡 Password: (stored in keyring - retrieve with: aico security keyring get grafana_admin_password)"))
    console.print(format_info("💡 Loki datasource is pre-configured and ready to use"))
    console.print(format_info("💡 Navigate to Explore → Loki to query logs"))
    console.print("")


@app.command("gateway", help="Provision AICO Gateway (Docker), optionally with --nuke for full reset")
def deploy_gateway(
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy Gateway container before provisioning.",
    ),
):
    """Deploy AICO Gateway container.

    Secrets are handled via docker/compose secrets:
    - CLI ensures docker/secrets/* exists
    - docker-compose mounts secrets into containers under /run/secrets/*
    """
    console.print("\n" + "=" * 60)
    console.print("🌐 [bold cyan]AICO Gateway Deployment[/bold cyan]")
    console.print("=" * 60 + "\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing Gateway container!"))
        _nuke_gateway()

    _ensure_all_secrets()

    # Use --no-cache when nuking to ensure fresh build
    if nuke:
        args = ["build", "--no-cache", "gateway"]
        console.print("🔨 [cyan]Building Gateway (no cache)...[/cyan]")
        code = _run_compose(args, env=None)
        if code != 0:
            raise typer.Exit(code)
        args = ["up", "-d", "gateway"]
    else:
        args = ["up", "-d", "--build", "gateway"]

    console.print("🚀 [cyan]Starting Gateway container...[/cyan]")
    code = _run_compose(args, env=None)
    if code != 0:
        raise typer.Exit(code)

    console.print("")
    console.print(format_success("✅ Gateway deployment completed successfully!"))
    console.print("")


@app.command("core", help="Provision AICO Core (Docker), optionally with --nuke for full reset")
def deploy_core(
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy Core container before provisioning.",
    ),
):
    """Deploy AICO Core container.

    Secrets are handled via docker/compose secrets:
    - CLI ensures docker/secrets/* exists
    - docker-compose mounts secrets into containers under /run/secrets/*
    """
    console.print("\n" + "=" * 60)
    console.print("🧠 [bold cyan]AICO Core Deployment[/bold cyan]")
    console.print("=" * 60 + "\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing Core container!"))
        _nuke_core()

    _ensure_all_secrets()

    # Use --no-cache when nuking to ensure fresh build
    if nuke:
        args = ["build", "--no-cache", "core"]
        console.print("🔨 [cyan]Building Core (no cache)...[/cyan]")
        code = _run_compose(args, env=None)
        if code != 0:
            raise typer.Exit(code)
        args = ["up", "-d", "core"]
    else:
        args = ["up", "-d", "--build", "core"]

    console.print("🚀 [cyan]Starting Core container...[/cyan]")
    code = _run_compose(args, env=None)
    if code != 0:
        raise typer.Exit(code)

    console.print("")
    console.print(format_success("✅ Core deployment completed successfully!"))
    console.print("")


@app.command("modelservice", help="Provision AICO Modelservice (Docker), optionally with --nuke for full reset")
def deploy_modelservice(
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy Modelservice container before provisioning.",
    ),
):
    """Deploy AICO Modelservice container with automatic credential management.
    
    Note: Modelservice doesn't directly use PostgreSQL, but credentials are
    ensured for consistency across all backend services.
    """
    console.print("\n" + "=" * 60)
    console.print("🤖 [bold cyan]AICO Modelservice Deployment[/bold cyan]")
    console.print("=" * 60 + "\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing Modelservice container!"))
        _nuke_modelservice()

    _ensure_all_secrets()

    # Use --no-cache when nuking to ensure fresh build
    if nuke:
        args = ["build", "--no-cache", "modelservice"]
        console.print("🔨 [cyan]Building Modelservice (no cache)...[/cyan]")
        code = _run_compose(args, env=None)
        if code != 0:
            raise typer.Exit(code)
        args = ["up", "-d", "modelservice"]
    else:
        args = ["up", "-d", "--build", "modelservice"]

    console.print("🚀 [cyan]Starting Modelservice container...[/cyan]")
    code = _run_compose(args, env=None)
    if code != 0:
        raise typer.Exit(code)

    console.print("")
    console.print(format_success("✅ Modelservice deployment completed successfully!"))
    console.print("")


@app.command("vllm", help="Provision vLLM (Docker with GPU), optionally with --nuke for full reset")
def deploy_vllm(
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy vLLM container before provisioning.",
    ),
    model: str = typer.Option(
        "Qwen/Qwen2.5-3B-Instruct",
        "--model",
        help="HuggingFace model to deploy (e.g., Qwen/Qwen2.5-3B-Instruct)",
    ),
):
    """Deploy vLLM inference server with GPU support (Linux/Windows only).
    
    This command deploys vLLM as a Docker container with NVIDIA GPU passthrough.
    The service uses the 'vllm' profile and must be explicitly started.
    
    Note: On macOS, use 'aico vllm deploy' instead for Metal GPU support.
    """
    import platform
    system = platform.system()
    
    console.print("\n" + "=" * 60)
    console.print("🚀 [bold cyan]vLLM Deployment (Docker + GPU)[/bold cyan]")
    console.print("=" * 60 + "\n")
    
    # Check platform
    if system == "Darwin":
        console.print(format_warning("⚠️  macOS detected - Docker GPU passthrough not supported"))
        console.print(format_info("💡 Use 'aico vllm deploy' for macOS Metal GPU support"))
        console.print("")
        raise typer.Exit(1)
    
    console.print(f"[dim]Platform: {system} (GPU passthrough enabled)[/dim]\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing vLLM container!"))
        _nuke_vllm()

    # Set model via environment
    env = {
        "VLLM_MODEL": model,
    }
    
    # Use --profile to activate vLLM service
    args = ["--profile", "vllm", "up", "-d", "vllm"]

    console.print(f"🚀 [cyan]Starting vLLM container with model: {model}[/cyan]")
    console.print("[dim]This will download the model on first run (may take several minutes)[/dim]\n")
    
    code = _run_compose(args, env=env)
    if code != 0:
        raise typer.Exit(code)

    console.print("")
    console.print(format_success("✅ vLLM deployment completed successfully!"))
    console.print(format_info("💡 API available at: http://localhost:8774"))
    console.print(format_info("💡 Check logs: docker logs -f aico-vllm"))
    console.print("")


@app.command("studio", help="Provision AICO Studio (Docker), with --dev for npm start and --nuke for full reset")
def deploy_studio(
    dev: bool = typer.Option(
        False,
        "--dev",
        help="Run Studio in dev mode (npm start) with source bind-mounts.",
    ),
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy Studio container + image before provisioning.",
    ),
    api_base_url: str = typer.Option(
        "",
        "--api-base-url",
        help="AICO Gateway API base URL (e.g. http://localhost:8771/api/v1). Overrides default.",
    ),
):
    """Deploy or refresh the AICO Studio web UI.

    - Production mode (default): builds a static bundle and serves via nginx.
    - Dev mode (--dev): runs `npm start` inside a container with bind mounts.

    The backend URL is configured at runtime via AICO_STUDIO_API_BASE_URL.
    """

    console.print("\n" + "=" * 60)
    console.print("🧩 [bold cyan]AICO Studio Deployment[/bold cyan]")
    console.print("=" * 60 + "\n")

    # Resolve studio path:
    # 1) Env var override: AICO_COMPONENT_STUDIO_DIR
    # 2) Config: system.components.studio.path
    # 3) Convention default: ../aico-studio relative to AICO repo root
    #
    # NOTE: _resolve_component_path uses ConfigurationManager(lightweight=True)
    # to avoid keyring blocking.
    studio_dir = _resolve_component_path("studio")
    if not studio_dir.exists():
        console.print(format_error(f"Studio directory not found: {studio_dir}"))
        console.print(format_info("Set system.components.studio.path in system.yaml or export AICO_COMPONENT_STUDIO_DIR."))
        raise typer.Exit(1)

    compose_file = studio_dir / "docker" / ("compose.dev.yml" if dev else "compose.prod.yml")
    if not compose_file.exists():
        console.print(format_error(f"Studio compose file not found: {compose_file}"))
        console.print(format_info("Ensure aico-studio has docker/compose.prod.yml and docker/compose.dev.yml."))
        raise typer.Exit(1)

    if nuke:
        _nuke_studio(studio_dir)

    # Default API base URL for local dev.
    api_url = api_base_url.strip() or os.getenv("AICO_STUDIO_API_BASE_URL") or "http://localhost:8771/api/v1"

    env = {
        "AICO_STUDIO_API_BASE_URL": api_url,
    }

    console.print(format_info(f"Using Studio directory: {studio_dir}"))
    console.print(format_info(f"Using API base URL: {api_url}"))

    console.print("🚀 [cyan]Starting Studio container...[/cyan]")
    code = _run_compose_file(compose_file, ["up", "-d", "--build"], env=env, cwd=studio_dir)
    if code != 0:
        raise typer.Exit(code)

    console.print("")
    console.print(format_success("✅ Studio deployment completed successfully!"))
    console.print(format_info("💡 Studio will be available at: http://localhost:3002"))
    console.print("")


def _get_or_create_grafana_password() -> str:
    """
    Get or create Grafana admin password using AICOKeyManager.
    
    Returns:
        Grafana admin password
    """
    config = ConfigurationManager()
    key_manager = AICOKeyManager(config)
    
    # Check if password already exists
    existing_password = key_manager.get_database_password("grafana", username="admin_password")
    if existing_password:
        console.print(format_info("Using existing Grafana password from keyring"))
        return existing_password
    
    # Generate new password
    console.print("🔐 [cyan]Generating new Grafana password from master key...[/cyan]")
    
    # Authenticate to get master key (prompts if needed)
    try:
        master_key = key_manager.authenticate(interactive=True)
    except Exception as e:
        console.print(format_error(f"Failed to authenticate: {e}"))
        raise typer.Exit(1)
    
    # Generate deterministic password from master key
    derived_key = key_manager.derive_purpose_key(master_key, "grafana-password")
    
    # Convert derived key to base64 URL-safe string for use as password
    import base64
    password = base64.urlsafe_b64encode(derived_key[:32]).decode('utf-8').rstrip('=')
    
    # Store in keyring
    key_manager.store_database_password(password, "grafana", username="admin_password")
    console.print(format_success("Generated and stored new Grafana password"))
    
    return password


def _nuke_grafana():
    """Completely destroy Grafana container and volume."""
    console.print("")
    console.print("💥 [bold red]NUKING GRAFANA[/bold red]")
    console.print("="*60)
    console.print("")
    
    # 1. Stop and remove container
    console.print("  [dim]→ Stopping Grafana container...[/dim]")
    _run_compose(["stop", "grafana"])
    
    console.print("  [dim]→ Removing Grafana container...[/dim]")
    _run_compose(["rm", "-f", "grafana"])
    
    # 2. Remove volume
    console.print("  [dim]→ Removing Grafana volume...[/dim]")
    try:
        subprocess.run(
            ["docker", "volume", "rm", "-f", "aico-grafanadata"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass
    
    console.print("")
    console.print(format_success("✓ Grafana nuked successfully"))
    console.print("")


def _ensure_docker_volume(volume_name: str) -> None:
    try:
        inspect = subprocess.run(
            ["docker", "volume", "inspect", volume_name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if inspect.returncode == 0:
            return

        create = subprocess.run(
            ["docker", "volume", "create", volume_name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if create.returncode != 0:
            console.print(format_error(f"Failed to create docker volume: {volume_name}"))
            raise typer.Exit(1)
    except FileNotFoundError:
        console.print(format_error("'docker' command not found. Install Docker and ensure it is on your PATH."))
        raise typer.Exit(1)


@app.command("valkey", help="Provision Valkey (Redis-compatible cache), optionally with --nuke for full reset")
def deploy_valkey(
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy Valkey container + volume before provisioning (DANGEROUS).",
    )
):
    """Deploy Valkey in-memory data store (Redis-compatible).
    
    This command is FULLY AUTOMATED:
    - No credentials needed (unauthenticated by default for local dev)
    - Starts Valkey container with persistence
    - Creates data volume for RDB snapshots
    
    Safe to run multiple times without --nuke. With --nuke it
    will wipe the Valkey volume and start from a clean slate.
    """
    console.print("\n" + "=" * 60)
    console.print("⚡ [bold cyan]AICO Valkey Deployment[/bold cyan]")
    console.print("=" * 60 + "\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing data!"))
        _nuke_valkey()

    console.print("🚀 [cyan]Starting Valkey container...[/cyan]")
    code = _run_compose(["up", "-d", "valkey"])
    if code != 0:
        console.print(format_error("Failed to start Valkey container"))
        raise typer.Exit(code)

    console.print("")
    console.print(format_success("✅ Valkey deployment completed successfully!"))
    console.print(format_info("💡 Valkey available at: localhost:6379"))
    console.print(format_info("💡 Redis-compatible protocol for caching and pub/sub"))
    console.print("")


@app.command("nats", help="Provision NATS (message broker), optionally with --nuke for full reset")
def deploy_nats(
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy NATS container before provisioning.",
    )
):
    """Deploy NATS message broker for event streaming.
    
    This command is FULLY AUTOMATED:
    - No credentials needed (unauthenticated by default for local dev)
    - Starts NATS container with JetStream enabled
    - Provides client port (4222) and monitoring port (8222)
    
    Safe to run multiple times without --nuke.
    """
    console.print("\n" + "=" * 60)
    console.print("📨 [bold cyan]AICO NATS Deployment[/bold cyan]")
    console.print("=" * 60 + "\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing NATS container!"))
        _nuke_nats()

    console.print("🚀 [cyan]Starting NATS container...[/cyan]")
    code = _run_compose(["up", "-d", "nats"])
    if code != 0:
        console.print(format_error("Failed to start NATS container"))
        raise typer.Exit(code)

    console.print("")
    console.print(format_success("✅ NATS deployment completed successfully!"))
    console.print(format_info("💡 Client port: 4222"))
    console.print(format_info("💡 Monitoring: http://localhost:8222"))
    console.print("")


@app.command("prometheus", help="Provision Prometheus (metrics), optionally with --nuke for full reset")
def deploy_prometheus(
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy Prometheus container + volume before provisioning (DANGEROUS).",
    )
):
    """Deploy Prometheus metrics collection and monitoring.
    
    This command is FULLY AUTOMATED:
    - No credentials needed (unauthenticated by default for local dev)
    - Starts Prometheus container with configuration
    - Creates data volume for time-series storage
    - Configures scrape targets for AICO services
    
    Safe to run multiple times without --nuke. With --nuke it
    will wipe the Prometheus volume and start from a clean slate.
    """
    console.print("\n" + "=" * 60)
    console.print("📊 [bold cyan]AICO Prometheus Deployment[/bold cyan]")
    console.print("=" * 60 + "\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing data!"))
        _nuke_prometheus()

    console.print("🚀 [cyan]Starting Prometheus container...[/cyan]")
    code = _run_compose(["up", "-d", "prometheus"])
    if code != 0:
        console.print(format_error("Failed to start Prometheus container"))
        raise typer.Exit(code)

    console.print("")
    console.print(format_success("✅ Prometheus deployment completed successfully!"))
    console.print(format_info("💡 Web UI: http://localhost:9090"))
    console.print(format_info("💡 Metrics endpoint for Grafana datasource configured"))
    console.print("")


@app.command("tempo", help="Provision Tempo (distributed tracing), optionally with --nuke for full reset")
def deploy_tempo(
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy Tempo container + volume before provisioning (DANGEROUS).",
    )
):
    """Deploy Grafana Tempo for distributed tracing.
    
    This command is FULLY AUTOMATED:
    - No credentials needed (unauthenticated by default for local dev)
    - Starts Tempo container with configuration
    - Creates data volume for trace storage
    - Supports OTLP, Jaeger, and Zipkin protocols
    
    Safe to run multiple times without --nuke. With --nuke it
    will wipe the Tempo volume and start from a clean slate.
    """
    console.print("\n" + "=" * 60)
    console.print("🔍 [bold cyan]AICO Tempo Deployment[/bold cyan]")
    console.print("=" * 60 + "\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing data!"))
        _nuke_tempo()

    console.print("🚀 [cyan]Starting Tempo container...[/cyan]")
    code = _run_compose(["up", "-d", "tempo"])
    if code != 0:
        console.print(format_error("Failed to start Tempo container"))
        raise typer.Exit(code)

    console.print("")
    console.print(format_success("✅ Tempo deployment completed successfully!"))
    console.print(format_info("💡 HTTP API: http://localhost:3200"))
    console.print(format_info("💡 OTLP gRPC: localhost:4317"))
    console.print(format_info("💡 Query traces via Grafana datasource"))
    console.print("")


@app.command("otel-collector", help="Provision OpenTelemetry Collector, optionally with --nuke for full reset")
def deploy_otel_collector(
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy OTel Collector container before provisioning.",
    )
):
    """Deploy OpenTelemetry Collector for telemetry aggregation.
    
    This command is FULLY AUTOMATED:
    - No credentials needed (configured via otel-collector-config.yaml)
    - Starts OTel Collector container
    - Receives telemetry from AICO services
    - Exports to Prometheus, Tempo, and Loki
    
    Safe to run multiple times without --nuke.
    """
    console.print("\n" + "=" * 60)
    console.print("📡 [bold cyan]AICO OpenTelemetry Collector Deployment[/bold cyan]")
    console.print("=" * 60 + "\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing OTel Collector container!"))
        _nuke_otel_collector()

    console.print("🚀 [cyan]Starting OpenTelemetry Collector container...[/cyan]")
    code = _run_compose(["up", "-d", "otel-collector"])
    if code != 0:
        console.print(format_error("Failed to start OTel Collector container"))
        raise typer.Exit(code)

    console.print("")
    console.print(format_success("✅ OpenTelemetry Collector deployment completed successfully!"))
    console.print(format_info("💡 OTLP gRPC: localhost:4317"))
    console.print(format_info("💡 OTLP HTTP: localhost:4318"))
    console.print(format_info("💡 Prometheus metrics: localhost:8888/metrics"))
    console.print(format_info("💡 Health check: localhost:8888"))
    console.print("")


def _nuke_valkey() -> int:
    """Destroy Valkey container and volume."""
    console.print("💣 [bold yellow]NUKING Valkey - cleanup of Docker artifacts...[/bold yellow]")

    _run_compose(["stop", "valkey"])
    _run_compose(["rm", "-f", "valkey"])

    try:
        subprocess.run(
            ["docker", "volume", "rm", "-f", "aico-valkeydata"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return 1

    console.print(format_success("✅ Valkey nuked"))
    return 0


def _nuke_nats() -> int:
    """Destroy NATS container."""
    console.print("💣 [bold yellow]NUKING NATS - cleanup of Docker artifacts...[/bold yellow]")

    _run_compose(["stop", "nats"])
    _run_compose(["rm", "-f", "nats"])

    console.print(format_success("✅ NATS nuked"))
    return 0


def _nuke_prometheus() -> int:
    """Destroy Prometheus container and volume."""
    console.print("💣 [bold yellow]NUKING Prometheus - cleanup of Docker artifacts...[/bold yellow]")

    _run_compose(["stop", "prometheus"])
    _run_compose(["rm", "-f", "prometheus"])

    try:
        subprocess.run(
            ["docker", "volume", "rm", "-f", "aico-prometheusdata"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return 1

    console.print(format_success("✅ Prometheus nuked"))
    return 0


def _nuke_tempo() -> int:
    """Destroy Tempo container and volume."""
    console.print("💣 [bold yellow]NUKING Tempo - cleanup of Docker artifacts...[/bold yellow]")

    _run_compose(["stop", "tempo"])
    _run_compose(["rm", "-f", "tempo"])

    try:
        subprocess.run(
            ["docker", "volume", "rm", "-f", "aico-tempodata"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return 1

    console.print(format_success("✅ Tempo nuked"))
    return 0


def _nuke_otel_collector() -> int:
    """Destroy OpenTelemetry Collector container."""
    console.print("💣 [bold yellow]NUKING OpenTelemetry Collector - cleanup of Docker artifacts...[/bold yellow]")

    _run_compose(["stop", "otel-collector"])
    _run_compose(["rm", "-f", "otel-collector"])

    console.print(format_success("✅ OpenTelemetry Collector nuked"))
    return 0


def _nuke_gateway() -> int:
    """Destroy the Gateway container (and any related artifacts that are safe to remove)."""
    console.print("💣 [bold yellow]NUKING Gateway - cleanup of Docker artifacts...[/bold yellow]")

    _run_compose(["kill", "gateway"])
    _run_compose(["rm", "-f", "gateway"])

    try:
        subprocess.run(
            ["docker", "rm", "-f", "aico-gateway"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return 1

    try:
        result = subprocess.run(
            ["docker", "ps", "-aq", "--filter", "label=com.aico.component=gateway"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            container_ids = result.stdout.strip().split("\n")
            subprocess.run(
                ["docker", "rm", "-f", *container_ids],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except FileNotFoundError:
        return 1

    console.print(format_success("✅ Gateway nuked"))
    return 0


def _nuke_core() -> int:
    """Destroy the Core container (and any related artifacts that are safe to remove)."""
    console.print("💣 [bold yellow]NUKING Core - cleanup of Docker artifacts...[/bold yellow]")

    _run_compose(["kill", "core"])
    _run_compose(["rm", "-f", "core"])

    try:
        subprocess.run(
            ["docker", "rm", "-f", "aico-core"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return 1

    try:
        result = subprocess.run(
            ["docker", "ps", "-aq", "--filter", "label=com.aico.component=core"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            container_ids = result.stdout.strip().split("\n")
            subprocess.run(
                ["docker", "rm", "-f", *container_ids],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except FileNotFoundError:
        return 1

    console.print(format_success("✅ Core nuked"))
    return 0


def _nuke_modelservice() -> int:
    """Destroy the Modelservice container (and any related artifacts that are safe to remove)."""
    console.print("💣 [bold yellow]NUKING Modelservice - cleanup of Docker artifacts...[/bold yellow]")

    _run_compose(["kill", "modelservice"])
    _run_compose(["rm", "-f", "modelservice"])

    try:
        subprocess.run(
            ["docker", "rm", "-f", "aico-modelservice"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return 1

    try:
        result = subprocess.run(
            ["docker", "ps", "-aq", "--filter", "label=com.aico.component=modelservice"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            container_ids = result.stdout.strip().split("\n")
            subprocess.run(
                ["docker", "rm", "-f", *container_ids],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except FileNotFoundError:
        return 1

    console.print(format_success("✅ Modelservice nuked"))
    return 0
