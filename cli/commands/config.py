"""
AICO CLI Configuration Commands

Provides configuration management commands for viewing, setting, and validating
configuration across all AICO subsystems.
"""

import typer
from rich.table import Table
from rich import box
from pathlib import Path
import sys
import os
import yaml
import json

# Import decorators
import sys
from pathlib import Path
decorators_path = Path(__file__).parent.parent / "decorators"
sys.path.insert(0, str(decorators_path))
from cli.decorators.sensitive import sensitive

# Standard Rich console - encoding is fixed at app startup
from rich.console import Console

# Add shared module to path for CLI usage
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager, ConfigurationError, ConfigurationValidationError
from aico.core.paths import AICOPaths

# Import shared utilities using the same pattern as other CLI modules
from cli.utils.path_display import format_smart_path, create_path_table, display_full_paths_section, display_platform_info, get_status_indicator

def config_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("get", "Get configuration value using dot notation"),
            ("set", "Set configuration value using dot notation"),
            ("list", "List configuration values"),
            ("validate", "Validate configuration against schemas"),
            ("export", "Export configuration to file"),
            ("import", "Import configuration from file"),
            ("reload", "Reload configuration from files"),
            ("domains", "List available configuration domains"),
            ("schema", "Show schema for a configuration domain"),
            ("show", "Show configuration paths, platform info, and system settings"),
            ("init", "Initialize AICO configuration directories and setup")
        ]
        
        examples = [
            "aico config list",
            "aico config get api_gateway.protocols.rest.port",
            "aico config set api_gateway.protocols.rest.port 8771",
            "aico config show",
            "aico config domains"
        ]
        
        format_subcommand_help(
            console=console,
            command_name="config",
            description="Configuration management and validation",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()

app = typer.Typer(
    help="Configuration management and validation.",
    callback=config_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)
# Standard Rich console - encoding is fixed at app startup
console = Console()




@app.command(help="Get configuration value using dot notation")
def get(key: str):
    """Get configuration value using dot notation."""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize()
        value = config_manager.get(key)
        
        if value is not None:
            console.print(f"[cyan]{key}[/cyan]: [green]{value}[/green]")
        else:
            console.print(f"[red]Configuration key '{key}' not found[/red]")
            raise typer.Exit(1)
            
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)


@app.command(help="Set configuration value using dot notation")
def set(
    key: str,
    value: str,
    persist: bool = typer.Option(True, "--no-persist", help="Don't persist change to storage")
):
    """Set configuration value using dot notation."""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize()
        
        # Try to parse as JSON for complex values
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            parsed_value = value
            
        config_manager.set(key, parsed_value, persist=persist)
        
        persist_text = " (persisted)" if persist else " (runtime only)"
        console.print(f"[green]✓[/green] Set [cyan]{key}[/cyan] = [yellow]{parsed_value}[/yellow]{persist_text}")
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)


@app.command(help="List configuration values")
def list(
    domain: str = typer.Option(None, "--domain", "-d", help="Configuration domain to list"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, yaml, json")
):
    """List configuration values."""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize()
        
        if domain:
            config = config_manager.get(domain, {})
            title = f"Configuration: {domain}"
        else:
            config = config_manager.config_cache
            title = "All Configuration"
            
        if format == "yaml":
            console.print(yaml.dump(config, default_flow_style=False))
        elif format == "json":
            console.print(json.dumps(config, indent=2))
        else:
            # Table format (default)
            table = Table(title=f"✨ {title}", box=box.SIMPLE_HEAD)
            table.add_column("Key", style="cyan", no_wrap=True)
            table.add_column("Value", style="green")
            
            def add_rows(data, prefix=""):
                for key, value in data.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, dict):
                        add_rows(value, full_key)
                    else:
                        # Truncate long values for table display
                        str_value = str(value)
                        if len(str_value) > 50:
                            str_value = str_value[:47] + "..."
                        table.add_row(full_key, str_value)
                        
            add_rows(config)
            console.print(table)
            
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)


