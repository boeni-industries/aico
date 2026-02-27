"""AICO CLI Deploy Commands

High-level orchestration for deploying and bootstrapping infrastructure
backends (Postgres, InfluxDB, Loki, and Grafana). These commands are intended to be used
in CI/CD pipelines or for one-shot local provisioning.

Fully automated credential management (ZERO manual effort):
- Backend containers auto-generate PostgreSQL password on first run via entrypoint script
- Credentials are persisted in docker/.env for reuse across container restarts
- CLI deploy commands ensure docker/.env exists with all required credentials
- Containers receive credentials via environment variable injection
- Fallback: CLI generates credentials if docker/.env doesn't exist
- Zero manual credential management required - just run docker-compose up
"""

import sys
import subprocess
import secrets
import os
import asyncio
import stat
from pathlib import Path
from typing import Tuple

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
    """Resolve the AICO repo root by walking upwards from this file."""

    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    # Fallback: assume cli/commands/deploy.py => repo root is three levels up
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


def _persist_credential(key: str, value: str) -> None:
    """Persist a single credential to docker/.env."""
    compose_file = _get_compose_file()
    env_file = compose_file.parent / ".env"
    
    # Load existing
    existing = _load_env_file(env_file) if env_file.exists() else {}
    
    # Update
    existing[key] = value
    
    # Save
    _write_env_file(env_file, existing)

def _persist_compose_env(env: dict[str, str]) -> None:
    """Persist credentials in docker/.env so docker compose always has them."""

    compose_file = _get_compose_file()
    env_file = compose_file.parent / ".env"
    existing = _load_env_file(env_file)

    updated = dict(existing)
    for key, value in env.items():
        if value is None:
            continue
        if isinstance(value, str) and value != "":
            updated[key] = value

    if updated != existing:
        _write_env_file(env_file, updated)


def _generate_secure_password(length: int = 32) -> str:
    """Generate a cryptographically secure password."""
    # Use URL-safe base64 encoding for compatibility
    return secrets.token_urlsafe(length)


def _ensure_all_credentials() -> None:
    """
    Ensure ALL required credentials exist before any service starts.
    This prevents password mismatches and initialization failures.
    """
    compose_file = _get_compose_file()
    env_file = compose_file.parent / ".env"
    
    # Load existing
    existing = _load_env_file(env_file) if env_file.exists() else {}
    
    # Required credentials with their lengths
    required = {
        'AICO_PG_PASSWORD': 32,
        'AICO_INFLUX_ADMIN_PASSWORD': 32,
        'AICO_INFLUX_ADMIN_TOKEN': 48,
        # Keep JWT signing stable across container restarts/rebuilds.
        # Key name matches AICOKeyManager.get_jwt_secret("api_gateway") => "api_gateway_jwt_secret"
        # CredentialProvider env var name: AICO_API_GATEWAY_JWT_SECRET
        'AICO_API_GATEWAY_JWT_SECRET': 48,
    }
    
    # Generate missing credentials
    updated = False
    for key, length in required.items():
        if key not in existing or not existing[key]:
            existing[key] = _generate_secure_password(length)
            updated = True
            console.print(format_info(f"Generated {key}"))
    
    # Save if any were generated
    if updated:
        _write_env_file(env_file, existing)
        console.print(format_success("✓ Credentials initialized in docker/.env"))

