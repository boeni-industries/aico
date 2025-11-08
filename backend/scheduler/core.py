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
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Type
from pathlib import Path

from aico.core.logging import get_logger
from backend.core.service_container import BaseService
from .tasks.base import BaseTask, TaskContext, TaskResult, TaskStatus
from .storage import TaskStore
from .cron import CronParser


class TaskRegistry:
    """Registry for discovering and managing task classes"""
    
    def __init__(self, config_manager, db_connection):
        self.config_manager = config_manager
        self.db_connection = db_connection
        self.logger = get_logger("backend", "scheduler.task_registry")
        self.tasks: Dict[str, Type[BaseTask]] = {}
        self.task_store = TaskStore(db_connection)
    
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
            "backend.scheduler.tasks.lmdb_cleanup"  # LMDB cleanup
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
            # Get user tasks from database
            db_tasks = self.task_store.list_tasks()
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
        for task_id, task_class in self.tasks.items():
            if not task_id.startswith('user.'):
                # Get default config from task class
                default_config = task_class().get_default_config()
                schedule = default_config.get('schedule', '0 3 * * *')  # Default: daily at 3 AM
                enabled = default_config.get('enabled', True)
                
                # Upsert task in database
                self.task_store.upsert_task(
                    task_id=task_id,
                    task_class=task_class.__name__,
                    schedule=schedule,
                    config=default_config,
                    enabled=enabled
                )


class TaskExecutor:
    """Executes tasks with resource management and error handling"""
    
    def __init__(self, config_manager, db_connection):
        self.config_manager = config_manager
        self.db_connection = db_connection
        self.logger = get_logger("backend", "scheduler.task_executor")
        self.task_store = TaskStore(db_connection)
        self.running_tasks: Dict[str, asyncio.Task] = {}
    
    async def execute_task(self, task_class: Type[BaseTask], task_config: Dict[str, Any]) -> TaskResult:
        """Execute a single task with full lifecycle management"""
        task_id = task_config['task_id']
        execution_id = str(uuid.uuid4())
        
        # Print to console if in foreground mode for immediate visibility
        if os.getenv('AICO_DETACH_MODE') == 'false':
            print(f"[SCHEDULER] Executing task: {task_id}")
        
        self.logger.info(f"Starting execution of task {task_id} (execution_id: {execution_id})")
        
        # Check if task is already running
        if task_id in self.running_tasks:
            self.logger.warning(f"Task {task_id} is already running, skipping")
            return TaskResult(success=False, message="Task already running", skipped=True)
        
        # Acquire execution lock
        lock_acquired = self.task_store.acquire_lock(task_id, execution_id)
        if not lock_acquired:
            self.logger.warning(f"Could not acquire lock for task {task_id}")
            return TaskResult(success=False, message="Could not acquire execution lock", skipped=True)

        # Add to running tasks *after* acquiring lock
        self.running_tasks[task_id] = asyncio.current_task()

        start_time = datetime.now()
        task_instance = None

        try:
            # Record execution start
            self.task_store.record_execution_start(task_id, execution_id)
            
            # Create task instance and context
            task_instance = task_class()
            context = TaskContext(
                task_id=task_id,
                config_manager=self.config_manager,
                db_connection=self.db_connection,
                instance_config=task_config.get('config', {}),
                execution_id=execution_id
            )
            
            # Apply task defaults to context for config resolution
            context.task_defaults = task_instance.get_default_config()
            
            # Check resource constraints
            if not await self._check_resource_constraints(context):
                result = TaskResult(success=False, message="Resource constraints not met", skipped=True)
                await self._record_completion(task_id, execution_id, result, TaskStatus.SKIPPED, start_time)
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
            
            self.logger.info(f"Task {task_id} completed: {result.message}")
            return result
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            result = TaskResult(success=False, error=error_msg)
            await self._record_completion(task_id, execution_id, result, TaskStatus.FAILED, start_time)
            
            self.logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            return result
            
        finally:
            # Cleanup
            if task_instance:
                try:
                    await task_instance.cleanup()
                except Exception as e:
                    self.logger.warning(f"Task cleanup failed for {task_id}: {e}")
            
            # Release lock
            self.task_store.release_lock(task_id, execution_id)

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
            scheduler_config = self.get_config("scheduler", {})
            max_cpu = scheduler_config.get("max_cpu_percent", 80)
            max_memory = scheduler_config.get("max_memory_percent", 80)
            
            # TODO: Implement actual resource checking
            # For now, always allow execution
            return True
            
        except Exception as e:
            self.logger.warning(f"Resource check failed: {e}")
            return True  # Allow execution on check failure
    
    async def _record_completion(self, task_id: str, execution_id: str, result: TaskResult, 
                               status: TaskStatus, start_time: datetime):
        """Record task completion in database"""
        try:
            end_time = datetime.now()
            result.duration_seconds = (end_time - start_time).total_seconds()
            
            self.task_store.record_execution_result(task_id, execution_id, result, status)
            
        except Exception as e:
            self.logger.error(f"Failed to record completion for {task_id}: {e}")
    
    def get_running_tasks(self) -> List[str]:
        """Get list of currently running task IDs"""
        return list(self.running_tasks.keys())


