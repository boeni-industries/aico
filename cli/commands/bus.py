import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text
from pathlib import Path
import sys
import asyncio
import json
from datetime import datetime
from typing import Optional

# Import decorators
decorators_path = Path(__file__).parent.parent / "decorators"
sys.path.insert(0, str(decorators_path))
from cli.decorators.sensitive import sensitive, destructive

def bus_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("test", "Test message bus connection and basic pub/sub functionality"),
            ("monitor", "Monitor real-time message traffic"),
            ("stats", "Show message bus statistics from database"),
            ("clear", "Clear the message log")
        ]
        
        examples = [
            "aico bus test",
            "aico bus monitor",
            "aico bus stats",
            "aico bus clear"
        ]
        
        format_subcommand_help(
            console=console,
            command_name="bus",
            description="Message bus testing, monitoring, and management",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()

app = typer.Typer(
    help="Message bus testing, monitoring, and management.",
    callback=bus_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)
console = Console()

# Add shared module to path for CLI usage
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.core.bus import MessageBusClient, MessageBusBroker, create_client
from aico.security.key_manager import AICOKeyManager
from aico.core.paths import AICOPaths
from cli.utils.pg_connection import get_pg_connection
# Required protobuf imports - fail loudly if not available
from aico.proto import aico_core_logging_pb2
from aico.proto.aico_core_envelope_pb2 import AicoMessage
from google.protobuf.timestamp_pb2 import Timestamp
from cli.decorators.sensitive import sensitive

def _get_database_connection(force_fresh: bool = False):
    """Helper function to get PostgreSQL database connection."""
    try:
        return get_pg_connection()
    except Exception as e:
        console.print(f"[red]Error connecting to database: {e}[/red]")
        raise typer.Exit(1)


@app.command("test")
def test_connection(
    broker_address: str = typer.Option("tcp://localhost:5555", "--broker", "-b", help="Broker address"),
    client_id: str = typer.Option("cli_test", "--client", "-c", help="Client ID"),
    message_count: int = typer.Option(5, "--count", "-n", help="Number of test messages")
):
    """Test message bus connection and basic pub/sub functionality"""
    
    # Initialize logging for bus operations
    try:
        from aico.core.logging import initialize_logging
        initialize_logging(service_name="cli", enable_influx=True, enable_console=True)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not initialize logging: {e}[/yellow]")
    
    async def run_test():
        console.print(f"[cyan]Testing Message Bus Connection[/cyan]")
        console.print(f"[dim]Broker: {broker_address}[/dim]")
        console.print(f"[dim]Client: {client_id}[/dim]")
        console.print()
        
        try:
            # Create test client
            client = await create_client(client_id, broker_address)
            console.print("[green]✓[/green] Connected to message bus")
            
            # Set up message counter
            received_messages = []
            
            async def test_callback(message):
                received_messages.append(message)
                console.print(f"[green]✓[/green] Received: {message.metadata.message_type}")
            
            # Subscribe to test topic - use exact pattern that matches sent messages
            await client.subscribe("test/message/*", test_callback)
            console.print("[green]✓[/green] Subscribed to test/message/* topics")
            
            # Small delay to ensure subscription is active
            console.print("[dim]Waiting for subscription to activate...[/dim]")
            await asyncio.sleep(1.0)  # Longer delay to ensure subscription is ready
            
            # Send test messages
            console.print(f"\n[yellow]Sending {message_count} test messages...[/yellow]")
            for i in range(message_count):
                # Create a proper protobuf message for testing
                test_log = LogEntry()
                test_log.subsystem = "test"
                test_log.module = "bus_test"
                test_log.function = "test_connection"
                test_log.level = LogLevel.INFO
                test_log.message = f"Test message {i}"
                test_log.topic = f"test.message_{i}"
                
                # Set timestamp
                timestamp = Timestamp()
                timestamp.GetCurrentTime()
                test_log.timestamp.CopyFrom(timestamp)
                
                await client.publish(
                    f"test/message/{i}",
                    test_log
                )
                console.print(f"[cyan]→[/cyan] Sent test/message/{i}")
                await asyncio.sleep(0.1)  # Small delay
            
            # Wait for messages to be received
            console.print("[dim]Waiting for messages to be received...[/dim]")
            await asyncio.sleep(2)  # Longer wait time
            
            # Results
            console.print(f"\n[cyan]Test Results:[/cyan]")
            console.print(f"[green]✓[/green] Sent: {message_count} messages")
            console.print(f"[green]✓[/green] Received: {len(received_messages)} messages")
            
            # Debug info
            if len(received_messages) == 0:
                console.print(f"[yellow]Debug: Client running: {client.running}[/yellow]")
                console.print(f"[yellow]Debug: Subscriptions: {list(client.subscriptions.keys())}[/yellow]")
            
            if len(received_messages) == message_count:
                console.print("[green]✓ All messages received successfully![/green]")
            else:
                console.print(f"[yellow]⚠ Only {len(received_messages)}/{message_count} messages received[/yellow]")
            
            await client.disconnect()
            
        except Exception as e:
            console.print(f"[red]✗ Test failed: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(run_test())


@app.command("monitor")
def monitor_traffic(
    broker_address: str = typer.Option("tcp://localhost:5555", "--broker", "-b", help="Broker address"),
    client_id: str = typer.Option("cli_monitor", "--client", "-c", help="Client ID"),
    topics: str = typer.Option("*", "--topics", "-t", help="Topics to monitor (comma-separated)"),
    max_messages: int = typer.Option(100, "--max", "-m", help="Maximum messages to display")
):
    """Monitor real-time message traffic"""
    
    # Initialize logging for bus operations
    try:
        from aico.core.logging import initialize_logging
        initialize_logging(service_name="cli", enable_influx=True, enable_console=True)
        
    except Exception as e:
        console.print(f"[red]✗ Failed to initialize logging: {e}[/red]")
        sys.exit(1)
    
    async def run_monitor():
        console.print(f"[cyan]Monitoring Message Bus Traffic[/cyan]")
        console.print(f"[dim]Broker: {broker_address}[/dim]")
        console.print(f"[dim]Topics: {topics}[/dim]")
        console.print()
        
        message_count = 0
        
        try:
            # Create monitor client
            client = await create_client(client_id, broker_address)
            console.print("[green]✓[/green] Connected to message bus")
            
            async def monitor_callback(message):
                nonlocal message_count
                message_count += 1
                timestamp = datetime.now().strftime("%H:%M:%S")
                console.print(f"[dim]{timestamp}[/dim] [yellow]{message.metadata.topic}[/yellow] from [cyan]{message.metadata.source}[/cyan]")
            
            # Subscribe to topics
            topic_list = [t.strip() for t in topics.split(",")]
            for topic in topic_list:
                await client.subscribe(topic, monitor_callback)
                console.print(f"[green]✓[/green] Monitoring: {topic}")
            
            console.print("\n[cyan]Message Traffic:[/cyan]")
            
            # Keep monitoring until interrupted
            try:
                while message_count < max_messages:
                    await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                console.print(f"\n[yellow]Stopped monitoring. Received {message_count} messages.[/yellow]")
            
            await client.disconnect()
            
        except Exception as e:
            console.print(f"[red]✗ Monitor failed: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(run_monitor())


@app.command("stats")
def show_stats(
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path (auto-detect if not provided)")
):
    """Show message bus statistics from database"""
    
    console.print(f"[cyan]Message Bus Statistics[/cyan]")
    
    try:
        # Connect to database using established pattern
        conn = _get_database_connection()
        
        # Query statistics
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_messages,
                COUNT(DISTINCT topic) as unique_topics,
                COUNT(DISTINCT source) as unique_sources,
                MIN(timestamp) as earliest_message,
                MAX(timestamp) as latest_message
            FROM system_events
        """)
        
        row = cursor.fetchone()
        
        if not row or row[0] == 0:
            console.print("[yellow]No messages found in database[/yellow]")
            return
        
        # Display statistics table
        table = Table(title="Message Bus Statistics", box=box.SIMPLE_HEAD)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="white")
        
        table.add_row("Total Messages", f"{row[0]:,}")
        table.add_row("Unique Topics", str(row[1]))
        table.add_row("Unique Sources", str(row[2]))
        table.add_row("Earliest Message", row[3] or "N/A")
        table.add_row("Latest Message", row[4] or "N/A")
        
        console.print(table)
        
        # Top topics
        cursor = conn.execute("""
            SELECT topic, COUNT(*) as count
            FROM system_events 
            GROUP BY topic 
            ORDER BY count DESC 
            LIMIT 10
        """)
        
        topic_rows = cursor.fetchall()
        
        if topic_rows:
            console.print("\n[cyan]Top Topics:[/cyan]")
            topic_table = Table(box=box.SIMPLE_HEAD)
            topic_table.add_column("Topic", style="yellow")
            topic_table.add_column("Messages", style="white", justify="right")
            
            for topic, count in topic_rows:
                topic_table.add_row(topic, f"{count:,}")
            
            console.print(topic_table)
        
        conn.close()
        
    except Exception as e:
        console.print(f"[red]✗ Failed to get statistics: {e}[/red]")
        sys.exit(1)


@app.command("clear")
@sensitive
def clear_messages(
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
):
    """Clear all messages from the message log"""
    
    if not confirm:
        confirmed = typer.confirm("This will delete all message log entries. Continue?")
        if not confirmed:
            console.print("[yellow]Operation cancelled[/yellow]")
            return
    
    try:
        # Connect to database using established pattern
        conn = _get_database_connection()
        
        # Clear messages
        conn.execute("DELETE FROM system_events")
        conn.commit()
        
        console.print("[green]✓ Message log cleared[/green]")
        
        conn.close()
        
    except Exception as e:
        console.print(f"[red]✗ Failed to clear messages: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    app()
