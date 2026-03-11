import asyncio
from typing import Any, Optional

from aico.common.service_container import ServiceContainer
from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger


class CoreLifecycleManager:
    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        self.logger = get_logger("core.core_lifecycle")
        self.container: ServiceContainer = ServiceContainer(config_manager)
        self._handlers_started = False
        self._message_bus = None

    async def startup(self) -> None:
        from aico.common.postgres_dependencies import initialize_postgres_dependencies

        await initialize_postgres_dependencies()

        await self._initialize_container()
        await self.container.start_all()
        await self._initialize_nats_handlers()

        self.logger.info("Core startup complete (NATS-only)")

    async def stop(self) -> None:
        try:
            if self._message_bus is not None:
                try:
                    await self._message_bus.disconnect()
                except Exception:
                    pass
                self._message_bus = None
        finally:
            await self.container.stop_all()

    async def _initialize_container(self) -> None:
        await self._register_core_services()
        await self._register_ai_processors()

    async def _register_core_services(self) -> None:
        def create_config_service(container: ServiceContainer):
            return container.config

        def create_database_connection(_container: ServiceContainer) -> Any:
            return None

        self.container.register_service(
            "config",
            create_config_service,
            dependencies=[],
            priority=1,
        )

        self.container.register_service(
            "database",
            create_database_connection,
            dependencies=[],
            priority=5,
        )

        def create_outbox_publisher(_container: ServiceContainer):
            from core.services.outbox_publisher import OutboxPublisherService

            return OutboxPublisherService("outbox_publisher", _container)

        self.container.register_service(
            "outbox_publisher",
            create_outbox_publisher,
            dependencies=[],
            priority=25,
        )

        def create_task_scheduler(container: ServiceContainer):
            from core.services.scheduler import TaskScheduler

            return TaskScheduler("task_scheduler", container)

        self.container.register_service(
            "task_scheduler",
            create_task_scheduler,
            dependencies=[],
            priority=25,
        )

        def create_scheduler_worker(container: ServiceContainer):
            from core.services.scheduler_worker import SchedulerWorkerService

            return SchedulerWorkerService("scheduler_worker", container)

        self.container.register_service(
            "scheduler_worker",
            create_scheduler_worker,
            dependencies=[],
            priority=26,
        )

        def create_emotion_engine(container: ServiceContainer):
            from core.services.emotion_engine import EmotionEngine

            return EmotionEngine("emotion_engine", container)

        self.container.register_service(
            "emotion_engine",
            create_emotion_engine,
            dependencies=[],
            priority=30,
        )

        def create_conversation_engine(container: ServiceContainer, emotion_engine=None):
            from core.services.conversation_engine import ConversationEngine

            return ConversationEngine("conversation_engine", container)

        self.container.register_service(
            "conversation_engine",
            create_conversation_engine,
            dependencies=["emotion_engine"],
            priority=35,
        )

        def create_uow_factory(_container: ServiceContainer):
            from aico.common.postgres_dependencies import get_uow_factory

            return get_uow_factory()

        self.container.register_service(
            "uow",
            create_uow_factory,
            dependencies=[],
            priority=10,
        )

    async def _register_ai_processors(self) -> None:
        from aico.ai import ai_registry
        from aico.ai.agency import bootstrap as agency_bootstrap
        from aico.ai.agency import AgencyEngine
        from aico.ai.memory.manager import MemoryManager
        from core.services.modelservice_client import get_modelservice_client

        from aico.common.postgres_dependencies import get_uow_factory

        uow_factory = get_uow_factory()

        memory_manager = MemoryManager(self.config, uow_factory=uow_factory)
        try:
            modelservice_client = get_modelservice_client(self.config)
            memory_manager.set_modelservice(modelservice_client)
        except Exception:
            pass

        await memory_manager.initialize()
        ai_registry.register("memory", memory_manager)

        try:
            await agency_bootstrap.initialize()
        except Exception:
            pass

        message_bus_client = None
        try:
            from aico.core.bus import MessageBusClient

            message_bus_client = MessageBusClient("agency_engine", config_manager=self.config)
            await message_bus_client.connect()
        except Exception:
            message_bus_client = None

        # AgencyEngine requires an AgencyService implementation.
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.services.agency_service import AgencyService

        session_factory = await get_session_factory()

        class AgencyServiceProxy:
            def __init__(self, session_factory):
                self._session_factory = session_factory

            async def _execute(self, method_name: str, *args, **kwargs):
                async with UnitOfWork(self._session_factory) as uow:
                    svc = AgencyService(uow)
                    method = getattr(svc, method_name)
                    result = await method(*args, **kwargs)
                    await uow.commit()
                    return result

            async def create_goal(self, goal):
                return await self._execute("create_goal", goal)

            async def get_goal(self, goal_id):
                return await self._execute("get_goal", goal_id)

            async def update_goal(self, goal):
                return await self._execute("update_goal", goal)

            async def list_goals(self, user_id=None, status=None):
                return await self._execute("list_goals", user_id=user_id, status=status)

            async def get_active_goals(self, user_id):
                return await self._execute("get_active_goals", user_id)

            async def get_goals_bulk(self, goal_ids):
                return await self._execute("get_goals_bulk", goal_ids)

            async def create_plan(self, plan):
                return await self._execute("create_plan", plan)

            async def get_plan(self, plan_id):
                return await self._execute("get_plan", plan_id)

            async def list_plans(self, goal_id: str, status=None):
                return await self._execute("list_plans", goal_id=goal_id, status=status)

            async def update_plan(self, plan):
                return await self._execute("update_plan", plan)

        agency_service = AgencyServiceProxy(session_factory)

        agency_engine = AgencyEngine(
            config=self.config,
            agency_service=agency_service,
            message_bus=message_bus_client,
            memory_manager=memory_manager,
            session_factory=session_factory,
        )
        ai_registry.register("agency", agency_engine)

    async def _initialize_nats_handlers(self) -> None:
        if self._handlers_started:
            return

        from aico.core.bus import MessageBusClient
        from core.handlers.nats_handlers import CoreNATSHandlers

        message_bus = MessageBusClient("core_request_handler")
        await message_bus.connect()

        handlers = CoreNATSHandlers(self.container)
        await handlers.setup_handlers(message_bus)

        self._handlers_started = True
        self._message_bus = message_bus
