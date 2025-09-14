"""
CLI utility functions for managing the LMDB database.

This module acts as a wrapper around the shared `aico.data.lmdb` module,
providing user-facing console output for CLI commands.
"""

import lmdb
from rich.console import Console

# Import shared logic
from typing import Optional
from aico.core.config import ConfigurationManager
from aico.data.lmdb import get_lmdb_path, initialize_lmdb_env
from rich.table import Table

console = Console()

def initialize_lmdb_cli(config: Optional[ConfigurationManager] = None, verbose: bool = True) -> None:
    """Idempotently initialize the LMDB database with CLI feedback."""
    db_path = get_lmdb_path(config)
    try:
        # The shared function is idempotent, but we check existence here to control output
        if db_path.exists():
            if verbose:
                console.print(f"[blue]INFO[/blue] - LMDB working memory database already exists at [cyan]{db_path}[/cyan]")
            # Still call initialize to ensure named dbs are created
            initialize_lmdb_env(config)
            return

        initialize_lmdb_env(config)
        if verbose:
            console.print(f"✅ [green]Successfully initialized LMDB working memory database at[/green] [cyan]{db_path}[/cyan]")

    except Exception as e:
        console.print(f"❌ [red]Failed to initialize LMDB database: {e}[/red]")
        raise

def list_named_databases(config: Optional[ConfigurationManager] = None) -> list[str]:
    """Return a list of configured named databases."""
    if config is None:
        config = ConfigurationManager()
        config.initialize(lightweight=True)
    return config.get("core.memory.working.named_databases", [])

def get_lmdb_status_cli(config: Optional[ConfigurationManager] = None) -> dict:
    """Get the status of the LMDB database for CLI display."""
    if config is None:
        config = ConfigurationManager()
        config.initialize(lightweight=True)

    db_path = get_lmdb_path(config)
    status = {
        "path": str(db_path),
        "exists": db_path.exists(),
        "size_mb": None,
        "db_stats": {},
    }

    if not db_path.exists():
        return status

    try:
        named_dbs = list_named_databases(config)
        env = lmdb.open(str(db_path), readonly=True, max_dbs=len(named_dbs) + 1)
        db_stats = {}

        with env.begin() as txn:
            # Main DB
            main_db = env.open_db(None, txn=txn)
            db_stats["(main)"] = txn.stat(main_db)["entries"]
            # Named DBs
            for db_name in named_dbs:
                sub_db = env.open_db(db_name.encode('utf-8'), txn=txn)
                db_stats[db_name] = txn.stat(sub_db)["entries"]
        
        status["db_stats"] = db_stats
        status["size_mb"] = round(db_path.stat().st_size / (1024 * 1024), 2)
        env.close()

    except Exception as e:
        status["error"] = str(e)


    return status

def dump_lmdb_db(db_name: str, limit: int, config: Optional[ConfigurationManager] = None) -> Table:
    """Dump key-value pairs from a specific named database."""
    db_path = get_lmdb_path(config)
    if not db_path.exists():
        raise FileNotFoundError(f"LMDB database not found at {db_path}")

    table = Table(
        title=f"✨ [bold cyan]Dump of '{db_name}' Database (First {limit} keys)[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1)
    )
    table.add_column("Key", style="cyan", justify="left")
    table.add_column("Value", style="white", justify="left")

    if config is None:
        config = ConfigurationManager()
        config.initialize(lightweight=True)
    named_dbs = list_named_databases(config)
    env = lmdb.open(str(db_path), readonly=True, max_dbs=len(named_dbs) + 1)
    db_key = db_name.encode('utf-8') if db_name != "(main)" else None
    
    with env.begin() as txn:
        sub_db = env.open_db(db_key, txn=txn)
        cursor = txn.cursor(sub_db)
        count = 0
        for key, value in cursor:
            if count >= limit:
                break
            try:
                key_str = key.decode('utf-8')
            except UnicodeDecodeError:
                key_str = repr(key)
            try:
                value_str = value.decode('utf-8')
            except UnicodeDecodeError:
                value_str = repr(value)
            
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."

            table.add_row(key_str, value_str)
            count += 1
    env.close()
    return table

def clear_lmdb_cli(config: Optional[ConfigurationManager] = None) -> None:
    """Clear and re-initialize the LMDB database with CLI feedback."""
    db_path = get_lmdb_path(config)
    try:
        if db_path.exists():
            # This is a directory, so we need to remove it recursively
            import shutil
            shutil.rmtree(db_path)
            console.print(f"🗑️ [yellow]Cleared existing LMDB database at[/yellow] [cyan]{db_path}[/cyan]")
        
        initialize_lmdb_env(config)
        console.print("✅ [green]Successfully re-initialized empty LMDB database.[/green]")

    except Exception as e:
        console.print(f"❌ [red]Failed to clear LMDB database: {e}[/red]")
        raise
