"""
AICO Development Commands

Commands for development workflows including data cleanup and security reset.
These commands are designed for development/testing and should be used with caution.

⚠️  SECURITY WARNING: These commands are DESTRUCTIVE and should NEVER be used in production!
"""

import os
import typer
import subprocess
import sys
from rich.console import Console
from pathlib import Path
import shutil
from aico.security import AICOKeyManager
from aico.core.paths import AICOPaths
from aico.core.config import ConfigurationManager

console = Console()

def dev_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("wipe", "Wipe development data with granular control (--security, --data, --config, --all)"),
            ("protoc", "Compile Protocol Buffer files to Python code")
        ]
        
        examples = [
            "aico dev wipe --security",
            "aico dev wipe --data", 
            "aico dev wipe --security --data",
            "aico dev wipe --all",
            "aico dev wipe --all --dry-run",
            "aico dev protoc"
        ]
        
        format_subcommand_help(
            console=console,
            command_name="dev",
            description="Development utilities for data cleanup and security reset",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()

app = typer.Typer(
    help="🧹 Development utilities (DESTRUCTIVE - dev only)",
    callback=dev_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)


def _check_development_environment():
    """Ensure we're in a development environment before allowing destructive operations."""
    # Check explicit production flag
    if os.getenv("AICO_ENV") == "production":
        console.print("❌ [bold red]SECURITY BLOCK: Development commands disabled in production environment[/bold red]")
        console.print("💡 [dim]Set AICO_ENV=development to enable (only in dev environments!)[/dim]")
        raise typer.Exit(1)
    
    # Check for development indicators
    cwd = Path.cwd()
    dev_indicators = [
        cwd / ".git",
        cwd / "pyproject.toml", 
        cwd / "package.json",
        cwd / "requirements.txt",
        cwd / "shared",  # AICO development structure
    ]
    
    if not any(indicator.exists() for indicator in dev_indicators):
        console.print("❌ [bold red]SECURITY BLOCK: No development environment detected[/bold red]")
        console.print("💡 [dim]Development commands require development project structure[/dim]")
        raise typer.Exit(1)


def _require_explicit_confirmation(operation_name: str, items_to_delete: list):
    """Require explicit typed confirmation for destructive operations."""
    console.print(f"🚨 [bold red]DESTRUCTIVE OPERATION: {operation_name}[/bold red]")
    console.print("📝 [yellow]This will permanently delete:[/yellow]")
    
    for item in items_to_delete:
        console.print(f"  • {item}")
    
    console.print("\n⚠️ [red]This action CANNOT be undone![/red]")
    console.print("💡 [dim]Consider backing up important data first[/dim]")
    
    # Require typing YES to confirm
    confirmation = typer.prompt("\nType 'YES' (in capitals) to confirm", show_default=False)
    if confirmation != "YES":
        console.print("❌ [yellow]Confirmation failed. Operation cancelled.[/yellow]")
        raise typer.Exit()


@app.command(help="Wipe development data with granular control")
def wipe(
    security: bool = typer.Option(False, "--security", help="Clear master password and keyring data"),
    data: bool = typer.Option(False, "--data", help="Remove databases and salt files"),
    config: bool = typer.Option(False, "--config", help="Remove configuration files"),
    cache: bool = typer.Option(False, "--cache", help="Remove cache and temporary files"),
    app_dir: bool = typer.Option(False, "--app-dir", help="Remove entire application directory"),
    all: bool = typer.Option(False, "--all", help="Wipe everything (security + data + config + cache + app-dir)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted without doing it"),
    i_know_what_im_doing: bool = typer.Option(False, "--i-know-what-im-doing", help="Skip environment checks (DANGEROUS)")
):
    """🧹 Wipe development data with granular control.
    
    Examples:
      aico dev wipe --security          # Clear keyring only
      aico dev wipe --data             # Remove databases/salt files only
      aico dev wipe --security --data  # Reset security + remove databases
      aico dev wipe --app-dir          # Nuclear option: remove entire app directory
      aico dev wipe --all              # Everything (security + data + config + cache + app-dir)
      aico dev wipe --all --dry-run    # Preview what would be deleted
    """
    
    # Security checks (unless explicitly bypassed)
    if not i_know_what_im_doing:
        _check_development_environment()
    
    # Determine what to wipe
    if all:
        security = data = config = cache = app_dir = True
    
    if not (security or data or config or cache or app_dir):
        console.print("❌ [red]No wipe targets specified. Use --security, --data, --config, --cache, --app-dir, or --all[/red]")
        console.print("💡 [dim]Run 'aico dev wipe --help' for examples[/dim]")
        raise typer.Exit(1)
    
    # Build list of items to delete
    items_to_delete = []
    if security:
        items_to_delete.extend([
            "Master password from OS keyring",
            "Cached security keys",
            "Key creation timestamps",
            "Database-specific passwords"
        ])
    if data:
        items_to_delete.extend([
            "Database files (.db)",
            "Salt files (.salt)"
        ])
    if config:
        items_to_delete.extend([
            "Configuration files (.yaml, .yml, .json)"
        ])
    if cache:
        items_to_delete.extend([
            "Cache directories",
            "Temporary files",
            "Log files"
        ])
    if app_dir:
        items_to_delete.extend([
            "Entire application directory (nuclear option)"
        ])
    
    # Dry run mode
    if dry_run:
        console.print("🔍 [cyan]DRY RUN - Would delete:[/cyan]")
        for item in items_to_delete:
            console.print(f"  • {item}")
        console.print("\n💡 [dim]Remove --dry-run to execute[/dim]")
        return
    
    # Require explicit confirmation
    operation_name = "wipe-all" if all else f"wipe-{'security-' if security else ''}{'data-' if data else ''}{'config' if config else ''}".rstrip('-')
    _require_explicit_confirmation(operation_name, items_to_delete)
    
    try:
        files_deleted = 0
        dirs_deleted = 0
        
        # Wipe security
        if security:
            console.print("🔐 [yellow]Clearing security data...[/yellow]")
            config = ConfigurationManager()
            config.initialize(lightweight=True)
            key_manager = AICOKeyManager(config)
            
            # Clear all keyring entries more thoroughly
            try:
                import keyring
                service_name = key_manager.service_name
                
                # Clear core security keys
                for key_name in ["master_key", "salt", "key_created"]:
                    try:
                        keyring.delete_password(service_name, key_name)
                        console.print(f"🗑️ Cleared: {key_name}")
                    except keyring.errors.PasswordDeleteError:
                        console.print(f"📭 [dim]Key '{key_name}' not found in keyring[/dim]")
                    except Exception as e:
                        console.print(f"⚠️ [yellow]Failed to delete key '{key_name}': {e}[/yellow]")
                
                # Clear database-specific passwords (multiple patterns)
                db_patterns = [
                    "libsql_password", "duckdb_password", "chroma_password", "rocksdb_password",
                    "libsql_aico_password", "duckdb_aico_password", "chroma_aico_password",
                    "aico_password", "database_password"
                ]
                
                for pattern in db_patterns:
                    try:
                        keyring.delete_password(service_name, pattern)
                        console.print(f"🗑️ Cleared: {pattern}")
                    except keyring.errors.PasswordDeleteError:
                        console.print(f"📭 [dim]Password '{pattern}' not found in keyring[/dim]")
                    except Exception as e:
                        console.print(f"⚠️ [yellow]Failed to delete password '{pattern}': {e}[/yellow]")
                
                # Also try clearing with @AICO suffix (Windows Credential Manager pattern)
                for pattern in db_patterns:
                    try:
                        keyring.delete_password(service_name, f"{pattern}@AICO")
                        console.print(f"🗑️ Cleared: {pattern}@AICO")
                    except keyring.errors.PasswordDeleteError:
                        console.print(f"📭 [dim]Password '{pattern}@AICO' not found in keyring[/dim]")
                    except Exception as e:
                        console.print(f"⚠️ [yellow]Failed to delete password '{pattern}@AICO': {e}[/yellow]")
                        
            except Exception as e:
                console.print(f"⚠️ [yellow]Keyring cleanup warning: {e}[/yellow]")
            
            console.print("✅ [green]Security data cleared[/green]")
        
        # Wipe data (databases and salt files only)
        if data:
            console.print("🗄️ [yellow]Removing database files...[/yellow]")
            data_dir = AICOPaths.get_data_directory()
            
            if data_dir.exists():
                for item in data_dir.rglob("*"):
                    try:
                        if item.is_file() and (item.suffix in ['.db', '.salt'] or item.name.endswith('.db.salt')):
                            console.print(f"🗑️ Deleting: {item.name}")
                            item.unlink()
                            files_deleted += 1
                    except Exception as e:
                        console.print(f"⚠️ [yellow]Could not delete {item}: {e}[/yellow]")
            
            console.print(f"✅ [green]Database files removed ({files_deleted} files)[/green]")
        
        # Wipe cache
        if cache:
            console.print("🗂️ [yellow]Removing cache and temporary files...[/yellow]")
            data_dir = AICOPaths.get_data_directory()
            
            if data_dir.exists():
                for item in data_dir.rglob("*"):
                    try:
                        if item.is_dir() and item.name in ['chroma', 'vectors', 'embeddings', 'cache', 'tmp', 'temp', 'logs']:
                            console.print(f"🗑️ Deleting directory: {item.name}")
                            shutil.rmtree(item)
                            dirs_deleted += 1
                        elif item.is_file() and item.suffix in ['.log', '.tmp', '.cache']:
                            console.print(f"🗑️ Deleting: {item.name}")
                            item.unlink()
                            files_deleted += 1
                    except Exception as e:
                        console.print(f"⚠️ [yellow]Could not delete {item}: {e}[/yellow]")
            
            console.print(f"✅ [green]Cache files removed ({files_deleted} files, {dirs_deleted} dirs)[/green]")
        
        # Nuclear option: remove entire app directory
        if app_dir:
            console.print("💥 [yellow]Removing entire AICO application directory...[/yellow]")
            data_dir = AICOPaths.get_data_directory()
            
            if data_dir.exists():
                # Count items for reporting
                all_items = list(data_dir.rglob("*"))
                total_files = len([item for item in all_items if item.is_file()])
                total_dirs = len([item for item in all_items if item.is_dir()])
                
                console.print(f"🗑️ Removing entire AICO directory: {data_dir}")
                console.print(f"📊 [dim]Contains: {total_files} files, {total_dirs} directories[/dim]")
                
                try:
                    # Remove the entire AICO directory
                    shutil.rmtree(data_dir)
                    console.print("✅ [green]AICO directory completely removed[/green]")
                    files_deleted += total_files
                    dirs_deleted += total_dirs
                    
                    # Clean up parent directory if it's now empty
                    parent_dir = data_dir.parent  # boeni-industries
                    try:
                        if parent_dir.exists() and not any(parent_dir.iterdir()):
                            console.print(f"🗑️ Removing empty parent directory: {parent_dir}")
                            parent_dir.rmdir()
                            console.print("✅ [green]Empty parent directory removed[/green]")
                    except Exception as e:
                        console.print(f"⚠️ [yellow]Could not remove parent directory: {e}[/yellow]")
                        
                except Exception as e:
                    console.print(f"❌ [red]Could not remove AICO directory: {e}[/red]")
                    
            else:
                console.print("📁 [dim]AICO directory does not exist[/dim]")
            
            console.print(f"✅ [green]Application directory removal complete[/green]")
        
        # Wipe config
        if config:
            console.print("⚙️ [yellow]Removing configuration files...[/yellow]")
            config_files_deleted = 0
            data_dir = AICOPaths.get_data_directory()
            
            if data_dir.exists():
                for item in data_dir.rglob("*"):
                    try:
                        if item.is_file() and item.suffix in ['.yaml', '.yml', '.json']:
                            console.print(f"🗑️ Deleting config: {item.name}")
                            item.unlink()
                            config_files_deleted += 1
                    except Exception as e:
                        console.print(f"⚠️ [yellow]Could not delete {item}: {e}[/yellow]")
            
            console.print(f"✅ [green]Configuration files removed ({config_files_deleted} files)[/green]")
        
        # Success summary
        console.print("\n🎉 [bold green]Wipe operation completed successfully![/bold green]")
        
        if security:
            console.print("🔄 [yellow]Re-setup the system:[/yellow]")
            console.print("  1. Run 'aico security setup' to create new master password")
            if data:
                console.print("  2. Run 'aico db init' to create new encrypted databases")
            if config:
                console.print("  3. Run 'aico config init' to initialize configuration files")
            elif not data:  # Only security was wiped, but config might still be needed
                console.print("  2. Run 'aico config init' to verify configuration files")
        
    except Exception as e:
        console.print(f"❌ [red]Wipe operation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command(help="Compile Protocol Buffer files to Python code")
def protoc(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show command that would be executed without running it")
):
    """🔧 Compile Protocol Buffer files to Python code.
    
    Uses the proper protoc command from the documentation to generate Python
    bindings for all .proto files in the /proto directory.
    
    Examples:
      aico dev protoc              # Compile all proto files
      aico dev protoc --verbose    # Show detailed output
      aico dev protoc --dry-run    # Preview command without executing
    """
    
    # Get project root (where we should run the command from)
    project_root = Path.cwd()
    
    # Verify we're in the right directory
    proto_dir = project_root / "proto"
    if not proto_dir.exists():
        console.print("❌ [red]Proto directory not found. Run this command from the AICO project root.[/red]")
        raise typer.Exit(1)
    
    # Verify output directory exists
    output_dir = project_root / "shared" / "aico" / "proto"
    if not output_dir.exists():
        console.print("❌ [red]Output directory not found: shared/aico/proto[/red]")
        raise typer.Exit(1)
    
    # Find venv site-packages directory for protobuf includes
    venv_site_packages = None
    possible_venv_paths = [
        project_root / ".venv" / "Lib" / "site-packages",  # Windows
        project_root / ".venv" / "lib" / "python3.11" / "site-packages",  # Linux/macOS
        project_root / ".venv" / "lib" / "python3.12" / "site-packages",  # Linux/macOS
        project_root / ".venv" / "lib" / "python3.13" / "site-packages",  # Linux/macOS
    ]
    
    for path in possible_venv_paths:
        if path.exists() and (path / "google" / "protobuf").exists():
            venv_site_packages = path
            break
    
    if not venv_site_packages:
        console.print("❌ [red]Could not find venv site-packages with protobuf. Ensure your venv is activated and protobuf is installed.[/red]")
        raise typer.Exit(1)
    
    # Build the protoc command from documentation
    proto_files = [
        "proto/aico_core_api_gateway.proto",
        "proto/aico_core_common.proto", 
        "proto/aico_core_envelope.proto",
        "proto/aico_core_logging.proto",
        "proto/aico_core_plugin_system.proto",
        "proto/aico_core_update_system.proto",
        "proto/aico_emotion.proto",
        "proto/aico_integration.proto",
        "proto/aico_personality.proto",
        "proto/aico_conversation.proto"
    ]
    
    cmd = [
        "protoc",
        f"-I=proto",
        f"-I={venv_site_packages}",
        "--python_out=shared/aico/proto"
    ] + proto_files
    
    if dry_run:
        console.print("🔍 [cyan]DRY RUN - Would execute:[/cyan]")
        console.print(f"Working directory: {project_root}")
        console.print(f"Command: {' '.join(cmd)}")
        return
    
    console.print("🔧 [yellow]Compiling Protocol Buffer files...[/yellow]")
    if verbose:
        console.print(f"Working directory: {project_root}")
        console.print(f"Command: {' '.join(cmd)}")
        console.print(f"Include paths:")
        console.print(f"  - proto/")
        console.print(f"  - {venv_site_packages}")
        console.print(f"Output directory: shared/aico/proto")
    
    try:
        # Run protoc command
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        
        if verbose and result.stdout:
            console.print("📤 [dim]stdout:[/dim]")
            console.print(result.stdout)
        
        if result.stderr:
            console.print("⚠️ [yellow]stderr:[/yellow]")
            console.print(result.stderr)
        
        # Count generated files
        generated_files = list(output_dir.glob("*_pb2.py"))
        
        # Post-process generated files to fix relative imports
        console.print("🔧 [yellow]Post-processing imports...[/yellow]")
        for pb_file in generated_files:
            content = pb_file.read_text(encoding='utf-8')
            # Fix imports like "import aico_core_common_pb2" to "from . import aico_core_common_pb2"
            import re
            new_content = re.sub(
                r'^import (aico_\w+_pb2) as (\w+)$',
                r'from . import \1 as \2',
                content,
                flags=re.MULTILINE
            )
            if new_content != content:
                pb_file.write_text(new_content, encoding='utf-8')
                if verbose:
                    console.print(f"  • Fixed imports in {pb_file.name}")
        
        console.print(f"✅ [green]Protocol Buffer compilation successful![/green]")
        console.print(f"📁 Generated {len(generated_files)} Python files in shared/aico/proto/")
        
        if verbose:
            for file in generated_files:
                console.print(f"  • {file.name}")
        
    except subprocess.CalledProcessError as e:
        console.print(f"❌ [red]protoc compilation failed with exit code {e.returncode}[/red]")
        if e.stdout:
            console.print("📤 [dim]stdout:[/dim]")
            console.print(e.stdout)
        if e.stderr:
            console.print("📤 [dim]stderr:[/dim]")
            console.print(e.stderr)
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("❌ [red]protoc command not found. Please install Protocol Buffers compiler.[/red]")
        console.print("💡 [dim]Install instructions:[/dim]")
        console.print("  Windows: choco install protoc")
        console.print("  macOS: brew install protobuf")
        console.print("  Ubuntu/Debian: sudo apt-get install protobuf-compiler")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
