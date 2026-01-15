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
            "backend.scheduler.tasks.proactive_conversation",  # Agency Phase 6.11 - Proactive Conversations
            "backend.scheduler.tasks.goal_expiration",  # Agency - Goal expiration cleanup
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
                        print(f"📋 [SCHEDULER] Registered built-in task: {obj.task_id}")
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
            plugins_config = self.config_manager.get("plugins", {})
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
    
    async def execute_task(self, task_class: Type[BaseTask], task_config: Dict[str, Any], retry_count: int = 0) -> TaskResult:
        """Execute a single task with full lifecycle management"""
        task_id = task_config['task_id']
        execution_id = str(uuid.uuid4())
        
        self.logger.debug(f"Executing task: {task_id} (execution_id: {execution_id})")
        
        # Check if task is already running
        if task_id in self.running_tasks:
            self.logger.warning(f"Task {task_id} is already running, skipping")
            return TaskResult(success=False, message="Task already running", skipped=True)
        
        # Acquire execution lock via SchedulerService
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.services.scheduler_service import SchedulerService
        
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            scheduler_service = SchedulerService(uow)
            lock_acquired = await scheduler_service.acquire_lock(task_id, execution_id, ttl_seconds=3600)
        
        if not lock_acquired:
            self.logger.warning(f"Could not acquire lock for task {task_id}")
            return TaskResult(success=False, message="Could not acquire execution lock", skipped=True)

        # Add to running tasks *after* acquiring lock
        self.running_tasks[task_id] = asyncio.current_task()

        start_time = datetime.now(timezone.utc)
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
                
                context = TaskContext(
                    task_id=task_id,
                    config_manager=self.config_manager,
                    db_connection=self.db_connection,
                    instance_config=task_config.get('config', {}),
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
                scheduler_config = self.get_config("scheduler", {})
                timeout = scheduler_config.get("task_timeout", 3600)  # 1 hour default
                
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
                # Cleanup
                if task_instance:
                    try:
                        await task_instance.cleanup()
                    except Exception as e:
                        self.logger.warning(f"Task cleanup failed for {task_id}: {e}")
                
                # Release lock via SchedulerService
                async with UnitOfWork(session_factory) as uow:
                    scheduler_service = SchedulerService(uow)
                    await scheduler_service.release_lock(task_id, execution_id)

            # Remove from running tasks
            try:
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]
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
    
    async def _record_completion(self, task_id: str, execution_id: str, result: TaskResult, 
                               status: TaskStatus, start_time: datetime):
        """Record task completion in database via SchedulerService"""
        try:
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService
            
            end_time = datetime.now(timezone.utc)
            result.duration_seconds = (end_time - start_time).total_seconds()
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                await scheduler_service.update_execution({
                    'execution_id': execution_id,
                    'task_id': task_id,
                    'status': status.value if hasattr(status, 'value') else str(status),
                    'completed_at': end_time,
                    'result': result.message,
                    'error': result.error,
                    'duration_seconds': result.duration_seconds
                })
            
        except Exception as e:
            self.logger.error(f"Failed to record completion for {task_id}: {e}")
    
    def get_running_tasks(self) -> List[str]:
        """Get list of currently running task IDs"""
        return list(self.running_tasks.keys())
    
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
        
        # Clean up any stale locks from previous runs (e.g., if backend crashed)
        self.logger.info("Cleaning up stale task locks from previous runs...")
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.services.scheduler_service import SchedulerService
        
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            scheduler_service = SchedulerService(uow)
            # Clean up all locks (simple approach - delete all)
            all_locks = await scheduler_service.check_lock('')  # Get all locks
            # Note: SchedulerService doesn't have bulk delete, so we'll rely on cleanup_expired_locks
            await scheduler_service.cleanup_expired_locks()
        self.logger.info("Stale task locks cleared")
        
        self.logger.info("Task scheduler initialized with priority queue")
    
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
        """Main scheduler loop"""
        scheduler_config = self.get_config("scheduler", {})
        interval = scheduler_config.get("scheduler_interval", 1.0)
        
        self.logger.info(f"Scheduler loop started (interval: {interval}s)")
        
        try:
            while self.running:
                await self._check_and_execute_tasks()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            self.logger.info("Scheduler loop cancelled")
        except Exception as e:
            self.logger.error(f"Scheduler loop error: {e}")
            raise
    
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
                self.logger.info(f"Manual trigger file detected for task: {task_id}")
                triggered_tasks.append(task_id)
                try:
                    trigger_file.unlink()  # Delete after processing
                except OSError as e:
                    self.logger.error(f"Failed to delete trigger file {trigger_file}: {e}")

        except Exception as e:
            self.logger.error(f"Error checking for task triggers: {e}")

        return triggered_tasks

    async def _check_and_execute_tasks(self):
        """Check for tasks that need to run and execute them (Phase 6.2: Priority Queue)"""
        try:
            now = datetime.now(timezone.utc)
            
            # 1. Enqueue scheduled tasks that are due
            for task_id, next_run in list(self.next_run_times.items()):
                if next_run <= now:
                    await self._enqueue_task(task_id, is_scheduled=True)

            # 2. Enqueue manually triggered tasks
            triggered_tasks = await self._check_for_triggers()
            for task_id in triggered_tasks:
                await self._enqueue_task(task_id, is_scheduled=False)
            
            # 3. Execute tasks from priority queue
            await self._execute_from_priority_queue()
                    
        except Exception as e:
            self.logger.error(f"Error in task check and execute: {e}")
    
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
                self.logger.error(f"Task class not found for {task_id}")
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
                return
            if hasattr(self, "priority_queue") and self.priority_queue and self.priority_queue.has_task(task_id):
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
                self.logger.warning(f"Failed to enqueue {task_id} - queue full")
                
        except Exception as e:
            self.logger.error(f"Error enqueuing task {task_id}: {e}")
    
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
                self.logger.error(f"Task class not found for {prioritized_task.task_id}")
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
