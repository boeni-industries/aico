"""
Core Scheduler Components

Provides the main TaskScheduler, TaskRegistry, and TaskExecutor classes
for high-performance async task scheduling and execution.
"""

import asyncio
import os
import importlib
import inspect
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Type
from pathlib import Path

from aico.core.logging import get_logger

# Use try/except to handle both backend and CLI import contexts
try:
    # When imported as backend.scheduler (backend context)
    from backend.scheduler.tasks.base import BaseTask, TaskContext, TaskResult, TaskStatus
    from backend.scheduler.cron import CronParser
    from backend.scheduler.priority_queue import PriorityTaskQueue
    from backend.scheduler.retry_manager import RetryManager, RetryTracker
except ImportError:
    # When imported as scheduler (CLI context with backend in sys.path)
    from scheduler.tasks.base import BaseTask, TaskContext, TaskResult, TaskStatus
    from scheduler.cron import CronParser
    from scheduler.priority_queue import PriorityTaskQueue
    from scheduler.retry_manager import RetryManager, RetryTracker

# Optional imports for backend-specific features (only available when running in backend)
try:
    from backend.core.service_container import ServiceContainer, BaseService
    from backend.services.scheduler.metrics import track_job
    BACKEND_AVAILABLE = True
except ImportError:
    from contextlib import contextmanager
    from abc import ABC
    
    # Stub classes for CLI context
    ServiceContainer = None
    BaseService = ABC  # Use ABC as a placeholder base class
    BACKEND_AVAILABLE = False
    
    # No-op context manager when metrics aren't available
    @contextmanager
    def track_job(*args, **kwargs):
        class NoOpTracker:
            def set_success(self, success): pass
            def set_error(self, error): pass
        yield NoOpTracker()