@app.command(help="Validate configuration against schemas")
def validate(domain: str = typer.Option(None, "--domain", "-d", help="Domain to validate")):
    """Validate configuration against schemas."""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize()
        
        if domain:
            domains = [domain]
        else:
            domains = config_manager.get_domains()
            
        table = Table(title="✨ Configuration Validation", box=box.SIMPLE_HEAD)
        table.add_column("Domain", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details", style="dim")
        
        all_valid = True
        
        for d in domains:
            try:
                config = config_manager.get(d, {})
                is_valid = config_manager.validate(d, config)
                
                if is_valid:
                    table.add_row(d, "[green]✓ Valid[/green]", "Schema validation passed")
                else:
                    table.add_row(d, "[red]✗ Invalid[/red]", "Schema validation failed")
                    all_valid = False
                    
            except ConfigurationValidationError as e:
                table.add_row(d, "[red]✗ Invalid[/red]", str(e))
                all_valid = False
            except ConfigurationError as e:
                table.add_row(d, "[yellow]⚠ Warning[/yellow]", f"No schema found: {e}")
                
        console.print(table)
        
        if not all_valid:
            raise typer.Exit(1)
            
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
@sensitive("exports potentially sensitive configuration data to external files")
def export(
    file: str,
    domains: str = typer.Option(None, "--domains", "-d", help="Comma-separated list of domains to export"),
    format: str = typer.Option("yaml", "--format", "-f", help="Export format: yaml, json")
):
    """Export configuration to file."""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize()
        
        domain_list = domains.split(',') if domains else None
        config = config_manager.export_config(domain_list)
        
        output_path = Path(file)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            if format == "json":
                json.dump(config, f, indent=2)
            else:
                yaml.dump(config, f, default_flow_style=False)
                
        console.print(f"[green]✓[/green] Configuration exported to [cyan]{file}[/cyan]")
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)
    except IOError as e:
        console.print(f"[red]File error: {e}[/red]")
        raise typer.Exit(1)


@app.command(help="Import configuration from file")
def import_config(
    file: str,
    validate: bool = typer.Option(True, "--no-validate", help="Skip validation during import")
):
    """Import configuration from file."""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize()
        
        input_path = Path(file)
        
        if not input_path.exists():
            console.print(f"[red]File not found: {file}[/red]")
            raise typer.Exit(1)
            
        with open(input_path, 'r', encoding='utf-8') as f:
            if file.endswith('.json'):
                config = json.load(f)
            else:
                config = yaml.safe_load(f)
                
        config_manager.import_config(config, validate=validate)
        
        validation_text = " (with validation)" if validate else " (without validation)"
        console.print(f"[green]✓[/green] Configuration imported from [cyan]{file}[/cyan]{validation_text}")
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)
    except (IOError, json.JSONDecodeError, yaml.YAMLError) as e:
        console.print(f"[red]File error: {e}[/red]")
        raise typer.Exit(1)


@app.command(help="Reload configuration from files")
def reload():
    """Reload configuration from files."""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize()
        config_manager.reload()
        
        console.print("[green]✓[/green] Configuration reloaded from files")
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)


@app.command(help="List available configuration domains")
def domains():
    """List available configuration domains."""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize()
        
        available_domains = config_manager.get_domains()
        
        table = Table(title="✨ Available Configuration Domains", box=box.SIMPLE_HEAD)
        table.add_column("Domain", style="cyan")
        table.add_column("Schema", style="green")
        
        for domain in sorted(available_domains):
            schema_path = config_manager.config_dir / "schemas" / f"{domain}.schema.json"
            schema_status = "✓ Available" if schema_path.exists() else "✗ Missing"
            table.add_row(domain, schema_status)
            
        console.print(table)
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)


@app.command(help="Show schema for a configuration domain")
def schema(domain: str):
    """Show schema for a configuration domain."""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize()
        
        schema = config_manager.get_schema(domain)
        
        console.print(f"[cyan]Schema for domain: {domain}[/cyan]")
        console.print(json.dumps(schema, indent=2))
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)


@app.command("show")
def show():
    """Show configuration paths, platform info, and system settings."""
    
    # Get platform info
    platform_info = AICOPaths.get_platform_info()
    
    # Create table using shared utility
    table = create_path_table("Platform Configuration Paths", [
        ("Directory Type", "cyan", True),
        ("Smart Path", "green", False),
        ("Status", "white", True)
    ])
    
    # Add directory paths - fix data directory to show actual data subdirectory
    data_dir = AICOPaths.get_data_directory() / "data"  # Add the data subdirectory
    directories = [
        ("Data Directory", str(data_dir)),
        ("Config Directory", platform_info["config_directory"]), 
        ("Cache Directory", platform_info["cache_directory"]),
        ("Logs Directory", platform_info["logs_directory"])
    ]
    
    for dir_type, dir_path in directories:
        path_obj = Path(dir_path)
        status = get_status_indicator(path_obj)
        smart_path = format_smart_path(path_obj)
        table.add_row(dir_type, smart_path, status)
    
    console.print(table)
    
    # Show full paths using shared utility
    display_full_paths_section(console, directories)
    
    # Show platform info using shared utility
    display_platform_info(console, platform_info)