def _get_or_create_postgres_password() -> str:
    """
    Get or create Postgres password - FULLY AUTOMATIC.
    
    Priority:
    1. docker/.env file (persisted credentials - may be auto-generated by container entrypoint)
    2. AICO_PG_PASSWORD environment variable
    3. Auto-generate and save to docker/.env (CLI fallback)
    
    Note: Backend containers have entrypoint scripts that auto-generate passwords
    on first run if docker/.env doesn't exist. This function ensures docker/.env
    exists before containers start, providing a fallback if needed.
    
    Returns:
        Postgres password
    """
    # Ensure all credentials exist first
    _ensure_all_credentials()
    
    # Check docker/.env first (persistent storage)
    compose_file = _get_compose_file()
    env_file = compose_file.parent / ".env"
    
    if env_file.exists():
        env_vars = _load_env_file(env_file)
        if password := env_vars.get("AICO_PG_PASSWORD"):
            console.print(format_info("Using Postgres password from docker/.env"))
            return password
    
    # Check environment variable
    if password := os.getenv("AICO_PG_PASSWORD"):
        console.print(format_info("Using Postgres password from environment"))
        # Save to .env for persistence
        _persist_credential("AICO_PG_PASSWORD", password)
        return password
    
    # Auto-generate and persist
    console.print(format_info("Auto-generating Postgres password..."))
    password = _generate_secure_password(32)
    _persist_credential("AICO_PG_PASSWORD", password)
    console.print(format_success("✓ Postgres password generated and saved to docker/.env"))
    
    return password