class TaskRegistry:
    """Registry for discovering and managing task classes"""
    
    def __init__(self, config_manager, db_connection):
        self.config_manager = config_manager
        self.db_connection = db_connection
        self.logger = get_logger("backend.scheduler.task_registry")
        self.tasks: Dict[str, Type[BaseTask]] = {}
        # SchedulerService will be used via UoW instead of TaskStore
        self._session_factory = None
    
    async def discover_tasks(self):
        """Discover and register all available tasks"""
        self.logger.info("Starting task discovery")
        
        # 1. Load built-in tasks from tasks/maintenance.py
        await self._load_builtin_tasks()
        
        # 2. Scan configured plugin modules for BaseTask subclasses
        await self._load_plugin_tasks()
        
        # 3. Load user task definitions from database
        await self._load_user_tasks()
        
        self.logger.info(f"Task discovery completed. Registered {len(self.tasks)} tasks")
    
    async def _load_builtin_tasks(self):
        """Load built-in maintenance tasks"""
        builtin_modules = [
            "backend.scheduler.tasks.maintenance",
            "backend.scheduler.tasks.ams_consolidation",  # AMS Phase 1.5
            "backend.scheduler.tasks.kg_consolidation",  # KG consolidation
            "backend.scheduler.tasks.lmdb_cleanup",  # LMDB cleanup
            "backend.scheduler.tasks.ams_feedback_classification",  # AMS Phase 3
            "backend.scheduler.tasks.ams_thompson_sampling",  # AMS Phase 3
            "backend.scheduler.tasks.ams_trajectory_cleanup",  # AMS Phase 3
            "backend.scheduler.tasks.agency_followups",  # Agency Phase 1
            "backend.scheduler.tasks.curiosity_scan",  # Agency Phase 3
            "backend.scheduler.tasks.agency_reflection",  # Agency reflection / behavioral learning
            "backend.scheduler.tasks.agency_arbiter",  # Agency Phase 4 - Goal Arbiter
            "backend.scheduler.tasks.agency_plan_executor",  # Agency Phase 6.10 - Plan Execution
            "backend.scheduler.tasks.goal_expiration",  # Agency - Goal expiration cleanup
            "backend.scheduler.tasks.issue_detection",  # System Health - Issue Detection
        ]
        
        for module_name in builtin_modules:
            try:
                module = importlib.import_module(module_name)
                task_count = 0
                
                for name in dir(module):
                    obj = getattr(module, name)
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseTask) and 
                        obj != BaseTask and
                        hasattr(obj, 'task_id')):
                        
                        self.tasks[obj.task_id] = obj
                        task_count += 1
                        self.logger.debug(f"Registered built-in task: {obj.task_id}")
                
                self.logger.info(f"Loaded {task_count} tasks from {module_name}")
                
            except ImportError as e:
                self.logger.warning(f"Could not import built-in module {module_name}: {e}")
            except Exception as e:
                self.logger.error(f"Error loading built-in tasks from {module_name}: {e}")
    
    async def _load_plugin_tasks(self):
        """Load tasks from configured plugin modules"""
        try:
            # Get plugin configuration
            plugins_config = self.config_manager.get("api_gateway.plugins", {})
            enabled_plugins = [name for name, config in plugins_config.items() 
                             if config.get("enabled", False)]
            
            task_count = 0
            for plugin_name in enabled_plugins:
                try:
                    # Try to import plugin's task module
                    task_module_name = f"backend.plugins.{plugin_name}.tasks"
                    module = importlib.import_module(task_module_name)
                    
                    for name in dir(module):
                        obj = getattr(module, name)
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseTask) and 
                            obj != BaseTask and
                            hasattr(obj, 'task_id')):
                            
                            self.tasks[obj.task_id] = obj
                            task_count += 1
                            self.logger.debug(f"Registered plugin task: {obj.task_id} from {plugin_name}")
                
                except ImportError:
                    # Plugin doesn't have tasks module - that's OK
                    continue
                except Exception as e:
                    self.logger.error(f"Error loading tasks from plugin {plugin_name}: {e}")
            
            if task_count > 0:
                self.logger.info(f"Loaded {task_count} tasks from plugins")
                
        except Exception as e:
            self.logger.error(f"Error loading plugin tasks: {e}")
    
    async def _load_user_tasks(self):
        """Load user-defined tasks from database and filesystem"""
        try:
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService
            
            # Get user tasks from database via SchedulerService
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                db_tasks_models = await scheduler_service.list_tasks()
                db_tasks = [
                    {
                        'task_id': t.task_id,
                        'task_class': t.task_class,
                        'schedule': t.schedule,
                        'config': t.config,
                        'enabled': t.enabled
                    }
                    for t in db_tasks_models
                ]
                user_tasks = [task for task in db_tasks if task['task_id'].startswith('user.')]
            
            if not user_tasks:
                return
            
            # Import user task classes from tasks/user/ directory
            user_tasks_path = Path("backend/scheduler/tasks/user")
            if not user_tasks_path.exists():
                self.logger.warning("User tasks directory does not exist: backend/scheduler/tasks/user")
                return
            
            task_count = 0
            for task_info in user_tasks:
                task_id = task_info['task_id']
                task_class_name = task_info['task_class']
                
                try:
                    # Derive module name from task_id (user.my_task -> my_task.py)
                    module_name = task_id.replace('user.', '')
                    module_path = f"backend.scheduler.tasks.user.{module_name}"
                    
                    module = importlib.import_module(module_path)
                    task_class = getattr(module, task_class_name)
                    
                    if (inspect.isclass(task_class) and 
                        issubclass(task_class, BaseTask) and
                        hasattr(task_class, 'task_id')):
                        
                        self.tasks[task_id] = task_class
                        task_count += 1
                        self.logger.debug(f"Registered user task: {task_id}")
                    else:
                        self.logger.error(f"Invalid user task class: {task_class_name}")
                
                except Exception as e:
                    self.logger.error(f"Failed to load user task {task_id}: {e}")
            
            if task_count > 0:
                self.logger.info(f"Loaded {task_count} user tasks")
                
        except Exception as e:
            self.logger.error(f"Error loading user tasks: {e}")
    
    def get_task_class(self, task_id: str) -> Optional[Type[BaseTask]]:
        """Get task class by ID"""
        return self.tasks.get(task_id)
    
    def list_task_ids(self) -> List[str]:
        """Get list of all registered task IDs"""
        return list(self.tasks.keys())
    
    async def register_builtin_tasks(self):
        """Register built-in tasks in database with default schedules"""
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.services.scheduler_service import SchedulerService
        from datetime import datetime, UTC
        
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            scheduler_service = SchedulerService(uow)
            
            for task_id, task_class in self.tasks.items():
                if not task_id.startswith('user.'):
                    # Get default config from task class
                    default_config = task_class().get_default_config()
                    schedule = default_config.get('schedule', '0 3 * * *')  # Default: daily at 3 AM
                    enabled = default_config.get('enabled', True)
                    
                    # Check if task exists
                    existing_task = await scheduler_service.get_task(task_id)
                    
                    import json
                    task_data = {
                        'task_id': task_id,
                        'task_class': task_class.__name__,
                        'schedule': schedule,
                        'config': json.dumps(default_config) if default_config else None,
                        'enabled': enabled,
                        'created_at': datetime.now(UTC),
                        'updated_at': datetime.now(UTC)
                    }
                    
                    if existing_task:
                        await scheduler_service.update_task(task_data)
                    else:
                        await scheduler_service.create_task(task_data)


