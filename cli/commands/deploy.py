"""AICO CLI Deploy Commands

High-level orchestration for deploying and bootstrapping infrastructure
backends (Postgres, InfluxDB, Loki, and Grafana). These commands are intended to be used
in CI/CD pipelines or for one-shot local provisioning.

Fully automated credential management:
- Master password is the ONLY manual input
- All database passwords/tokens are auto-generated from master key
- Credentials are stored in system keyring via AICOKeyManager
- Containers receive credentials via environment variable injection
- Zero manual credential management required
"""

import sys
import subprocess
import secrets
import os
import asyncio
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


def _generate_secure_password(length: int = 32) -> str:
    """Generate a cryptographically secure password."""
    # Use URL-safe base64 encoding for compatibility
    return secrets.token_urlsafe(length)


def _get_or_create_postgres_password() -> str:
    """
    Get or create Postgres password using AICOKeyManager.
    
    This ensures the password is derived from the master key and stored
    securely in the system keyring. The master password prompt happens
    automatically if needed.
    
    Returns:
        Postgres password
    """
    config = ConfigurationManager()
    key_manager = AICOKeyManager(config)
    
    # Check if password already exists
    existing_password = key_manager.get_database_password("postgres", username="postgres")
    if existing_password:
        console.print(format_info("Using existing Postgres password from keyring"))
        return existing_password
    
    # Generate new password (this will prompt for master password if needed)
    console.print("🔐 [cyan]Generating new Postgres password from master key...[/cyan]")
    
    # Authenticate to get master key (prompts if needed)
    try:
        master_key = key_manager.authenticate(interactive=True)
    except Exception as e:
        console.print(format_error(f"Failed to authenticate: {e}"))
        raise typer.Exit(1)
    
    # Generate deterministic password from master key
    # Use purpose-specific derivation for Postgres
    derived_key = key_manager.derive_purpose_key(master_key, "postgres-password")
    
    # Convert derived key to base64 URL-safe string for use as password
    import base64
    password = base64.urlsafe_b64encode(derived_key[:32]).decode('utf-8').rstrip('=')
    
    # Store in keyring
    key_manager.store_database_password(password, "postgres", username="postgres")
    console.print(format_success("Generated and stored new Postgres password"))
    
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
    Get or create InfluxDB admin password and token using AICOKeyManager.
    
    Returns:
        Tuple of (admin_password, admin_token)
    """
    config = ConfigurationManager()
    key_manager = AICOKeyManager(config)
    
    # Check if credentials already exist
    existing_password = key_manager.get_database_password("influx", username="admin")
    existing_token = key_manager.get_database_password("influx", username="admin_token")
    
    if existing_password and existing_token:
        console.print(format_info("Using existing InfluxDB credentials from keyring"))
        return existing_password, existing_token
    
    # Generate new credentials
    console.print("🔐 [cyan]Generating new InfluxDB credentials from master key...[/cyan]")
    
    # Authenticate to get master key (prompts if needed)
    try:
        master_key = key_manager.authenticate(interactive=True)
    except Exception as e:
        console.print(format_error(f"Failed to authenticate: {e}"))
        raise typer.Exit(1)
    
    # Generate deterministic credentials from master key
    password_key = key_manager.derive_purpose_key(master_key, "influx-admin-password")
    token_key = key_manager.derive_purpose_key(master_key, "influx-admin-token")
    
    # Convert derived keys to base64 URL-safe strings for use as credentials
    import base64
    password = base64.urlsafe_b64encode(password_key[:32]).decode('utf-8').rstrip('=')
    token = base64.urlsafe_b64encode(token_key[:64]).decode('utf-8').rstrip('=')
    
    # Store in keyring
    key_manager.store_database_password(password, "influx", username="admin")
    key_manager.store_database_password(token, "influx", username="admin_token")
    console.print(format_success("Generated and stored new InfluxDB credentials"))
    
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
        result = subprocess.run(cmd, check=False, env=run_env)
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


def _nuke_postgres() -> int:
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


app = typer.Typer(
    help="Deployment orchestration for AICO backends (Postgres, InfluxDB, Loki).",
    invoke_without_command=False,
)


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

    console.print("🚀 [cyan]Starting InfluxDB container with auto-generated credentials...[/cyan]")
    code = _run_compose(["up", "-d", "influxdb"], env=container_env)
    if code != 0:
        console.print(format_error("Failed to start InfluxDB container"))
        raise typer.Exit(code)

    console.print("⏳ [cyan]Waiting for InfluxDB to be ready...[/cyan]")
    import time
    time.sleep(8)  # Give InfluxDB time to auto-initialize with DOCKER_INFLUXDB_INIT_* env vars

    console.print("🩺 [cyan]Verifying deployment health...[/cyan]")
    influx_cli.doctor()

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
    grafana_url = config.get("grafana.url", "http://127.0.0.1:3000")
    
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
