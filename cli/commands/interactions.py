"""
AICO CLI Interaction Commands

Provides commands for testing and simulating interaction requests.
"""

import typer
import json
import asyncio
import websockets
from rich.console import Console
from rich.table import Table
from rich import box
from rich.text import Text
from typing import Optional, Any
from datetime import datetime

from cli.utils.api_client import get_backend_client
from cli.decorators.sensitive import sensitive

console = Console()

app = typer.Typer(
    help="Interaction request testing and simulation",
    invoke_without_command=True,
    context_settings={"help_option_names": []},
)


def interactions_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("simulate", "Simulate an interaction request for testing"),
            ("reply", "Reply to an interaction (answer/approve/reject/cancel)"),
            ("list", "List interaction requests"),
            ("ls", "Alias for list (bash-style)"),
            ("get", "Get interaction request details"),
        ]
        
        examples = [
            "aico interactions simulate question --user <uuid> --prompt 'Test question?'",
            "aico interactions reply <id> --answer 'My answer'",
            "aico interactions reply <id> --approve",
            "aico interactions list --user <uuid>",
            "aico interactions ls --user <uuid>",
        ]
        
        format_subcommand_help(
            console=console,
            command_name="interactions",
            description="Interaction request testing and simulation",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()


app.callback(invoke_without_command=True)(interactions_callback)


async def _listen_websocket(user_id: str, admin: bool = False, timeout: int = 10):
    """
    Connect to API Gateway WebSocket and listen for interaction notifications.
    
    Returns the first received notification or None if timeout.
    """
    from aico.core.config import ConfigurationManager
    from aico.security.key_manager import AICOKeyManager
    
    # Get WebSocket configuration
    config_manager = ConfigurationManager()
    config_manager.initialize()
    gateway_config = config_manager.get("api_gateway", {})
    ws_config = gateway_config.get("websocket", {})
    host = ws_config.get("host", "127.0.0.1")
    port = ws_config.get("port", 8772)
    
    # Get JWT token
    key_manager = AICOKeyManager(config_manager)
    jwt_token = key_manager.get_jwt_token("api_gateway")
    if not jwt_token:
        console.print("[red]✗ No JWT token found. Run 'aico gateway auth login' first.[/red]")
        return None
    
    ws_url = f"ws://{host}:{port}/ws"
    
    console.print(f"[dim]Connecting to WebSocket: {ws_url}[/dim]")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            # First, receive welcome message
            welcome_response = await asyncio.wait_for(websocket.recv(), timeout=5)
            welcome_data = json.loads(welcome_response)
            
            if welcome_data.get("type") != "welcome":
                console.print(f"[red]✗ Unexpected initial message: {welcome_data}[/red]")
                return None
            
            # Now authenticate
            auth_message = {
                "type": "auth",
                "token": jwt_token
            }
            await websocket.send(json.dumps(auth_message))
            
            # Wait for auth response
            auth_response = await asyncio.wait_for(websocket.recv(), timeout=5)
            auth_data = json.loads(auth_response)
            
            if auth_data.get("type") != "auth_success":
                console.print(f"[red]✗ WebSocket authentication failed: {auth_data}[/red]")
                return None
            
            console.print("[green]✓ WebSocket authenticated[/green]")
            
            # Subscribe to topic
            topic = "interaction.notifications.admin" if admin else f"interaction.notifications.{user_id}"
            subscribe_message = {
                "type": "subscribe",
                "topic": topic
            }
            await websocket.send(json.dumps(subscribe_message))
            
            console.print(f"[dim]Subscribed to: {topic}[/dim]")
            console.print(f"[yellow]Waiting for notification (timeout: {timeout}s)...[/yellow]")
            
            # Wait for broadcast (loop through messages until we get a broadcast or timeout)
            start_time = asyncio.get_event_loop().time()
            try:
                while True:
                    remaining = timeout - (asyncio.get_event_loop().time() - start_time)
                    if remaining <= 0:
                        console.print(f"[yellow]⚠ No notification received within {timeout}s[/yellow]")
                        return None
                    
                    message = await asyncio.wait_for(websocket.recv(), timeout=remaining)
                    data = json.loads(message)
                    
                    if data.get("type") == "broadcast":
                        console.print("[green]✓ Received notification![/green]")
                        return data
                    # Ignore non-broadcast messages (subscribed, heartbeat, etc.) and keep waiting
            
            except asyncio.TimeoutError:
                console.print(f"[yellow]⚠ No notification received within {timeout}s[/yellow]")
                return None
    
    except Exception as e:
        console.print(f"[red]✗ WebSocket error: {e}[/red]")
        return None


@app.command("simulate")
@sensitive
def simulate_interaction(
    interaction_type: str = typer.Argument(..., help="question | choice | dialogue | approval"),
    user_id: str = typer.Option(..., "--user", "-u", help="Target user UUID"),
    prompt: str = typer.Option(..., "--prompt", "-p", help="Interaction prompt/question text"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Interaction title"),
    requirement: str = typer.Option("required", "--requirement", "-r", help="required | optional"),
    severity: str = typer.Option("medium", "--severity", "-s", help="low | medium | high"),
    category: str = typer.Option("general", "--category", "-c", help="Interaction category"),
    expected_answer_type: Optional[str] = typer.Option(None, "--answer-type", "-a", help="text | yes_no | number | date | choice"),
    allowed_options: Optional[str] = typer.Option(None, "--options", "-o", help="Comma-separated allowed options (for choice type)"),
    expires_in: Optional[int] = typer.Option(None, "--expires", "-e", help="Expiration time in seconds"),
    scenario: Optional[str] = typer.Option(None, "--scenario", help="create_only | create_then_answer | create_then_cancel"),
    answer_text: Optional[str] = typer.Option(None, "--answer", help="Answer text for scenario resolution"),
    broadcast_admin: bool = typer.Option(False, "--broadcast-admin", help="Also publish to admin topic"),
    listen_ws: bool = typer.Option(False, "--listen-ws", "-w", help="Listen for WebSocket notification"),
    ws_timeout: int = typer.Option(10, "--ws-timeout", help="WebSocket listen timeout in seconds"),
    format_output: str = typer.Option("table", "--format", "-f", help="Output format: table | json"),
):
    """
    Simulate an interaction request for end-to-end testing.
    
    This creates a real interaction_request in the database and publishes
    to the message bus, allowing you to test the full pipeline including
    WebSocket delivery to clients.
    """
    
    # Build request payload
    payload = {
        "user_id": user_id,
        "interaction_type": interaction_type,
        "requirement": requirement,
        "severity": severity,
        "category": category,
        "prompt": prompt,
        "broadcast_admin": broadcast_admin,
    }
    
    if title:
        payload["title"] = title
    if expected_answer_type:
        payload["expected_answer_type"] = expected_answer_type
    if allowed_options:
        payload["allowed_options"] = [opt.strip() for opt in allowed_options.split(",")]
    if expires_in:
        payload["expires_in_seconds"] = expires_in
    if scenario:
        payload["scenario"] = scenario
    if answer_text:
        payload["answer_text"] = answer_text
    
    # Start WebSocket listener if requested
    ws_future = None
    if listen_ws:
        import concurrent.futures
        import threading
        
        # Run WebSocket listener in a separate thread with its own event loop
        def run_listener():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_listen_websocket(user_id, admin=broadcast_admin, timeout=ws_timeout))
            finally:
                loop.close()
        
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        ws_future = executor.submit(run_listener)
        
        # Give WebSocket time to connect and authenticate
        import time
        time.sleep(2)  # Allow connection to establish before triggering simulator
    
    # Call backend API
    try:
        with get_backend_client() as client:
            response = client.post("/api/v1/admin/interactions/simulate", json=payload)
        
        if format_output == "json":
            console.print(json.dumps(response, indent=2))
        else:
            # Display interaction details
            interaction = response.get("interaction", {})
            event = response.get("event", {})
            
            console.print("\n[bold green]✓ Interaction simulated successfully[/bold green]\n")
            
            table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("Interaction ID", interaction.get("interaction_id", ""))
            table.add_row("User ID", interaction.get("user_id", ""))
            table.add_row("Correlation ID", interaction.get("correlation_id", ""))
            table.add_row("Type", interaction.get("interaction_type", ""))
            table.add_row("Status", interaction.get("status", ""))
            table.add_row("Requirement", interaction.get("requirement", ""))
            table.add_row("Severity", interaction.get("severity", ""))
            table.add_row("Prompt", interaction.get("prompt", ""))
            
            if interaction.get("title"):
                table.add_row("Title", interaction["title"])
            if interaction.get("expected_answer_type"):
                table.add_row("Answer Type", interaction["expected_answer_type"])
            if interaction.get("expires_at"):
                table.add_row("Expires At", interaction["expires_at"])
            
            console.print(table)
            
            if response.get("scenario_executed"):
                console.print(f"\n[yellow]Scenario executed: {response['scenario_executed']}[/yellow]")
                
                if response.get("additional_events"):
                    console.print(f"[dim]Additional events: {len(response['additional_events'])}[/dim]")
        
        # Wait for WebSocket notification if listener is active
        if ws_future:
            console.print("\n[bold cyan]WebSocket Listener[/bold cyan]")
            ws_result = ws_future.result(timeout=ws_timeout + 5)
            
            if ws_result:
                broadcast_data = ws_result.get("data", {})
                console.print("\n[green]✓ End-to-end test successful![/green]")
                console.print(f"[dim]Topic: {ws_result.get('topic')}[/dim]")
                console.print(f"[dim]Broadcast type: {broadcast_data.get('type')}[/dim]")
                
                if format_output == "json":
                    console.print("\n[bold]WebSocket Payload:[/bold]")
                    console.print(json.dumps(ws_result, indent=2))
            else:
                console.print("[yellow]⚠ Interaction created but WebSocket notification not received[/yellow]")
                console.print("[dim]Check that API Gateway WebSocket adapter is running[/dim]")
    
    except Exception as e:
        console.print(f"[red]✗ Failed to simulate interaction: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
@app.command("ls")
@sensitive
def list_interactions(
    user_id: Optional[str] = typer.Option(None, "--user", "-u", help="Filter by user UUID"),
    status: Optional[list[str]] = typer.Option(None, "--status", "-s", help="Filter by status", show_default=False),
    interaction_type: Optional[list[str]] = typer.Option(None, "--type", "-t", help="Filter by type", show_default=False),
    category: Optional[list[str]] = typer.Option(None, "--category", "-c", help="Filter by category", show_default=False),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of results"),
    format_output: str = typer.Option("table", "--format", "-f", help="Output format: table | json"),
):
    """List interaction requests."""
    
    params: list[tuple[str, str]] = [("limit", str(limit))]
    if user_id:
        params.append(("user_id", user_id))
    if status:
        for s in status:
            params.append(("status", s))
    if interaction_type:
        for t in interaction_type:
            params.append(("interaction_type", t))
    if category:
        for c in category:
            params.append(("category", c))
    
    try:
        with get_backend_client() as client:
            response = client.get("/api/v1/interactions", params=params)
        
        items = response.get("items", [])
        
        if not items:
            console.print("[yellow]No interactions found[/yellow]")
            return
        
        if format_output == "json":
            console.print(json.dumps(response, indent=2))
        else:
            console.print()
            console.print(f"[bold yellow]Interaction Requests ({len(items)} found)[/bold yellow]")
            console.print()

            for idx, item in enumerate(items, start=1):
                interaction_id = item.get("interaction_id", "")
                user_id_value = item.get("user_id", "")
                created_at = item.get("created_at", "") if item.get("created_at") else ""

                header = f"[bold]{idx}.[/bold] [cyan]{interaction_id}[/cyan]"
                console.print(header)

                def _kv(label: str, value: str) -> Text:
                    t = Text("  ")
                    t.append(f"{label}: ", style="dim")
                    t.append(value or "")
                    return t

                lines = [
                    _kv("User", user_id_value),
                    _kv("Type", item.get("interaction_type", "")),
                    _kv("Status", item.get("status", "")),
                    _kv("Requirement", item.get("requirement", "")),
                    _kv("Severity", item.get("severity", "")),
                    _kv("Category", item.get("category", "")),
                    _kv("Prompt", item.get("prompt", "")),
                    _kv("Created", created_at),
                ]

                for line in lines:
                    console.print(line, soft_wrap=True)
                console.print()

    except Exception as e:
        console.print(f"[red]✗ Failed to list interactions: {e}[/red]")
        raise typer.Exit(1)


@app.command("reply")
@sensitive
def reply_interaction(
    interaction_id: str = typer.Argument(..., help="Interaction ID"),
    answer: Optional[str] = typer.Option(None, "--answer", "-a", help="Answer text (for question/choice types)"),
    answer_json: Optional[str] = typer.Option(None, "--answer-json", help="Answer JSON (for structured answers)"),
    approve: bool = typer.Option(False, "--approve", help="Approve the interaction (approval type only)"),
    reject: bool = typer.Option(False, "--reject", help="Reject the interaction (approval type only)"),
    cancel: bool = typer.Option(False, "--cancel", help="Cancel the interaction"),
    reason: Optional[str] = typer.Option(None, "--reason", "-r", help="Reason for reject/cancel"),
    listen_ws: bool = typer.Option(False, "--listen-ws", "-w", help="Listen for WebSocket notification"),
    ws_timeout: int = typer.Option(10, "--ws-timeout", help="WebSocket listen timeout in seconds"),
    format_output: str = typer.Option("table", "--format", "-f", help="Output format: table | json"),
):
    """
    Reply to an interaction request (answer/approve/reject/cancel).
    
    This simulates a user responding to an interaction, allowing you to test
    the full state transition flow including WebSocket notifications.
    """
    
    # Validate mutually exclusive actions
    actions = sum([bool(answer or answer_json), approve, reject, cancel])
    if actions == 0:
        console.print("[red]✗ Must specify one action: --answer, --approve, --reject, or --cancel[/red]")
        raise typer.Exit(1)
    if actions > 1:
        console.print("[red]✗ Only one action allowed at a time[/red]")
        raise typer.Exit(1)
    
    # First, get the interaction to determine user_id for WebSocket
    user_id = None
    if listen_ws:
        try:
            with get_backend_client() as client:
                detail_response = client.get(f"/api/v1/interactions/{interaction_id}")
                user_id = detail_response.get("interaction", {}).get("user_id")
        except Exception as e:
            console.print(f"[yellow]⚠ Could not fetch interaction for WebSocket listener: {e}[/yellow]")
    
    # Start WebSocket listener if requested
    ws_task = None
    loop = None
    if listen_ws and user_id:
        async def listen_task():
            return await _listen_websocket(user_id, admin=False, timeout=ws_timeout)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ws_task = loop.create_task(listen_task())
        
        # Give WebSocket time to connect
        import time
        time.sleep(1)
    
    # Determine endpoint and payload
    endpoint = None
    payload = {}
    
    if answer or answer_json:
        endpoint = f"/api/v1/interactions/{interaction_id}/answer"
        if answer:
            payload["answer_text"] = answer
        if answer_json:
            try:
                payload["answer_json"] = json.loads(answer_json)
            except json.JSONDecodeError:
                console.print("[red]✗ Invalid JSON in --answer-json[/red]")
                raise typer.Exit(1)
    
    elif approve:
        endpoint = f"/api/v1/interactions/{interaction_id}/approve"
    
    elif reject:
        endpoint = f"/api/v1/interactions/{interaction_id}/reject"
        if reason:
            endpoint += f"?reason={reason}"
    
    elif cancel:
        endpoint = f"/api/v1/interactions/{interaction_id}/cancel"
        if reason:
            endpoint += f"?reason={reason}"
    
    # Call backend API
    try:
        with get_backend_client() as client:
            response = client.post(endpoint, json=payload if payload else None)
        
        if format_output == "json":
            console.print(json.dumps(response, indent=2))
        else:
            interaction = response.get("interaction", {})
            event = response.get("event", {})
            
            console.print("\n[bold green]✓ Reply recorded successfully[/bold green]\n")
            
            table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("Interaction ID", interaction.get("interaction_id", ""))
            table.add_row("Status", interaction.get("status", ""))
            table.add_row("Event Type", event.get("event_type", ""))
            table.add_row("Actor", event.get("actor", ""))
            
            if interaction.get("answer_text"):
                table.add_row("Answer", interaction["answer_text"])
            
            console.print(table)
        
        # Wait for WebSocket notification if listener is active
        if ws_task and loop:
            console.print("\n[bold cyan]WebSocket Listener[/bold cyan]")
            ws_result = loop.run_until_complete(ws_task)
            
            if ws_result:
                broadcast_data = ws_result.get("data", {})
                console.print("\n[green]✓ End-to-end reply test successful![/green]")
                console.print(f"[dim]Topic: {ws_result.get('topic')}[/dim]")
                console.print(f"[dim]Event type: {broadcast_data.get('event', {}).get('event_type')}[/dim]")
                
                if format_output == "json":
                    console.print("\n[bold]WebSocket Payload:[/bold]")
                    console.print(json.dumps(ws_result, indent=2))
            else:
                console.print("[yellow]⚠ Reply recorded but WebSocket notification not received[/yellow]")
            
            loop.close()
    
    except Exception as e:
        console.print(f"[red]✗ Failed to reply to interaction: {e}[/red]")
        if loop:
            loop.close()
        raise typer.Exit(1)


@app.command("get")
@sensitive
def get_interaction(
    interaction_id: str = typer.Argument(..., help="Interaction ID"),
    format_output: str = typer.Option("table", "--format", "-f", help="Output format: table | json"),
):
    """Get interaction request details including event timeline."""
    
    try:
        with get_backend_client() as client:
            response = client.get(f"/api/v1/interactions/{interaction_id}")
        
        if format_output == "json":
            console.print(json.dumps(response, indent=2))
        else:
            interaction = response.get("interaction", {})
            events = response.get("events", [])
            
            console.print("\n[bold cyan]Interaction Details[/bold cyan]\n")
            
            table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("Interaction ID", interaction.get("interaction_id", ""))
            table.add_row("User ID", interaction.get("user_id", ""))
            table.add_row("Correlation ID", interaction.get("correlation_id", ""))
            table.add_row("Type", interaction.get("interaction_type", ""))
            table.add_row("Status", interaction.get("status", ""))
            table.add_row("Requirement", interaction.get("requirement", ""))
            table.add_row("Severity", interaction.get("severity", ""))
            table.add_row("Category", interaction.get("category", ""))
            
            if interaction.get("title"):
                table.add_row("Title", interaction["title"])
            
            table.add_row("Prompt", interaction.get("prompt", ""))
            
            if interaction.get("answer_text"):
                table.add_row("Answer", interaction["answer_text"])
            
            table.add_row("Created", interaction.get("created_at", ""))
            table.add_row("Updated", interaction.get("updated_at", ""))
            
            console.print(table)
            
            if events:
                console.print(f"\n[bold cyan]Event Timeline ({len(events)} events)[/bold cyan]\n")
                
                event_table = Table(box=box.SIMPLE_HEAD, header_style="bold yellow")
                event_table.add_column("Event ID", style="cyan", no_wrap=True, max_width=12)
                event_table.add_column("Type", style="green")
                event_table.add_column("Actor", style="magenta")
                event_table.add_column("Transition", style="bright_blue")
                event_table.add_column("Created", style="dim")
                
                for event in events:
                    transition = ""
                    if event.get("from_status") and event.get("to_status"):
                        transition = f"{event['from_status']} → {event['to_status']}"
                    elif event.get("to_status"):
                        transition = f"→ {event['to_status']}"
                    
                    event_table.add_row(
                        event.get("event_id", "")[:12],
                        event.get("event_type", ""),
                        event.get("actor", ""),
                        transition,
                        event.get("created_at", "")[:19] if event.get("created_at") else "",
                    )
                
                console.print(event_table)
            
            console.print()
    
    except Exception as e:
        console.print(f"[red]✗ Failed to get interaction: {e}[/red]")
        raise typer.Exit(1)
