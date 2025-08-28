"""
AICO Process Management

Cross-platform process lifecycle management with PID files, graceful shutdown,
and health monitoring for AICO backend services.
"""

import os
import sys
import time
import signal
import psutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from .paths import AICOPaths
from .logging import get_logger

logger = get_logger("core", "process")


class ProcessManager:
    """Cross-platform process lifecycle management"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.paths = AICOPaths()
        self.pid_file = self.paths.get_runtime_path() / f"{service_name}.pid"
        self.lock_file = self.paths.get_runtime_path() / f"{service_name}.lock"
        
        # Ensure runtime directory exists
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
    
    def write_pid(self, pid: int) -> None:
        """Write PID to file with metadata"""
        try:
            pid_data = {
                "pid": pid,
                "service": self.service_name,
                "started_at": datetime.now().isoformat(),
                "platform": sys.platform,
                "python_version": sys.version,
                "working_directory": str(Path.cwd())
            }
            
            # Write PID file
            with open(self.pid_file, 'w') as f:
                f.write(str(pid))
            
            # Write lock file with metadata
            import json
            with open(self.lock_file, 'w') as f:
                json.dump(pid_data, f, indent=2)
            
            logger.info(f"PID file written: {self.pid_file} (PID: {pid})")
            
        except Exception as e:
            logger.error(f"Failed to write PID file: {e}")
            raise
    
    def read_pid(self) -> Optional[int]:
        """Read PID from file"""
        try:
            if not self.pid_file.exists():
                return None
            
            with open(self.pid_file, 'r') as f:
                pid_str = f.read().strip()
                return int(pid_str) if pid_str else None
                
        except (ValueError, FileNotFoundError):
            return None
        except Exception as e:
            logger.warning(f"Error reading PID file: {e}")
            return None
    
    def read_metadata(self) -> Optional[Dict[str, Any]]:
        """Read process metadata from lock file"""
        try:
            if not self.lock_file.exists():
                return None
            
            import json
            with open(self.lock_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.warning(f"Error reading process metadata: {e}")
            return None
    
    def cleanup_pid_files(self) -> None:
        """Remove PID and lock files"""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
                logger.debug(f"Removed PID file: {self.pid_file}")
            
            if self.lock_file.exists():
                self.lock_file.unlink()
                logger.debug(f"Removed lock file: {self.lock_file}")
                
        except Exception as e:
            logger.warning(f"Error cleaning up PID files: {e}")
    
    def is_process_running(self, pid: int) -> bool:
        """Check if process with given PID is running"""
        try:
            return psutil.pid_exists(pid)
        except Exception:
            return False
    
    def get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """Get detailed process information"""
        try:
            if not self.is_process_running(pid):
                return None
            
            proc = psutil.Process(pid)
            return {
                "pid": pid,
                "name": proc.name(),
                "status": proc.status(),
                "cpu_percent": proc.cpu_percent(),
                "memory_percent": proc.memory_percent(),
                "create_time": proc.create_time(),
                "cmdline": proc.cmdline()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
        except Exception as e:
            logger.warning(f"Error getting process info: {e}")
            return None
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status"""
        pid = self.read_pid()
        metadata = self.read_metadata()
        
        status = {
            "service": self.service_name,
            "pid_file": str(self.pid_file),
            "pid": pid,
            "running": False,
            "metadata": metadata
        }
        
        if pid:
            if self.is_process_running(pid):
                status["running"] = True
                status["process_info"] = self.get_process_info(pid)
            else:
                # Stale PID file
                status["stale_pid"] = True
                logger.warning(f"Stale PID file found for {self.service_name} (PID: {pid})")
        
        return status
    
    def terminate_process(self, pid: int, timeout: int = 30) -> bool:
        """Gracefully terminate process with timeout and fallback"""
        try:
            if not self.is_process_running(pid):
                logger.info(f"Process {pid} is not running")
                return True
            
            proc = psutil.Process(pid)
            logger.info(f"Terminating process {pid} gracefully...")
            print(f"🔫 ProcessManager: Sending SIGTERM to PID {pid}")
            
            # Step 1: Graceful shutdown (SIGTERM on all platforms)
            # Use SIGTERM consistently across platforms for proper signal handler compatibility
            proc.send_signal(signal.SIGTERM)
            print(f"✅ ProcessManager: SIGTERM sent to PID {pid}")
            
            # Step 2: Wait for graceful shutdown
            try:
                proc.wait(timeout=timeout)
                logger.info(f"Process {pid} terminated gracefully")
                return True
            except psutil.TimeoutExpired:
                logger.warning(f"Process {pid} did not terminate within {timeout}s, forcing...")
            
            # Step 3: Force kill if still running
            if proc.is_running():
                proc.kill()
                try:
                    proc.wait(timeout=5)
                    logger.info(f"Process {pid} force killed")
                    return True
                except psutil.TimeoutExpired:
                    logger.error(f"Failed to kill process {pid}")
                    return False
            
            return True
            
        except psutil.NoSuchProcess:
            logger.info(f"Process {pid} already terminated")
            return True
        except psutil.AccessDenied:
            logger.error(f"Access denied when terminating process {pid}")
            return False
        except Exception as e:
            logger.error(f"Error terminating process {pid}: {e}")
            return False
    
    def stop_service(self, timeout: int = 30) -> bool:
        """Stop the service gracefully using signal termination"""
        status = self.get_service_status()
        
        if not status["running"]:
            logger.info(f"Service {self.service_name} is not running")
            self.cleanup_pid_files()  # Clean up stale PID files
            return True
        
        pid = status["pid"]
        logger.info(f"Stopping {self.service_name} service (PID: {pid})")
        
        # Use direct signal-based termination for all services
        success = self.terminate_process(pid, timeout)
        
        if success:
            # Clean up PID files after successful termination
            self.cleanup_pid_files()
            logger.info(f"Service {self.service_name} stopped successfully")
        
        return success
    
    def _shutdown_via_file(self, pid: int, timeout: int = 30) -> bool:
        """Shutdown gateway service using shutdown file"""
        try:
            from aico.core.paths import AICOPaths
            paths = AICOPaths()
            shutdown_file = paths.get_runtime_path() / "gateway.shutdown"
            
            print(f"Creating shutdown file: {shutdown_file}")
            shutdown_file.touch()
            
            # Wait for process to exit
            proc = psutil.Process(pid)
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if not proc.is_running():
                    print("Gateway stopped via shutdown file")
                    return True
                time.sleep(0.5)
            
            print("Shutdown file timeout, falling back to signal")
            return False
            
        except Exception as e:
            print(f"Shutdown file failed: {e}")
            return False
    
    def find_service_processes(self) -> list:
        """Find running processes that match this service"""
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline:
                        cmdline_str = ' '.join(cmdline)
                        
                        # Look for service-specific patterns
                        if self.service_name == "gateway":
                            if any(pattern in cmdline_str for pattern in [
                                'main.py',
                                'api_gateway',
                                'uvicorn',
                                'AICO_SERVICE_MODE=gateway'
                            ]):
                                processes.append(proc.info)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        except Exception as e:
            logger.warning(f"Error finding service processes: {e}")
        
        return processes
    
    def cleanup_stale_processes(self) -> int:
        """Find and terminate stale service processes"""
        processes = self.find_service_processes()
        terminated = 0
        
        for proc_info in processes:
            pid = proc_info['pid']
            try:
                if self.terminate_process(pid):
                    terminated += 1
                    logger.info(f"Terminated stale process {pid}")
            except Exception as e:
                logger.warning(f"Failed to terminate process {pid}: {e}")
        
        return terminated


class ServiceContext:
    """Context manager for service lifecycle"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.process_manager = ProcessManager(service_name)
        self.pid = None
    
    def __enter__(self):
        self.pid = os.getpid()
        self.process_manager.write_pid(self.pid)
        logger.info(f"Service {self.service_name} started (PID: {self.pid})")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pid:
            self.process_manager.cleanup_pid_files()
            logger.info(f"Service {self.service_name} stopped (PID: {self.pid})")