class TaskScheduler(BaseService):
    """Main scheduler that coordinates task discovery, scheduling, and execution"""
    
    def __init__(self, name: str, container):
        super().__init__(name, container)
        
        # Core components
        self.task_registry = None
        self.task_executor = None
        self.task_store = None
        self.cron_parser = CronParser()
        
        # Runtime state
        self.running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        self.next_run_times: Dict[str, datetime] = {}
    
    async def initialize(self) -> None:
        """Initialize scheduler components"""
        database = self.require_service("database")
        config_manager = self.container.config
        
        # Initialize core components
        self.task_registry = TaskRegistry(config_manager, database)
        self.task_executor = TaskExecutor(config_manager, database)
        self.task_store = TaskStore(database)
        
        # Verify database tables exist
        self.task_store.verify_tables_exist()
        
        self.logger.info("Task scheduler initialized")
    
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
        """Check for tasks that need to run and execute them"""
        try:
            now = datetime.now()
            tasks_to_run: Set[str] = set()

            # 1. Check for scheduled tasks
            for task_id, next_run in self.next_run_times.items():
                if next_run <= now:
                    tasks_to_run.add(task_id)

            # 2. Check for manually triggered tasks
            triggered_tasks = await self._check_for_triggers()
            for task_id in triggered_tasks:
                tasks_to_run.add(task_id)
            
            if not tasks_to_run:
                return
            
            # Get task configurations from database
            for task_id in list(tasks_to_run):  # Iterate over a copy
                try:
                    task_config = self.task_store.get_task(task_id)
                    # For scheduled tasks, check if enabled. For triggered tasks, run regardless of enabled status.
                    is_scheduled = task_id in self.next_run_times
                    if not task_config or (is_scheduled and not task_config.get('enabled', True)):
                        continue
                    
                    task_class = self.task_registry.get_task_class(task_id)
                    if not task_class:
                        self.logger.error(f"Task class not found for {task_id}")
                        continue
                    
                    # Execute task asynchronously
                    asyncio.create_task(self.task_executor.execute_task(task_class, task_config))
                    
                    # For scheduled tasks, calculate next run time
                    if is_scheduled:
                        next_run = self.cron_parser.next_run_time(task_config['schedule'], now)
                        if next_run:
                            self.next_run_times[task_id] = next_run
                            self.logger.debug(f"Next run for {task_id}: {next_run}")
                        else:
                            # This can happen if the cron is a one-off that has passed
                            self.logger.warning(f"Could not calculate next run time for {task_id}")
                
                except Exception as e:
                    self.logger.error(f"Error processing task {task_id}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error in task check cycle: {e}")
    
    async def _calculate_next_run_times(self):
        """Calculate next run times for all enabled tasks"""
        try:
            tasks = self.task_store.list_tasks(enabled_only=True)
            now = datetime.now()
            
            for task in tasks:
                task_id = task['task_id']
                schedule = task['schedule']
                
                next_run = self.cron_parser.next_run_time(schedule, now)
                if next_run:
                    self.next_run_times[task_id] = next_run
                    self.logger.debug(f"Next run for {task_id}: {next_run}")
                else:
                    self.logger.error(f"Invalid schedule for task {task_id}: {schedule}")
            
            self.logger.info(f"Calculated next run times for {len(self.next_run_times)} tasks")
            
        except Exception as e:
            self.logger.error(f"Failed to calculate next run times: {e}")
    
    async def trigger_task(self, task_id: str) -> TaskResult:
        """Manually trigger a task execution"""
        try:
            task_config = self.task_store.get_task(task_id)
            if not task_config:
                return TaskResult(success=False, error=f"Task not found: {task_id}")
            
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