class TaskExecutor:
    """Executes tasks with resource management and error handling"""
    
    def __init__(self, config_manager, db_connection, container=None):
        self.config_manager = config_manager
        self.db_connection = db_connection
        self.container = container
        self.logger = get_logger("backend.scheduler.task_executor")
        # SchedulerService will be used via UoW instead of TaskStore
        self.running_tasks: Dict[str, asyncio.Task] = {}
        # Track execution start times and timeouts for stuck task detection
        self.task_start_times: Dict[str, datetime] = {}
        self.task_timeouts: Dict[str, int] = {}  # Configured timeout per task
        self.stuck_buffer_seconds = 300  # 5 minute buffer beyond timeout
        self.last_stuck_check: Optional[datetime] = None
    
    async def execute_task(self, task_class: Type[BaseTask], task_config: Dict[str, Any], retry_count: int = 0) -> TaskResult:
        """Execute a single task with full lifecycle management"""
        task_id = task_config['task_id']
        execution_id = str(uuid.uuid4())
        
        self.logger.debug(f"Executing task: {task_id} (execution_id: {execution_id})")
        
        # Check if task is already running in this process
        if task_id in self.running_tasks:
            self.logger.warning(f"Task {task_id} is already running, skipping")
            return TaskResult(success=False, message="Task already running", skipped=True)
        
        # CRITICAL: Define start_time BEFORE using it
        start_time = datetime.now(timezone.utc)
        
        # Add to running tasks (local process coordination)
        self.running_tasks[task_id] = asyncio.current_task()
        self.task_start_times[task_id] = start_time
        
        # Store configured timeout for this task (for stuck detection)
        # Prefer task-specific max_duration_seconds over global timeout
        task_specific_timeout = task_config.get('config', {}).get('max_duration_seconds') if isinstance(task_config.get('config'), dict) else None
        if task_specific_timeout:
            task_timeout = task_specific_timeout
        else:
            scheduler_config = self.get_config("scheduler", {})
            task_timeout = scheduler_config.get("task_timeout", 3600)  # 1 hour default
        self.task_timeouts[task_id] = task_timeout
        
        # Get session factory for database operations
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.services.scheduler_service import SchedulerService
        
        session_factory = await get_session_factory()

        task_instance = None

        # Track job execution metrics
        with track_job(task_id, queue_name=task_config.get('queue', 'default')) as tracker:
            try:
                # Record execution start via SchedulerService
                async with UnitOfWork(session_factory) as uow:
                    scheduler_service = SchedulerService(uow)
                    await scheduler_service.create_execution({
                        'execution_id': execution_id,
                        'task_id': task_id,
                        'status': 'running',
                        'started_at': start_time,
                        'created_at': start_time
                    })
                
                # Create task instance and context
                task_instance = task_class()

                # Normalize instance config: it may be stored as a JSON string
                # in scheduler_tasks.config, or already as a dict. Tasks expect
                # a mapping for context.get_config(), not a raw string.
                raw_config = task_config.get('config')
                if isinstance(raw_config, str) and raw_config.strip():
                    try:
                        instance_config = json.loads(raw_config)
                    except Exception:
                        instance_config = {}
                elif isinstance(raw_config, dict):
                    instance_config = raw_config
                else:
                    instance_config = {}

                context = TaskContext(
                    task_id=task_id,
                    config_manager=self.config_manager,
                    db_connection=self.db_connection,
                    instance_config=instance_config,
                    execution_id=execution_id,
                    service_container=self.container,
                    retry_count=retry_count  # Phase 6.2: Pass retry count to context
                )
                
                # Apply task defaults to context for config resolution
                context.task_defaults = task_instance.get_default_config()
                
                # Check resource constraints
                if not await self._check_resource_constraints(context):
                    result = TaskResult(success=False, message="Resource constraints not met", skipped=True)
                    await self._record_completion(task_id, execution_id, result, TaskStatus.SKIPPED, start_time)
                    tracker.set_success(False)
                    return result
                
                # Execute task with timeout
                # Prefer task-specific max_duration_seconds over global scheduler.task_timeout
                task_specific_timeout = instance_config.get("max_duration_seconds")
                if task_specific_timeout:
                    timeout = task_specific_timeout
                    self.logger.info(f"Using task-specific timeout: {timeout}s for {task_id}")
                else:
                    scheduler_config = self.get_config("scheduler", {})
                    timeout = scheduler_config.get("task_timeout", 3600)  # 1 hour default
                    self.logger.debug(f"Using global timeout: {timeout}s for {task_id}")
                
                try:
                    result = await asyncio.wait_for(task_instance.execute(context), timeout=timeout)
                    status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
                    
                except asyncio.TimeoutError:
                    result = TaskResult(success=False, error="Task execution timed out")
                    status = TaskStatus.FAILED
                    self.logger.error(f"Task {task_id} timed out after {timeout} seconds")
                
                # Record completion
                await self._record_completion(task_id, execution_id, result, status, start_time)
                
                # Record metrics
                tracker.set_success(result.success)
                if not result.success and result.error:
                    tracker.set_error(result.error)
                
                self.logger.info(f"Task {task_id} completed: {result.message}")
                return result
                
            except Exception as e:
                error_msg = f"Task execution failed: {str(e)}"
                result = TaskResult(success=False, error=error_msg)
                await self._record_completion(task_id, execution_id, result, TaskStatus.FAILED, start_time)
                
                tracker.set_success(False)
                tracker.set_error(error_msg)
                
                self.logger.error(f"Task {task_id} failed: {e}")
                import traceback
                traceback.print_exc()
                return result
                
            finally:
                # Cleanup task instance
                if task_instance:
                    try:
                        await task_instance.cleanup()
                    except Exception as e:
                        self.logger.warning(f"Task cleanup failed for {task_id}: {e}")
                
                # CRITICAL: Remove from running tasks to prevent permanent blocking
                # This MUST be in finally block to ensure it always runs
                try:
                    if task_id in self.running_tasks:
                        del self.running_tasks[task_id]
                        self.logger.debug(f"✓ Removed {task_id} from running_tasks")
                    else:
                        # LOG LOUDLY: Task wasn't in running_tasks - this shouldn't happen
                        self.logger.warning(
                            f"⚠️  Task {task_id} was not in running_tasks during cleanup. "
                            f"This may indicate a state management issue."
                        )
                    
                    # Clean up start time and timeout tracking
                    if task_id in self.task_start_times:
                        del self.task_start_times[task_id]
                    if task_id in self.task_timeouts:
                        del self.task_timeouts[task_id]
                        
                except KeyError:
                    self.logger.warning(f"Task {task_id} was not in running_tasks dict during cleanup.")
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value from config manager"""
        return self.config_manager.get(key, default)
    
    async def _check_resource_constraints(self, context: TaskContext) -> bool:
        """Check if system resources allow task execution"""
        try:
            import psutil
            from datetime import datetime, time
            
            scheduler_config = self.get_config("scheduler", {})
            max_cpu = scheduler_config.get("max_cpu_percent", 80)
            max_memory = scheduler_config.get("max_memory_percent", 80)
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if cpu_percent > max_cpu:
                self.logger.info(
                    f"Task {context.task_id} skipped: CPU usage {cpu_percent}% exceeds limit {max_cpu}%"
                )
                return False
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > max_memory:
                self.logger.info(
                    f"Task {context.task_id} skipped: Memory usage {memory.percent}% exceeds limit {max_memory}%"
                )
                return False
            
            # Check quiet hours for agency tasks
            if context.task_id.startswith("agency."):
                quiet_hours_config = scheduler_config.get("quiet_hours", {})
                if quiet_hours_config.get("enabled", False):
                    now = datetime.now(timezone.utc).time()
                    start_str = quiet_hours_config.get("start", "22:00")
                    end_str = quiet_hours_config.get("end", "08:00")
                    
                    try:
                        start_time = time.fromisoformat(start_str)
                        end_time = time.fromisoformat(end_str)
                        
                        # Handle quiet hours that span midnight
                        if start_time <= end_time:
                            in_quiet_hours = start_time <= now <= end_time
                        else:
                            in_quiet_hours = now >= start_time or now <= end_time
                        
                        if in_quiet_hours:
                            self.logger.info(
                                f"Agency task {context.task_id} skipped: currently in quiet hours ({start_str}-{end_str})"
                            )
                            return False
                    except ValueError as e:
                        self.logger.warning(f"Invalid quiet hours config: {e}")
            
            # Check network bandwidth (if configured)
            network_config = scheduler_config.get("network", {})
            if network_config.get("check_bandwidth", False):
                max_bandwidth_mbps = network_config.get("max_bandwidth_mbps", 10)
                
                # Get network I/O stats
                net_io = psutil.net_io_counters()
                if hasattr(context, '_last_net_io'):
                    # Calculate bandwidth usage
                    bytes_sent = net_io.bytes_sent - context._last_net_io.bytes_sent
                    bytes_recv = net_io.bytes_recv - context._last_net_io.bytes_recv
                    total_bytes = bytes_sent + bytes_recv
                    
                    # Convert to Mbps (assuming 1 second interval)
                    mbps = (total_bytes * 8) / (1024 * 1024)
                    
                    if mbps > max_bandwidth_mbps:
                        self.logger.info(
                            f"Task {context.task_id} skipped: Network usage {mbps:.2f} Mbps exceeds limit {max_bandwidth_mbps} Mbps"
                        )
                        return False
                
                # Store for next check
                context._last_net_io = net_io
            
            # Check concurrent execution limits
            max_concurrent = scheduler_config.get("max_concurrent_tasks", 5)
            if hasattr(self, '_running_tasks'):
                if len(self._running_tasks) >= max_concurrent:
                    self.logger.info(
                        f"Task {context.task_id} skipped: {len(self._running_tasks)} tasks running (limit: {max_concurrent})"
                    )
                    return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Resource check failed: {e}")
            return True  # Allow execution on check failure
    
    def check_for_stuck_tasks(self) -> list:
        """
        Check for tasks that have been running longer than their timeout + buffer.
        
        Uses task-specific timeout (default 1 hour) + 5 minute buffer to detect
        truly stuck tasks without false positives for legitimately long-running tasks.
        
        This method is called by the scheduler to detect stuck tasks.
        Returns list of stuck task details for logging/alerting.
        
        Returns:
            List of dicts with stuck task information
        """
        now = datetime.now(timezone.utc)
        stuck_tasks = []
        
        # Only check periodically to avoid spam (every 60 seconds)
        if self.last_stuck_check:
            time_since_last_check = (now - self.last_stuck_check).total_seconds()
            if time_since_last_check < 60:
                return stuck_tasks
        
        self.last_stuck_check = now
        
        for task_id, start_time in self.task_start_times.items():
            duration_seconds = (now - start_time).total_seconds()
            
            # Get task-specific timeout (or use default)
            task_timeout = self.task_timeouts.get(task_id, 3600)  # 1 hour default
            stuck_threshold = task_timeout + self.stuck_buffer_seconds
            
            # Only report if running longer than timeout + buffer
            if duration_seconds > stuck_threshold:
                duration_minutes = duration_seconds / 60
                timeout_minutes = task_timeout / 60
                threshold_minutes = stuck_threshold / 60
                
                stuck_tasks.append({
                    'task_id': task_id,
                    'start_time': start_time.isoformat(),
                    'duration_seconds': duration_seconds,
                    'duration_minutes': duration_minutes,
                    'timeout_seconds': task_timeout,
                    'threshold_seconds': stuck_threshold
                })
                
                # Log loudly
                self.logger.error(
                    f"⚠️  STUCK TASK DETECTED: {task_id} has been running for "
                    f"{duration_minutes:.1f} minutes (timeout: {timeout_minutes:.1f} min, "
                    f"threshold: {threshold_minutes:.1f} min)"
                )
                print(f"\n{'='*80}")
                print(f"⚠️  STUCK TASK DETECTED")
                print(f"{'='*80}")
                print(f"Task ID: {task_id}")
                print(f"Started: {start_time.isoformat()}")
                print(f"Duration: {duration_minutes:.1f} minutes")
                print(f"Configured Timeout: {timeout_minutes:.1f} minutes")
                print(f"Stuck Threshold: {threshold_minutes:.1f} minutes (timeout + 5 min buffer)")
                print(f"Status: Task exceeded timeout + buffer - likely hung")
                print(f"{'='*80}\n")
                
                # Broadcast event to WebSocket clients
                try:
                    import asyncio
                    from backend.api.scheduler.events import broadcast_scheduler_event
                    
                    event = {
                        'type': 'task_stuck',
                        'task_id': task_id,
                        'severity': 'error',
                        'timestamp': now.isoformat(),
                        'details': {
                            'duration_minutes': duration_minutes,
                            'timeout_minutes': timeout_minutes,
                            'threshold_minutes': threshold_minutes,
                            'start_time': start_time.isoformat()
                        }
                    }
                    
                    # Schedule broadcast in event loop
                    asyncio.create_task(broadcast_scheduler_event(event))
                except Exception as e:
                    self.logger.warning(f"Failed to broadcast stuck task event: {e}")
        
        return stuck_tasks
    
    async def _record_completion(self, task_id: str, execution_id: str, result: TaskResult, 
                               status: TaskStatus, start_time: datetime):
        """Record task completion in database via SchedulerService.
        
        CRITICAL: This method MUST succeed or raise an exception.
        Silent failures here cause jobs to stay stuck in 'running' status forever.
        """
        try:
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService
            from aico.ai.scheduler.models import SchedulerTaskExecution

            # Validate inputs
            if not task_id:
                raise ValueError("task_id cannot be empty")
            if not execution_id:
                raise ValueError("execution_id cannot be empty")
            if not status:
                raise ValueError("status cannot be None")

            end_time = datetime.now(timezone.utc)
            duration_seconds = (end_time - start_time).total_seconds()

            # Build a small structured result payload; repository will serialize this
            result_payload = {
                "success": bool(getattr(result, "success", False)),
                "skipped": bool(getattr(result, "skipped", False)),
                "message": getattr(result, "message", None),
                "data": getattr(result, "data", None),
                "error": getattr(result, "error", None),
            }

            session_factory = await get_session_factory()
            if not session_factory:
                raise RuntimeError("Failed to get session_factory - database connection unavailable")
            
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                
                # Get existing execution to retrieve database ID
                self.logger.debug(f"Looking up execution {execution_id} for task {task_id}")
                executions = await uow.scheduler_task_executions.list(
                    filters={"task_id": task_id},
                    limit=500  # Increased from 100 to handle high-frequency tasks
                )
                
                self.logger.debug(f"Found {len(executions)} executions for task {task_id}")
                
                # Find the execution by execution_id (UUID)
                existing_execution = None
                for exec in executions:
                    if exec.execution_id == execution_id:
                        existing_execution = exec
                        break
                
                if not existing_execution:
                    error_msg = (
                        f"CRITICAL: Could not find execution {execution_id} for task {task_id} to update. "
                        f"This will cause the job to stay stuck in 'running' status. "
                        f"Found {len(executions)} total executions for this task."
                    )
                    self.logger.error(error_msg)
                    raise RuntimeError(error_msg)
                
                # Validate we have the database ID
                if not hasattr(existing_execution, 'id') or existing_execution.id is None:
                    error_msg = (
                        f"CRITICAL: Execution {execution_id} has no database ID. "
                        f"Cannot update without primary key. This is a data integrity issue."
                    )
                    self.logger.error(error_msg)
                    raise RuntimeError(error_msg)
                
                self.logger.debug(
                    f"Updating execution {execution_id} (db_id={existing_execution.id}) "
                    f"with status={status.value if hasattr(status, 'value') else str(status)}"
                )
                
                # Update the execution with completion data
                existing_execution.status = status.value if hasattr(status, "value") else str(status)
                existing_execution.completed_at = end_time
                existing_execution.result = result_payload
                existing_execution.error_message = getattr(result, "error", None)
                existing_execution.duration_seconds = duration_seconds
                
                # Perform the update
                updated = await uow.scheduler_task_executions.update(existing_execution)
                
                # Verify the update returned something
                if not updated:
                    error_msg = (
                        f"CRITICAL: Update operation for execution {execution_id} returned None. "
                        f"This may indicate the update failed silently."
                    )
                    self.logger.error(error_msg)
                    raise RuntimeError(error_msg)
                
                # Commit the transaction
                await uow.commit()
                
                self.logger.info(
                    f"Successfully recorded completion for task {task_id}, "
                    f"execution {execution_id}, status={existing_execution.status}, "
                    f"duration={duration_seconds:.2f}s"
                )

        except Exception as e:
            # Log with full context
            error_msg = (
                f"❌ CRITICAL FAILURE in _record_completion: "
                f"task_id={task_id}, execution_id={execution_id}, status={status}. "
                f"Error: {e}"
            )
            # Log to logger with full stack trace
            self.logger.error(error_msg, exc_info=True)
            
            # ALSO print to console for immediate visibility
            print(f"\n{'='*80}")
            print(f"❌ SCHEDULER ERROR: Failed to record job completion")
            print(f"{'='*80}")
            print(f"Task ID: {task_id}")
            print(f"Execution ID: {execution_id}")
            print(f"Status: {status}")
            print(f"Error: {e}")
            print(f"{'='*80}")
            import traceback
            traceback.print_exc()
            print(f"{'='*80}\n")
            
            # RE-RAISE to prevent jobs from staying stuck in 'running' state
            # This will cause the task to fail visibly rather than silently
            raise RuntimeError(f"Failed to record completion for {task_id}: {e}") from e
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task (Phase 6.2)
        
        Args:
            task_id: Task to cancel
            
        Returns:
            True if task was cancelled, False if not running
        """
        if task_id not in self.running_tasks:
            self.logger.warning(f"Cannot cancel {task_id} - not running")
            return False
        
        task = self.running_tasks[task_id]
        task.cancel()
        
        self.logger.info(f"Cancelled task {task_id}")
        return True


