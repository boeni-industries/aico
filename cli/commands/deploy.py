"""AICO CLI Deploy Commands

High-level orchestration for deploying and bootstrapping infrastructure
backends (Postgres and InfluxDB). These commands are intended to be used
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
    password = secrets.token_urlsafe(32)  # Generate from derived key entropy
    
    # Store in keyring
    key_manager.store_database_password(password, "postgres", username="postgres")
    console.print(format_success("Generated and stored new Postgres password"))
    
    return password


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
    
    password = secrets.token_urlsafe(32)
    token = secrets.token_urlsafe(64)  # Longer token for API access
    
    # Store in keyring
    key_manager.store_database_password(password, "influx", username="admin")
    key_manager.store_database_password(token, "influx", username="admin_token")
    console.print(format_success("Generated and stored new InfluxDB credentials"))
    
    return password, token


def _get_compose_file() -> Path:
    """Return path to the local docker-compose file for DB services."""
    root = Path(__file__).parent.parent.parent
    return root / "docker" / "docker-compose.local.yml"


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
    help="Deployment orchestration for AICO backends (Postgres, InfluxDB).",
    invoke_without_command=False,
)


@app.command("pg", help="Provision Postgres (container + schema), optionally with --nuke for full reset")
def deploy_pg(
    nuke: bool = typer.Option(
        False,
        "--nuke",
        help="Destroy Postgres container + volume before provisioning (DANGEROUS).",
    )
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
        _nuke_postgres()

    # Get or create Postgres password (prompts for master password if needed)
    pg_password = _get_or_create_postgres_password()
    
    # Get Postgres config for connection details
    from aico.core.config import ConfigurationManager
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    pg_cfg = config.get("core.database.postgres", {}) or {}
    host = pg_cfg.get("host", "127.0.0.1")
    port = int(pg_cfg.get("port", 5432))
    
    # Prepare environment for container
    container_env = {
        "AICO_PG_PASSWORD": pg_password
    }

    console.print("🚀 [cyan]Starting Postgres container with auto-generated credentials...[/cyan]")
    code = _run_compose(["up", "-d", "postgres"], env=container_env)
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
                pg_cli.init()

                break
        except (OSError, socket.timeout):
            time.sleep(wait_interval)
            elapsed += wait_interval
    else:
        console.print(format_warning(f"Postgres did not become ready within {max_wait} seconds, continuing anyway..."))
        console.print("🔧 [cyan]Applying schema (idempotent)...[/cyan]")
        pg_cli.init()

    console.print("🩺 [cyan]Verifying deployment health...[/cyan]")
    pg_cli.doctor()

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
    time.sleep(5)  # Give InfluxDB time to initialize

    console.print("🔧 [cyan]Setting up org/bucket/retention (idempotent)...[/cyan]")
    # Call init with the auto-generated credentials
    influx_cli.init(admin_password=admin_password, admin_token=admin_token)

    console.print("🩺 [cyan]Verifying deployment health...[/cyan]")
    influx_cli.doctor()

    console.print("\n" + format_success("✅ InfluxDB deployment completed successfully!"))
    console.print(format_info("💡 Credentials stored in system keyring (derived from master key)"))
    console.print(format_info("💡 Backend components will auto-retrieve credentials from keyring at runtime"))
    console.print("")