def _setup_influx_downsampling(admin_token: str) -> None:
    """
    Configure InfluxDB downsampling tasks and retention policies.
    This is idempotent - safe to run multiple times.
    """
    from influxdb_client import InfluxDBClient, BucketRetentionRules
    
    config = ConfigurationManager()
    url = config.get("influx.url")
    org = config.get("influx.org")
    
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
            
            tasks_to_create = [
                ("downsample_api_requests", 'from(bucket: "aico_telemetry") |> range(start: -1m) |> filter(fn: (r) => r._measurement == "api_request") |> filter(fn: (r) => r._field == "latency_ms_f" or r._field == "status_code_i") |> aggregateWindow(every: 1m, fn: mean, createEmpty: false) |> set(key: "_measurement", value: "api_request_1m") |> to(bucket: "aico_telemetry_downsampled", org: "aico")'),
                ("downsample_api_counts", 'from(bucket: "aico_telemetry") |> range(start: -1m) |> filter(fn: (r) => r._measurement == "api_request") |> filter(fn: (r) => r._field == "status_code_i") |> aggregateWindow(every: 1m, fn: count, createEmpty: false) |> set(key: "_measurement", value: "api_request_counts_1m") |> to(bucket: "aico_telemetry_downsampled", org: "aico")'),
                ("downsample_messagebus", 'from(bucket: "aico_telemetry") |> range(start: -1m) |> filter(fn: (r) => r._measurement == "messagebus_event") |> filter(fn: (r) => r._field == "message_count_i" or r._field == "latency_ms_f") |> aggregateWindow(every: 1m, fn: sum, createEmpty: false) |> set(key: "_measurement", value: "messagebus_event_1m") |> to(bucket: "aico_telemetry_downsampled", org: "aico")'),
                ("downsample_scheduler", 'from(bucket: "aico_telemetry") |> range(start: -1m) |> filter(fn: (r) => r._measurement == "scheduler_job") |> filter(fn: (r) => r._field == "latency_ms_f" or r._field == "success_b") |> aggregateWindow(every: 1m, fn: mean, createEmpty: false) |> set(key: "_measurement", value: "scheduler_job_1m") |> to(bucket: "aico_telemetry_downsampled", org: "aico")'),
                ("downsample_memory_queries", 'from(bucket: "aico_telemetry") |> range(start: -1m) |> filter(fn: (r) => r._measurement == "memory_query") |> filter(fn: (r) => r._field == "latency_ms_f" or r._field == "result_count_i") |> aggregateWindow(every: 1m, fn: mean, createEmpty: false) |> set(key: "_measurement", value: "memory_query_1m") |> to(bucket: "aico_telemetry_downsampled", org: "aico")'),
                ("downsample_model_inference", 'from(bucket: "aico_telemetry") |> range(start: -1m) |> filter(fn: (r) => r._measurement == "model_inference") |> filter(fn: (r) => r._field == "latency_ms_f" or r._field == "token_count_i") |> aggregateWindow(every: 1m, fn: mean, createEmpty: false) |> set(key: "_measurement", value: "model_inference_1m") |> to(bucket: "aico_telemetry_downsampled", org: "aico")'),
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
    
    Priority:
    1. docker/.env file (persisted credentials)
    2. Environment variables
    3. Auto-generate and save to docker/.env
    
    Returns:
        Tuple of (admin_password, admin_token)
    """
    # Check docker/.env first (persistent storage)
    compose_file = _get_compose_file()
    env_file = compose_file.parent / ".env"
    
    if env_file.exists():
        env_vars = _load_env_file(env_file)
        password = env_vars.get("AICO_INFLUX_ADMIN_PASSWORD")
        token = env_vars.get("AICO_INFLUX_ADMIN_TOKEN")
        if password and token:
            console.print(format_info("Using InfluxDB credentials from docker/.env"))
            return password, token
    
    # Check environment variables
    env_password = os.getenv("AICO_INFLUX_ADMIN_PASSWORD")
    env_token = os.getenv("AICO_INFLUX_ADMIN_TOKEN")
    if env_password and env_token:
        console.print(format_info("Using InfluxDB credentials from environment"))
        # Save to .env for persistence
        _persist_credential("AICO_INFLUX_ADMIN_PASSWORD", env_password)
        _persist_credential("AICO_INFLUX_ADMIN_TOKEN", env_token)
        return env_password, env_token
    
    # Auto-generate and persist
    console.print(format_info("Auto-generating InfluxDB credentials..."))
    password = _generate_secure_password(32)
    token = _generate_secure_password(48)
    _persist_credential("AICO_INFLUX_ADMIN_PASSWORD", password)
    _persist_credential("AICO_INFLUX_ADMIN_TOKEN", token)
    console.print(format_success("✓ InfluxDB credentials generated and saved to docker/.env"))
    
    return password, token


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
        # Use the compose file directory as the working directory so docker/.env
        # is consistently picked up by docker compose (and relative paths resolve correctly).
        result = subprocess.run(cmd, check=False, env=run_env, cwd=str(compose_file.parent))
        if result.returncode != 0:
            console.print(
                format_error(
                    f"docker compose command failed with exit code {result.returncode}:\n"
                    + " ".join(cmd)
                )
            )
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

    # 4. Remove Docker images (postgres:18.1 and any dangling images)
    console.print("  [dim]→ Removing Docker images...[/dim]")
    try:
        # Remove specific postgres image
        subprocess.run(
            ["docker", "rmi", "-f", "postgres:18.1"],
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


app = typer.Typer(help="Deploy and provision AICO infrastructure")


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

    # Get or create InfluxDB credentials (prompts for master password if needed)
    admin_password, admin_token = _get_or_create_influx_credentials()
    
    # Prepare environment for container
    container_env = {
        "AICO_INFLUX_ADMIN_PASSWORD": admin_password,
        "AICO_INFLUX_ADMIN_TOKEN": admin_token
    }

    _persist_compose_env(container_env)

    console.print("🚀 [cyan]Starting InfluxDB container with auto-generated credentials...[/cyan]")
    code = _run_compose(["up", "-d", "influxdb"], env=container_env)
    if code != 0:
        console.print(format_error("Failed to start InfluxDB container"))
        raise typer.Exit(code)

    console.print("⏳ [cyan]Waiting for InfluxDB to be ready...[/cyan]")
    import time
    time.sleep(8)  # Give InfluxDB time to auto-initialize with DOCKER_INFLUXDB_INIT_* env vars

    non_interactive = (not sys.stdin.isatty()) or (os.getenv("AICO_NONINTERACTIVE") == "true")
    run_checks = os.getenv("AICO_DEPLOY_INFLUX_DOCTOR") == "true"
    run_downsampling = os.getenv("AICO_DEPLOY_INFLUX_DOWNSAMPLING") == "true"

    if non_interactive and not run_checks:
        console.print("[dim]Skipping InfluxDB doctor in non-interactive mode (set AICO_DEPLOY_INFLUX_DOCTOR=true to enable).[/dim]")
    else:
        console.print("🩺 [cyan]Verifying deployment health...[/cyan]")
        influx_cli.doctor()

    if non_interactive and not run_downsampling:
        console.print("[dim]Skipping downsampling setup in non-interactive mode (set AICO_DEPLOY_INFLUX_DOWNSAMPLING=true to enable).[/dim]")
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
    """Deploy AICO Gateway container with automatic credential management.
    
    Credentials are handled automatically:
    - CLI ensures docker/.env exists with all required credentials
    - Container entrypoint auto-generates missing credentials on first run
    - Credentials persist across container restarts via docker/.env
    - Zero manual configuration required
    """
    console.print("\n" + "=" * 60)
    console.print("🌐 [bold cyan]AICO Gateway Deployment[/bold cyan]")
    console.print("=" * 60 + "\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing Gateway container!"))
        _nuke_gateway()

    # Ensure credentials exist in docker/.env (CLI-side generation as fallback)
    # Container entrypoint will also auto-generate if missing
    pg_password = _get_or_create_postgres_password()
    influx_password, influx_token = _get_or_create_influx_credentials()

    env = {
        "AICO_PG_PASSWORD": pg_password,
        "AICO_INFLUX_ADMIN_PASSWORD": influx_password,
        "AICO_INFLUX_ADMIN_TOKEN": influx_token,
    }

    _persist_compose_env(env)

    args = ["up", "-d", "--build", "gateway"]

    console.print("🚀 [cyan]Starting Gateway container...[/cyan]")
    code = _run_compose(args, env=env)
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
    """Deploy AICO Core container with automatic credential management.
    
    Credentials are handled automatically:
    - CLI ensures docker/.env exists with all required credentials
    - Container entrypoint auto-generates missing credentials on first run
    - Credentials persist across container restarts via docker/.env
    - Zero manual configuration required
    """
    console.print("\n" + "=" * 60)
    console.print("🧠 [bold cyan]AICO Core Deployment[/bold cyan]")
    console.print("=" * 60 + "\n")

    if nuke:
        console.print(format_warning("⚠️  --nuke flag detected: Will destroy existing Core container!"))
        _nuke_core()

    # Ensure credentials exist in docker/.env (CLI-side generation as fallback)
    # Container entrypoint will also auto-generate if missing
    pg_password = _get_or_create_postgres_password()
    influx_password, influx_token = _get_or_create_influx_credentials()

    env = {
        "AICO_PG_PASSWORD": pg_password,
        "AICO_INFLUX_ADMIN_PASSWORD": influx_password,
        "AICO_INFLUX_ADMIN_TOKEN": influx_token,
    }

    _persist_compose_env(env)

    args = ["up", "-d", "--build", "core"]

    console.print("🚀 [cyan]Starting Core container...[/cyan]")
    code = _run_compose(args, env=env)
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

    # Ensure credentials exist in docker/.env for consistency
    pg_password = _get_or_create_postgres_password()
    influx_password, influx_token = _get_or_create_influx_credentials()

    env = {
        "AICO_PG_PASSWORD": pg_password,
        "AICO_INFLUX_ADMIN_PASSWORD": influx_password,
        "AICO_INFLUX_ADMIN_TOKEN": influx_token,
    }

    _persist_compose_env(env)

    args = ["up", "-d", "--build", "modelservice"]

    console.print("🚀 [cyan]Starting Modelservice container...[/cyan]")
    code = _run_compose(args, env=env)
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
    
    _persist_compose_env(env)

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

    # Resolve studio path WITHOUT ConfigurationManager to avoid keyring blocking
    # Priority: env var > convention default
    env_key = "AICO_COMPONENT_STUDIO_DIR"
    if override := os.getenv(env_key):
        studio_dir = Path(override).expanduser().resolve()
    else:
        repo_root = _get_aico_repo_root()
        studio_dir = (repo_root / "../aico-studio").resolve()
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