class TaskScheduler(BaseService):
    """Main scheduler that coordinates task discovery, scheduling, and execution"""
    
    def __init__(self, name: str, container):
        super().__init__(name, container)
        
        # Core components
        self.task_registry = None
        self.task_executor = None
        # SchedulerService will be used via UoW instead of TaskStore
        self.cron_parser = CronParser()
        
        # Phase 6.2: Priority queue and retry management
        self.priority_queue = None
        self.retry_manager = RetryManager()
        self.retry_tracker = RetryTracker()
        
        # Runtime state
        self.running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        self.next_run_times: Dict[str, datetime] = {}
    
    async def initialize(self) -> None:
        """Initialize scheduler components"""
        # Database not needed - PostgreSQL uses UoW pattern per request
        config_manager = self.container.config
        
        # Initialize core components
        self.task_registry = TaskRegistry(config_manager, None)
        self.task_executor = TaskExecutor(config_manager, None, self.container)
        
        # Phase 6.2: Initialize priority queue
        scheduler_config = config_manager.get("scheduler", {})
        max_queue_size = scheduler_config.get("max_queue_size", 1000)
        self.priority_queue = PriorityTaskQueue(max_queue_size=max_queue_size)
        
        self.logger.debug("Task scheduler initialized with priority queue")
    
    async def start(self) -> None:
        """Start the scheduler"""
        if self.running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.logger.info("Starting AICO Task Scheduler")
        
        try:
            # Discover and register tasks
            await self.task_registry.discover_tasks()
            
            # Register built-in tasks in database
            await self.task_registry.register_builtin_tasks()
            
            # Calculate initial run times
            await self._calculate_next_run_times()
            
            # Start scheduler loop
            self.running = True
            self.scheduler_task = asyncio.create_task(self._scheduler_loop())
            
            log_message = "Task Scheduler started successfully"
            self.logger.info(log_message)
            print(f"[+] {log_message}")
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")
            self.running = False
            raise
    
    async def stop(self) -> None:
        """Stop the scheduler"""
        if not self.running:
            return
        
        self.logger.info("Stopping task scheduler")
        self.running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Task scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop - resilient to individual task failures"""
        scheduler_config = self.get_config("scheduler", {})
        interval = scheduler_config.get("scheduler_interval", 1.0)
        
        self.logger.debug(f"Scheduler loop started (interval: {interval}s)")
        
        while self.running:
            try:
                await self._check_and_execute_tasks()
            except asyncio.CancelledError:
                self.logger.debug("Scheduler loop cancelled")
                break
            except Exception as e:
                # Log error loudly but DON'T crash the scheduler
                error_msg = f"❌ SCHEDULER LOOP ERROR: {e}"
                self.logger.error(error_msg, exc_info=True)
                print(f"\n{'='*80}")
                print(f"❌ SCHEDULER ERROR: Task check/execute failed")
                print(f"{'='*80}")
                print(f"Error: {e}")
                print(f"{'='*80}")
                import traceback
                traceback.print_exc()
                print(f"{'='*80}\n")
                # Continue running - don't let one error stop the scheduler
            
            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                self.logger.debug("Scheduler loop cancelled during sleep")
                break
    
    async def _check_for_triggers(self) -> List[str]:
        """Check for manually triggered tasks via trigger files."""
        triggered_tasks = []
        try:
            from aico.core.paths import AICOPaths
            paths = AICOPaths()
            trigger_dir = paths.get_runtime_path() / "scheduler" / "triggers"

            if not trigger_dir.exists():
                return []

            for trigger_file in trigger_dir.glob("*.trigger"):
                task_id = trigger_file.stem
                self.logger.debug(f"Manual trigger file detected for task: {task_id}")
                triggered_tasks.append(task_id)
                try:
                    trigger_file.unlink()  # Delete after processing
                except OSError as e:
                    self.logger.error(f"Failed to delete trigger file {trigger_file}: {e}")

        except Exception as e:
            self.logger.error(f"Error checking for task triggers: {e}")

        return triggered_tasks

    async def _check_and_execute_tasks(self):
        """Check for tasks that need to run and execute them (Phase 6.2: Priority Queue)
        
        This method is called every scheduler tick. Errors in individual tasks should
        not prevent other tasks from running.
        """
        now = datetime.now(timezone.utc)
        
        # 0. Monitor for stuck tasks (TaskExecutor owns this, throttles internally)
        try:
            stuck_tasks = self.task_executor.check_for_stuck_tasks()
            if stuck_tasks:
                self.logger.warning(f"Detected {len(stuck_tasks)} stuck task(s)")
        except Exception as e:
            self.logger.error(f"Failed to check for stuck tasks: {e}")
        
        # 1. Enqueue scheduled tasks that are due
        for task_id, next_run in list(self.next_run_times.items()):
            if next_run <= now:
                try:
                    await self._enqueue_task(task_id, is_scheduled=True)
                except Exception as e:
                    # Log but don't crash - other tasks should still run
                    self.logger.error(f"❌ Failed to enqueue scheduled task {task_id}: {e}", exc_info=True)
                    print(f"❌ Failed to enqueue task {task_id}: {e}")

        # 2. Enqueue manually triggered tasks
        try:
            triggered_tasks = await self._check_for_triggers()
            for task_id in triggered_tasks:
                try:
                    await self._enqueue_task(task_id, is_scheduled=False)
                except Exception as e:
                    self.logger.error(f"❌ Failed to enqueue triggered task {task_id}: {e}", exc_info=True)
                    print(f"❌ Failed to enqueue triggered task {task_id}: {e}")
        except Exception as e:
            self.logger.error(f"❌ Failed to check for triggers: {e}", exc_info=True)
        
        # 3. Execute tasks from priority queue
        try:
            await self._execute_from_priority_queue()
        except Exception as e:
            self.logger.error(f"❌ Failed to execute from priority queue: {e}", exc_info=True)
            print(f"❌ Failed to execute from priority queue: {e}")
    
    async def _enqueue_task(self, task_id: str, is_scheduled: bool = True):
        """Enqueue task to priority queue
        
        Args:
            task_id: Task identifier
            is_scheduled: Whether this is a scheduled task (vs triggered)
        """
        try:
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                task_model = await scheduler_service.get_task(task_id)
            
            if not task_model:
                return
            
            task_config = {
                'task_id': task_model.task_id,
                'task_class': task_model.task_class,
                'schedule': task_model.schedule,
                'config': task_model.config,
                'enabled': task_model.enabled
            }
            
            # For scheduled tasks, check if enabled. For triggered tasks, run regardless.
            if is_scheduled and not task_config.get('enabled', True):
                return
            
            task_class = self.task_registry.get_task_class(task_id)
            if not task_class:
                if is_scheduled and task_config.get('enabled', True):
                    await self._disable_unknown_task(task_id)
                self.logger.warning(f"Task class not found for {task_id}")
                return

            # For scheduled tasks, advance next_run immediately to prevent re-enqueueing on every tick
            # This must happen BEFORE the early return checks
            if is_scheduled and task_id in self.next_run_times:
                schedule = task_config.get('schedule')
                if schedule:
                    next_run = self.cron_parser.next_run_time(schedule, datetime.now(timezone.utc))
                    if next_run:
                        self.next_run_times[task_id] = next_run

            # Prevent enqueue storms: if already running or already queued, don't enqueue again
            if task_id in self.task_executor.running_tasks:
                # LOG LOUDLY: This could indicate a stuck task
                self.logger.warning(
                    f"⚠️  Task {task_id} is already in running_tasks - skipping enqueue. "
                    f"If this persists, the task may be stuck."
                )
                print(f"⚠️  Task {task_id} blocked: already running")
                return
            if hasattr(self, "priority_queue") and self.priority_queue and self.priority_queue.has_task(task_id):
                self.logger.debug(f"Task {task_id} already queued - skipping duplicate enqueue")
                return
            
            # Get task instance to access priority and queue
            task_instance = task_class()
            
            # Get retry count for this task
            retry_count = self.retry_tracker.get_retry_count(task_id)
            
            # Enqueue to priority queue
            success = self.priority_queue.enqueue(
                task_id=task_id,
                task_class=task_class.__name__,
                priority=task_instance.priority,
                queue=task_instance.queue,
                config=task_config,
                retry_count=retry_count
            )
            
            if success:
                self.logger.debug(
                    f"Enqueued {task_id} to {task_instance.queue.value} queue "
                    f"(priority={task_instance.priority.name})"
                )
            else:
                # LOG LOUDLY: Queue full is a serious issue
                error_msg = f"❌ CRITICAL: Failed to enqueue {task_id} - queue full!"
                self.logger.error(error_msg)
                print(f"\n{'='*80}")
                print(error_msg)
                print(f"Queue: {task_instance.queue.value}")
                print(f"Priority: {task_instance.priority.name}")
                print(f"This task will NOT run until queue space is available!")
                print(f"{'='*80}\n")
                
        except Exception as e:
            self.logger.error(f"Error enqueuing task {task_id}: {e}")

    async def _disable_unknown_task(self, task_id: str) -> None:
        try:
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                await scheduler_service.disable_task(task_id)

            if task_id in self.next_run_times:
                del self.next_run_times[task_id]
        except Exception as e:
            self.logger.error(f"Failed to disable unknown task {task_id}: {e}")
    
    async def _execute_from_priority_queue(self):
        """Execute tasks from priority queue based on fair scheduling"""
        # Get scheduler config for concurrent task limits
        scheduler_config = self.get_config("scheduler", {})
        max_concurrent = scheduler_config.get("max_concurrent_tasks", 5)
        
        # Check how many tasks are currently running
        running_count = len(self.task_executor.running_tasks)
        
        # Execute tasks up to concurrent limit
        while running_count < max_concurrent:
            # Dequeue next task (fair scheduling across queues)
            prioritized_task = self.priority_queue.dequeue()
            
            if not prioritized_task:
                break  # No more tasks in queue
            
            # Get task class
            task_class = self.task_registry.get_task_class(prioritized_task.task_id)
            if not task_class:
                await self._disable_unknown_task(prioritized_task.task_id)
                self.logger.warning(f"Task class not found for {prioritized_task.task_id}")
                continue
            
            # Execute task asynchronously with retry support
            asyncio.create_task(
                self._execute_task_with_retry(task_class, prioritized_task)
            )
            
            running_count += 1
    
    async def _execute_task_with_retry(self, task_class: Type[BaseTask], prioritized_task):
        """Execute task with retry logic
        
        Args:
            task_class: Task class to execute
            prioritized_task: PrioritizedTask from queue
        """
        task_id = prioritized_task.task_id
        retry_count = prioritized_task.retry_count
        
        try:
            # Execute task
            result = await self.task_executor.execute_task(
                task_class, 
                prioritized_task.config,
                retry_count=retry_count
            )
            
            # Handle result
            if result.success:
                # Success - clear retry history
                self.retry_tracker.record_success(task_id)
                # Note: next_run_times is already advanced when task becomes due (in _enqueue_task)
            
            elif not result.skipped:
                # Failure - check if should retry
                task_instance = task_class()
                retry_config = task_instance.retry_config
                
                if self.retry_manager.should_retry(retry_count, retry_config):
                    # Record failure
                    failure_reason = result.error or result.message
                    self.retry_tracker.record_failure(task_id, failure_reason)
                    
                    # Calculate retry delay
                    delay_seconds = self.retry_manager.calculate_delay(retry_count, retry_config)
                    
                    # Re-enqueue for retry after delay
                    await asyncio.sleep(delay_seconds)
                    
                    success = self.priority_queue.enqueue(
                        task_id=task_id,
                        task_class=task_class.__name__,
                        priority=task_instance.priority,
                        queue=task_instance.queue,
                        config=prioritized_task.config,
                        retry_count=retry_count + 1
                    )
                    
                    if success:
                        self.logger.info(
                            f"Re-enqueued {task_id} for retry {retry_count + 1}/"
                            f"{retry_config.max_retries} after {delay_seconds}s"
                        )
                else:
                    # Max retries exceeded
                    self.logger.error(
                        f"Task {task_id} failed after {retry_count} retries, giving up"
                    )
                    self.retry_tracker.clear(task_id)
                    
        except Exception as e:
            self.logger.error(f"Error executing task {task_id}: {e}")
    
    async def _calculate_next_run_times(self):
        """Calculate next run times for all enabled tasks"""
        try:
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                task_models = await scheduler_service.get_active_tasks()
            
            now = datetime.now(timezone.utc)
            
            for task_model in task_models:
                task_id = task_model.task_id
                schedule = task_model.schedule
                
                next_run = self.cron_parser.next_run_time(schedule, now)
                if next_run:
                    self.next_run_times[task_id] = next_run
                    self.logger.debug(f"Next run for {task_id}: {next_run}")
                else:
                    self.logger.error(f"Invalid schedule for task {task_id}: {schedule}")
            
            self.logger.info(f"Calculated next run times for {len(self.next_run_times)} tasks")
            
        except Exception as e:
            self.logger.error(f"Failed to calculate next run times: {e}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task (Phase 6.2)
        
        Cancels task if running, or removes from queue if pending.
        
        Args:
            task_id: Task to cancel
            
        Returns:
            True if task was cancelled/removed
        """
        # Try to cancel if running
        cancelled = await self.task_executor.cancel_task(task_id)
        if cancelled:
            return True
        
        # Try to remove from priority queue
        removed = self.priority_queue.remove(task_id)
        if removed:
            self.logger.info(f"Removed task {task_id} from priority queue")
            return True
        
        self.logger.warning(f"Task {task_id} not found (not running or queued)")
        return False
    
    async def trigger_task(self, task_id: str) -> TaskResult:
        """Manually trigger a task execution"""
        try:
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                task_model = await scheduler_service.get_task(task_id)
            
            if not task_model:
                return TaskResult(success=False, error=f"Task not found: {task_id}")
            
            task_config = {
                'task_id': task_model.task_id,
                'task_class': task_model.task_class,
                'schedule': task_model.schedule,
                'config': task_model.config,
                'enabled': task_model.enabled
            }
            
            task_class = self.task_registry.get_task_class(task_id)
            if not task_class:
                return TaskResult(success=False, error=f"Task class not found: {task_id}")
            
            result = await self.task_executor.execute_task(task_class, task_config)
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to trigger task {task_id}: {e}")
            return TaskResult(success=False, error=str(e))
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status information"""
        return {
            'running': self.running,
            'registered_tasks': len(self.task_registry.tasks),
            'scheduled_tasks': len(self.next_run_times),
            'running_tasks': len(self.task_executor.running_tasks),
            'next_run_times': {
                task_id: next_run.isoformat() 
                for task_id, next_run in self.next_run_times.items()
            }
        }
