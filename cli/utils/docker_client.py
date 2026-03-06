"""
Docker Client Utilities for AICO CLI

Provides Docker container detection, status checking, and management utilities
for the Docker-first AICO architecture.
"""

import subprocess
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class ContainerStatus(Enum):
    """Docker container status"""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    EXITED = "exited"
    DEAD = "dead"
    CREATED = "created"
    UNKNOWN = "unknown"


@dataclass
class ContainerInfo:
    """Container information"""
    name: str
    container_id: str
    image: str
    status: ContainerStatus
    state: str
    created: str
    ports: List[str]
    labels: Dict[str, str]


class DockerClient:
    """Lightweight Docker client using docker CLI"""
    
    AICO_SERVICES = {
        "gateway": "aico-gateway",
        "core": "aico-core",
        "modelservice": "aico-modelservice",
        "nats": "aico-nats",
        "postgres": "aico-postgres",
        "influxdb": "aico-influxdb",
        "loki": "aico-loki",
        "grafana": "aico-grafana"
    }
    
    @staticmethod
    def is_docker_available() -> bool:
        """Check if Docker is installed and accessible"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    @staticmethod
    def is_docker_running() -> bool:
        """Check if Docker daemon is running"""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    @staticmethod
    def get_container_status(container_name: str) -> Optional[ContainerInfo]:
        """Get status of a specific container by name"""
        try:
            result = subprocess.run(
                [
                    "docker", "inspect",
                    "--format", "{{json .}}",
                    container_name
                ],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return None
            
            data = json.loads(result.stdout)
            
            # Parse container info
            state = data.get("State", {})
            config = data.get("Config", {})
            network_settings = data.get("NetworkSettings", {})
            
            # Determine status
            if state.get("Running"):
                status = ContainerStatus.RUNNING
            elif state.get("Paused"):
                status = ContainerStatus.PAUSED
            elif state.get("Restarting"):
                status = ContainerStatus.RESTARTING
            elif state.get("Dead"):
                status = ContainerStatus.DEAD
            elif state.get("Status") == "created":
                status = ContainerStatus.CREATED
            elif state.get("Status") == "exited":
                status = ContainerStatus.EXITED
            else:
                status = ContainerStatus.UNKNOWN
            
            # Parse ports
            ports = []
            port_bindings = network_settings.get("Ports", {})
            for container_port, host_bindings in port_bindings.items():
                if host_bindings:
                    for binding in host_bindings:
                        host_port = binding.get("HostPort")
                        if host_port:
                            ports.append(f"{host_port}:{container_port}")
            
            return ContainerInfo(
                name=data.get("Name", "").lstrip("/"),
                container_id=data.get("Id", "")[:12],
                image=config.get("Image", ""),
                status=status,
                state=state.get("Status", "unknown"),
                created=data.get("Created", ""),
                ports=ports,
                labels=config.get("Labels", {})
            )
            
        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
            return None
    
    @staticmethod
    def list_aico_containers() -> List[ContainerInfo]:
        """List all AICO-related containers"""
        containers = []
        
        try:
            # Use docker ps with filter for aico project
            result = subprocess.run(
                [
                    "docker", "ps", "-a",
                    "--filter", "label=com.aico.project=aico",
                    "--format", "{{.Names}}"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                container_names = result.stdout.strip().split("\n")
                for name in container_names:
                    if name:
                        info = DockerClient.get_container_status(name)
                        if info:
                            containers.append(info)
            
        except subprocess.TimeoutExpired:
            pass
        
        return containers
    
    @staticmethod
    def is_service_running(service_name: str) -> bool:
        """Check if a specific AICO service is running"""
        container_name = DockerClient.AICO_SERVICES.get(service_name)
        if not container_name:
            return False
        
        info = DockerClient.get_container_status(container_name)
        return info is not None and info.status == ContainerStatus.RUNNING
    
    @staticmethod
    def get_container_logs(container_name: str, lines: int = 100, follow: bool = False) -> Optional[str]:
        """Get logs from a container"""
        try:
            cmd = ["docker", "logs"]
            if follow:
                cmd.append("-f")
            cmd.extend(["--tail", str(lines), container_name])
            
            if follow:
                # For follow mode, use Popen to stream
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                return process
            else:
                # For non-follow, get all logs at once
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return result.stdout if result.returncode == 0 else None
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
    
    @staticmethod
    def exec_in_container(container_name: str, command: List[str], interactive: bool = False) -> Optional[int]:
        """Execute a command in a container"""
        try:
            cmd = ["docker", "exec"]
            if interactive:
                cmd.extend(["-it"])
            cmd.append(container_name)
            cmd.extend(command)
            
            result = subprocess.run(cmd)
            return result.returncode
            
        except (FileNotFoundError, KeyboardInterrupt):
            return None
    
    @staticmethod
    def get_compose_status() -> Dict[str, Any]:
        """Get Docker Compose project status"""
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd="/Users/mbo/Documents/dev/aico/docker"
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse JSON output (one JSON object per line)
                services = []
                for line in result.stdout.strip().split("\n"):
                    if line:
                        services.append(json.loads(line))
                return {"services": services, "running": True}
            
            return {"services": [], "running": False}
            
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return {"services": [], "running": False}


def detect_deployment_mode() -> str:
    """
    Detect how AICO is deployed
    
    Returns:
        "docker" - Running in Docker containers
        "native" - Running as native processes
        "unknown" - Cannot determine
    """
    client = DockerClient()
    
    # Check if Docker is available and running
    if not client.is_docker_available() or not client.is_docker_running():
        return "native"
    
    # Check if any AICO containers are running
    containers = client.list_aico_containers()
    if containers:
        return "docker"
    
    # Check if native processes are running (fallback detection)
    try:
        import psutil
        for proc in psutil.process_iter(['name', 'cmdline']):
            cmdline = proc.info.get('cmdline', [])
            if cmdline:
                cmdline_str = ' '.join(cmdline)
                if 'gateway_main.py' in cmdline_str or 'core_main.py' in cmdline_str:
                    return "native"
    except (ImportError, Exception):
        pass
    
    return "unknown"
