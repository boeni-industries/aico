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
from utils.path_display import format_smart_path, create_path_table, display_full_paths_section, display_platform_info, get_status_indicator

app = typer.Typer()
# Standard Rich console - encoding is fixed at app startup
console = Console()




@app.command()
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


@app.command()
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


@app.command()
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


@app.command()
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


@app.command()
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


@app.command()
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


@app.command()
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


@app.command()
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


@app.command("paths")
def show_paths():
    """Show platform-specific configuration and data directories."""
    
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