@app.command("init")
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Force initialization, overwriting existing files")
):
    """Initialize AICO configuration directories and setup."""
    
    from cli.utils.platform import get_platform_chars
    import shutil
    chars = get_platform_chars()
    
    console.print(f"{chars['sparkle']} [bold cyan]Initializing AICO Configuration[/bold cyan]\n")
    
    try:
        config_dir = AICOPaths.get_config_directory()
        
        # Find source config templates in project
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle - config should be bundled
            project_config_dir = Path(sys._MEIPASS) / "config"
        else:
            # Running in development
            project_config_dir = Path(__file__).parent.parent.parent / "config"
        
        # Define configuration files to create
        config_files_to_create = [
            ("environments/development.yaml", project_config_dir / "environments" / "development.yaml"),
            ("environments/production.yaml", project_config_dir / "environments" / "production.yaml"),
            ("defaults/core.yaml", project_config_dir / "defaults" / "core.yaml"),
            ("defaults/security.yaml", project_config_dir / "defaults" / "security.yaml"),
            ("defaults/database.yaml", project_config_dir / "defaults" / "database.yaml"),
        ]
        
        # Check existing configurations for informational purposes
        existing_configs = []
        missing_configs = []
        
        for rel_path, source_file in config_files_to_create:
            target_file = config_dir / rel_path
            if target_file.exists():
                existing_configs.append(target_file)
            else:
                missing_configs.append((rel_path, source_file))
        
        # Show status of existing configurations
        if existing_configs:
            console.print(f"{chars['check']} [green]Found existing configuration files:[/green]")
            for config_file in existing_configs:
                console.print(f"  {chars['bullet']} {format_smart_path(config_file)}")
            if not force:
                console.print(f"  [dim]Use --force to overwrite existing files[/dim]")
            console.print()
        
        # Determine which files to actually create/update
        files_to_process = config_files_to_create if force else missing_configs
        
        # Initialize all platform directories including new frontend paths
        base_data_dir = AICOPaths.get_data_directory()
        directories = [
            ("Data Directory", base_data_dir / "data"),
            ("Config Directory", config_dir),
            ("Cache Directory", AICOPaths.get_cache_directory()),
            ("Logs Directory", AICOPaths.get_logs_directory()),
            ("Frontend State Directory", base_data_dir / "frontend" / "state"),
            ("Frontend Cache Directory", AICOPaths.get_cache_directory() / "frontend"),
            ("Frontend Offline Queue", base_data_dir / "frontend" / "offline_queue")
        ]
        
        # Create directories and track what was actually created
        dirs_created = 0
        dirs_existed = 0
        for dir_name, dir_path in directories:
            if dir_path.exists():
                dirs_existed += 1
            else:
                AICOPaths.ensure_directory(dir_path)
                console.print(f"{chars['check']} [green]Created {dir_name}[/green]: {format_smart_path(dir_path)}")
                dirs_created += 1
        
        # Copy actual configuration files from templates
        files_created = 0
        files_skipped = 0
        for rel_path, source_file in files_to_process:
            target_file = config_dir / rel_path
            
            if source_file.exists():
                # Ensure target directory exists
                target_file.parent.mkdir(parents=True, exist_ok=True)
                # Copy the file
                shutil.copy2(source_file, target_file)
                console.print(f"{chars['check']} [green]Created config file[/green]: {format_smart_path(target_file)}")
                files_created += 1
            else:
                console.print(f"{chars['cross']} [yellow]Template not found[/yellow]: {source_file}")
        
        # Show summary with delta information
        if dirs_created > 0 or files_created > 0 or len(existing_configs) > 0:
            console.print(f"\n{chars['sparkle']} [bold green]AICO configuration initialized successfully![/bold green]")
            
            # Show what was actually created (delta only)
            if dirs_created > 0:
                console.print(f"{chars['check']} [green]Created {dirs_created} new directories[/green]")
            if files_created > 0:
                console.print(f"{chars['check']} [green]Created {files_created} configuration files[/green]")
                
            # Show what already existed (if relevant)
            if existing_configs and not force:
                console.print(f"{chars['check']} [green]Preserved {len(existing_configs)} existing configuration files[/green]")
            if dirs_existed > 0 and dirs_created == 0:
                console.print(f"{chars['check']} [dim]All directories already existed[/dim]")
                
        else:
            console.print(f"\n{chars['cross']} [yellow]No configuration templates found to copy[/yellow]")
            
        console.print(f"\n{chars['bullet']} [cyan]Next steps:[/cyan]")
        console.print(f"   {chars['bullet']} Run [bold]aico db init[/bold] to create encrypted database")
        console.print(f"   {chars['bullet']} Run [bold]aico config show[/bold] to verify setup")
        
    except Exception as e:
        console.print(f"{chars['cross']} [red]Failed to initialize configuration: {e}[/red]")
        raise typer.Exit(1)
