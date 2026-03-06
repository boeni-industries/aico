"""CLI commands for vLLM deployment and management.

Provides zero-effort vLLM deployment with platform-specific optimizations.
"""

import sys
import subprocess
import platform
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add shared module to path
if getattr(sys, 'frozen', False):
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from cli.utils.formatting import format_error, format_success, format_info, format_warning

console = Console()
app = typer.Typer(help="🚀 vLLM deployment and management")


def _detect_gpu() -> tuple[bool, str, dict]:
    """Detect GPU availability and capabilities.
    
    Returns:
        Tuple of (has_gpu, gpu_type, gpu_info)
        gpu_type: 'nvidia', 'metal', or 'none'
        gpu_info: Dict with GPU details
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "Apple" in result.stdout:
                # Get GPU core count
                gpu_result = subprocess.run(
                    ["system_profiler", "SPDisplaysDataType"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                cores = 0
                for line in gpu_result.stdout.split('\n'):
                    if "Total Number of Cores:" in line:
                        cores = int(line.split(':')[1].strip())
                        break
                
                return True, "metal", {
                    "type": "Apple Silicon",
                    "cores": cores,
                    "unified_memory": True
                }
        except Exception:
            pass
        return False, "none", {}
    
    elif system in ["Linux", "Windows"]:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                gpus = []
                for line in lines:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        gpus.append({
                            "name": parts[0].strip(),
                            "memory": parts[1].strip()
                        })
                
                return True, "nvidia", {
                    "type": "NVIDIA",
                    "gpus": gpus,
                    "count": len(gpus)
                }
        except Exception:
            pass
        return False, "none", {}
    
    return False, "none", {}


def _get_optimal_vllm_args(character: str, has_gpu: bool, gpu_type: str, gpu_info: dict) -> list[str]:
    """Generate optimal vLLM arguments for current platform.
    
    Args:
        character: Character name (e.g., 'eve')
        has_gpu: Whether GPU is available
        gpu_type: Type of GPU ('nvidia', 'metal', 'none')
        gpu_info: GPU information dict
        
    Returns:
        List of vLLM command arguments
    """
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    
    # Load character configuration
    character_config = config.get(f"characters.{character}", {})
    if not character_config:
        raise ValueError(f"Character '{character}' not found in configuration")
    
    base_model = character_config.get("base_model", "")
    if not base_model:
        raise ValueError(f"Character '{character}' missing base_model")
    
    # Load vLLM configuration
    vllm_config = config.get("llm.vllm", {})
    server_config = vllm_config.get("server", {})
    
    # Base arguments
    args = [
        "vllm", "serve", base_model,
        "--host", vllm_config.get("host", "0.0.0.0"),
        "--port", str(vllm_config.get("port", 8774)),
    ]
    
    # Platform-specific optimizations
    if has_gpu and gpu_type == "nvidia":
        # NVIDIA GPU optimizations
        gpu_mem = server_config.get("gpu_memory_utilization", 0.9)
        max_seqs = server_config.get("max_num_seqs", 16)
        max_len = server_config.get("max_model_len", 8192)
        
        args.extend([
            "--gpu-memory-utilization", str(gpu_mem),
            "--max-num-seqs", str(max_seqs),
            "--max-model-len", str(max_len),
        ])
        
        # Multi-GPU support
        gpu_count = gpu_info.get("count", 1)
        if gpu_count > 1:
            tensor_parallel = min(gpu_count, server_config.get("tensor_parallel_size", 1))
            args.extend(["--tensor-parallel-size", str(tensor_parallel)])
        
        # Enable optimizations
        if server_config.get("enable_chunked_prefill", True):
            args.append("--enable-chunked-prefill")
    
    elif has_gpu and gpu_type == "metal":
        # macOS Metal - vLLM doesn't support Metal, use CPU
        console.print(format_warning(
            "⚠️  vLLM doesn't support Metal GPU on macOS.\n"
            "Running in CPU mode. For GPU acceleration on Mac, use Ollama instead."
        ))
        args.extend([
            "--device", "cpu",
            "--max-num-seqs", "4",  # Lower for CPU
            "--max-model-len", "8192",
        ])
    
    else:
        # CPU-only mode
        args.extend([
            "--device", "cpu",
            "--max-num-seqs", "4",
            "--max-model-len", "8192",
        ])
    
    return args


def _deploy_macos_daemon(model_name: str, character: str, detach: bool):
    """Deploy vLLM as native daemon on macOS with Metal GPU acceleration."""
    console.print("[bold cyan]🍎 macOS Deployment Strategy[/bold cyan]")
    console.print("[dim]Using vLLM Metal plugin for Apple Silicon GPU acceleration (MLX backend)[/dim]\n")
    
    # Check if vllm-metal is installed
    console.print("[dim]→ Checking vLLM Metal installation...[/dim]")
    vllm_metal_venv = Path.home() / ".venv-vllm-metal"
    
    if not vllm_metal_venv.exists():
        console.print("[yellow]⚠️  vLLM Metal not installed[/yellow]")
        console.print("[bold cyan]Installing vLLM Metal plugin (this may take 5-10 minutes)...[/bold cyan]")
        console.print("[dim]This creates a dedicated virtual environment with GPU-optimized vLLM[/dim]\n")
        
        try:
            # Run the official vllm-metal installer
            result = subprocess.run(
                ["curl", "-fsSL", "https://raw.githubusercontent.com/vllm-project/vllm-metal/main/install.sh"],
                capture_output=True,
                text=True,
                check=True
            )
            subprocess.run(
                ["bash", "-c", result.stdout],
                check=True,
                env={**subprocess.os.environ, "VLLM_METAL_INSTALL_QUIET": "0"}
            )
            console.print("[green]✓ vLLM Metal installed successfully[/green]\n")
        except subprocess.CalledProcessError as e:
            console.print(format_error(f"Failed to install vLLM Metal: {e}"))
            console.print("[yellow]Falling back to CPU-only vLLM...[/yellow]\n")
            # Fall back to regular vLLM
            try:
                subprocess.run(["pip", "install", "vllm"], check=True)
            except Exception as fallback_error:
                console.print(format_error(f"Fallback installation also failed: {fallback_error}"))
                raise typer.Exit(1)
    else:
        console.print("[green]✓ vLLM Metal already installed[/green]\n")
    
    # Build command using vllm-metal venv if available
    vllm_python = str(vllm_metal_venv / "bin" / "python") if vllm_metal_venv.exists() else "python"
    
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    vllm_config = config.get("llm.vllm", {})
    server_config = (vllm_config or {}).get("server", {}) if isinstance(vllm_config, dict) else {}

    max_model_len = int(server_config.get("max_model_len", 8192) or 8192)
    # With chunked prefill, max_num_batched_tokens is the main tuning knob.
    # Use a safe default >= max_model_len.
    max_num_batched_tokens = int(server_config.get("max_num_batched_tokens", max(16384, max_model_len)) or max(16384, max_model_len))
    if max_num_batched_tokens < max_model_len:
        max_num_batched_tokens = max_model_len

    cmd = [
        vllm_python, "-m", "vllm.entrypoints.openai.api_server",
        "--model", model_name,
        "--host", "0.0.0.0",
        "--port", "8774",
        "--max-model-len", str(max_model_len),
        "--max-num-batched-tokens", str(max_num_batched_tokens),  # Must be >= max-model-len
        "--enable-chunked-prefill",
        "--reasoning-parser", "qwen3",
        "--default-chat-template-kwargs", '{"enable_thinking": true}',
        # Note: vLLM Metal plugin auto-detects and uses Apple Silicon GPU (MLX backend)
    ]
    
    console.print("[bold]Starting vLLM server...[/bold]")
    console.print(f"[dim]Command: {' '.join(cmd)}[/dim]\n")
    
    if detach:
        # Run as background daemon
        console.print("[cyan]→ Starting as background daemon[/cyan]")
        with open("/tmp/vllm.log", "w") as log_file:
            run_env = os.environ.copy()
            # Support gated Hugging Face models.
            # vLLM/huggingface_hub will look for HF_TOKEN and/or HUGGING_FACE_HUB_TOKEN.
            # We do not load/store secrets here; we only pass through what the user provided.
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=run_env,
            )
        
        # Save PID for later management
        pid_file = Path.home() / ".aico" / "vllm.pid"
        pid_file.parent.mkdir(exist_ok=True)
        pid_file.write_text(str(process.pid))
        
        console.print(f"[green]✓ vLLM daemon started (PID: {process.pid})[/green]")
        console.print(f"[dim]Logs: /tmp/vllm.log[/dim]")
        console.print(f"[dim]API: http://localhost:8774[/dim]\n")
        console.print("[yellow]Note: First request will be slow (model loading)[/yellow]\n")
    else:
        # Run in foreground
        console.print("[cyan]→ Starting in foreground (Ctrl+C to stop)[/cyan]\n")
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            console.print("\n[yellow]vLLM stopped[/yellow]")


def _deploy_docker(model_name: str, character: str, detach: bool):
    """Deploy vLLM as Docker container (Linux/Windows) with latest version."""
    system = platform.system()
    console.print(f"[bold cyan]🐳 Docker Deployment ({system})[/bold cyan]")
    console.print("[dim]Using latest vLLM Docker image with GPU support[/dim]\n")
    
    # Check if Docker is available
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            console.print(format_error("Docker not found. Please install Docker first."))
            raise typer.Exit(1)
        console.print(f"[dim]✓ {result.stdout.strip()}[/dim]\n")
    except Exception as e:
        console.print(format_error(f"Docker not available: {e}"))
        raise typer.Exit(1)
    
    # Check if container already exists
    container_name = "aico-vllm"
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if container_name in result.stdout:
            console.print(f"[yellow]⚠️  Container '{container_name}' already exists[/yellow]")
            console.print("[dim]Stopping and removing old container...[/dim]")
            subprocess.run(["docker", "stop", container_name], capture_output=True)
            subprocess.run(["docker", "rm", container_name], capture_output=True)
            console.print("[green]✓ Old container removed[/green]\n")
    except Exception as e:
        console.print(format_warning(f"Could not check existing container: {e}"))
    
    # Use latest vLLM version for reasoning/thinking support
    vllm_image = "vllm/vllm-openai:latest"
    console.print(f"[dim]→ Using vLLM image: {vllm_image}[/dim]")
    
    # Build Docker command
    docker_cmd = [
        "docker", "run",
        "--name", container_name,
        "-p", "8774:8000",  # Map internal 8000 to external 8774
        "-v", f"{Path.home()}/.cache/huggingface:/root/.cache/huggingface",
        "--shm-size", "4g",  # Increase shared memory for better performance
    ]

    # Pass through Hugging Face tokens for gated model access.
    # If unset, these env vars are simply not added.
    hf_token = os.environ.get("HF_TOKEN")
    hub_token = os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if hf_token:
        docker_cmd.extend(["-e", "HF_TOKEN"])
    if hub_token:
        docker_cmd.extend(["-e", "HUGGING_FACE_HUB_TOKEN"])
    
    # Add GPU support if available
    if system == "Linux":
        docker_cmd.extend(["--gpus", "all"])
        console.print("[dim]→ NVIDIA GPU support enabled (--gpus all)[/dim]")
        console.print("[dim]→ Optimized for CUDA with tensor parallelism support[/dim]")
    elif system == "Windows":
        # Windows with WSL2 + NVIDIA GPU
        docker_cmd.extend(["--gpus", "all"])
        console.print("[dim]→ GPU support enabled (requires WSL2 + NVIDIA drivers)[/dim]")
    
    if detach:
        docker_cmd.append("-d")
    
    docker_cmd.extend([
        vllm_image,
        "--model", model_name,
        "--host", "0.0.0.0",
        "--port", "8000",  # Internal port
        "--gpu-memory-utilization", "0.9",
        "--max-num-seqs", "32",  # Increased for better throughput
        "--max-model-len", "8192",
        "--max-num-batched-tokens", "16384",  # Must be >= max-model-len for chunked prefill
        "--enable-chunked-prefill",  # Better latency for long prompts
        "--reasoning-parser", "qwen3",  # Enable Qwen3 reasoning extraction
        "--default-chat-template-kwargs", '{"enable_thinking": true}',  # Enable thinking mode by default
        "--tensor-parallel-size", "1",  # Can be increased for multi-GPU
    ])
    
    console.print("[bold]Starting vLLM Docker container...[/bold]")
    console.print(f"[dim]Command: {' '.join(docker_cmd[:8])}...[/dim]\n")
    
    try:
        if detach:
            console.print("[cyan]→ Starting as detached container[/cyan]")
            result = subprocess.run(docker_cmd, capture_output=True, text=True, check=True)
            container_id = result.stdout.strip()[:12]
            console.print(f"[green]✓ vLLM container started ({container_id})[/green]")
            console.print(f"[dim]Container: {container_name}[/dim]")
            console.print(f"[dim]API: http://localhost:8774[/dim]")
            console.print(f"[dim]Logs: docker logs -f {container_name}[/dim]\n")
            console.print("[yellow]Note: First request will be slow (model downloading + loading)[/yellow]\n")
        else:
            console.print("[cyan]→ Starting in foreground (Ctrl+C to stop)[/cyan]\n")
            subprocess.run(docker_cmd)
    except subprocess.CalledProcessError as e:
        console.print(format_error(f"Failed to start Docker container: {e}"))
        if e.stderr:
            console.print(f"[dim]{e.stderr}[/dim]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping container...[/yellow]")
        subprocess.run(["docker", "stop", container_name], capture_output=True)


@app.command("deploy")
def deploy(
    character: str = typer.Option("eve", "--character", "-c", help="Character model to deploy"),
    force: bool = typer.Option(False, "--force", "-f", help="Force restart if already running"),
    detach: bool = typer.Option(True, "--detach/--foreground", help="Run in background (daemon/Docker)")
):
    """Deploy vLLM server with platform-aware configuration.
    
    - Linux: Docker container (GPU support)
    - macOS: Native daemon (CPU/Metal)
    - Windows: Docker container (GPU support)
    """
    console.print("\n🚀 [bold cyan]vLLM Deployment[/bold cyan]\n")
    
    # Detect platform
    system = platform.system()
    console.print(f"[dim]→ Detected platform: {system}[/dim]")
    
    # Load character configuration
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        
        # Get characters config.
        # Supported shapes:
        # 1) {"eve": {...}, "joi": {...}}
        # 2) {"characters": {"eve": {...}, "joi": {...}}}
        characters_data = config_manager.get("characters", {})
        if isinstance(characters_data, dict) and "characters" in characters_data and isinstance(characters_data["characters"], dict):
            characters = characters_data["characters"]
        else:
            characters = characters_data if isinstance(characters_data, dict) else {}
        
        character_config = characters.get(character)
        if not character_config:
            console.print(format_error(f"Character '{character}' not found in configuration"))
            raise typer.Exit(1)
        
        model_name = character_config.get("base_model")
        if not model_name:
            console.print(format_error(f"No base_model defined for character '{character}'"))
            raise typer.Exit(1)
        
        console.print(f"[dim]→ Character: {character}[/dim]")
        console.print(f"[dim]→ Model: {model_name}[/dim]\n")
        
    except Exception as e:
        console.print(format_error(f"Failed to load configuration: {e}"))
        raise typer.Exit(1)
    
    # Check if already running
    if not force:
        try:
            import httpx
            response = httpx.get("http://localhost:8774/health", timeout=2.0)
            if response.status_code == 200:
                console.print("[yellow]⚠️  vLLM server already running[/yellow]")
                console.print("[dim]Use --force to restart[/dim]\n")
                return
        except:
            pass  # Not running, proceed with deployment
    
    # Platform-specific deployment
    if system == "Darwin":  # macOS
        _deploy_macos_daemon(model_name, character, detach)
    elif system == "Linux":
        _deploy_docker(model_name, character, detach)
    elif system == "Windows":
        _deploy_docker(model_name, character, detach)
    else:
        console.print(format_error(f"Unsupported platform: {system}"))
        raise typer.Exit(1)


@app.command("stop")
def stop():
    """Stop vLLM server (daemon or Docker container)."""
    console.print("\n🛑 [bold cyan]Stopping vLLM Server[/bold cyan]\n")
    
    system = platform.system()
    stopped = False
    
    try:
        if system == "Darwin":
            # macOS: Stop native daemon
            console.print("[dim]Platform: macOS (checking native daemon)[/dim]")
            
            # Check PID file
            pid_file = Path.home() / ".aico" / "vllm.pid"
            if pid_file.exists():
                pid = pid_file.read_text().strip()
                console.print(f"[dim]→ Found PID file: {pid}[/dim]")
                try:
                    subprocess.run(["kill", pid], timeout=5, check=True)
                    pid_file.unlink()
                    console.print(format_success(f"✅ vLLM daemon stopped (PID: {pid})"))
                    stopped = True
                except subprocess.CalledProcessError:
                    console.print(format_warning(f"⚠️  Process {pid} not found (already stopped?)"))
                    pid_file.unlink()
            else:
                # Fallback: search for process
                result = subprocess.run(
                    ["pgrep", "-f", "vllm.entrypoints.openai.api_server"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            subprocess.run(["kill", pid], timeout=5)
                    console.print(format_success(f"✅ vLLM daemon stopped ({len(pids)} process(es))"))
                    stopped = True
        
        else:
            # Linux/Windows: Stop Docker container
            console.print(f"[dim]Platform: {system} (checking Docker)[/dim]")
            container_name = "aico-vllm"
            
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if container_name in result.stdout:
                console.print(f"[dim]→ Stopping container '{container_name}'...[/dim]")
                subprocess.run(["docker", "stop", container_name], timeout=30, check=True)
                subprocess.run(["docker", "rm", container_name], timeout=10, check=True)
                console.print(format_success(f"✅ vLLM container stopped and removed"))
                stopped = True
        
        if not stopped:
            console.print(format_warning("⚠️  No running vLLM server found"))
    
    except Exception as e:
        console.print(format_error(f"Failed to stop vLLM: {e}"))
    
    console.print()


@app.command("status")
def status():
    """Check vLLM server status."""
    console.print("\n📊 [bold cyan]vLLM Server Status[/bold cyan]\n")
    
    # Try to detect deployment method
    system = platform.system()
    if system == "Darwin":
        console.print("[dim]Platform: macOS (native daemon)[/dim]")
    else:
        console.print(f"[dim]Platform: {system} (Docker)[/dim]")
    
    try:
        import httpx
        
        # Check if server is running
        try:
            response = httpx.get("http://localhost:8774/v1/models", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                
                console.print("[green]✓ vLLM server is running[/green]")
                console.print(f"[dim]  Endpoint: http://localhost:8774[/dim]")
                console.print(f"[dim]  Models loaded: {len(models)}[/dim]")
                
                if models:
                    console.print("\n[bold]Loaded Models:[/bold]")
                    for model in models:
                        console.print(f"  • {model.get('id', 'unknown')}")
            else:
                console.print("[yellow]⚠️  vLLM server responded with error[/yellow]")
        
        except Exception:
            console.print("[red]✗ vLLM server not responding[/red]")
            console.print("[dim]  Start with: aico deploy vllm[/dim]")
    
    except ImportError:
        console.print(format_error("httpx not installed. Install with: pip install httpx"))
    
    console.print()
