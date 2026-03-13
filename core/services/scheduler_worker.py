from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from aico.core.bus import MessageBusClient
from aico.core.jetstream import JetStreamManager, JetStreamStreamSpec, JetStreamConsumerSpec

from aico.common.service_container import BaseService


@dataclass
class SchedulerWorkerConfig:
    stream_name: str = "SCHEDULER_JOBS"
    subject_filter: str = "scheduler.jobs.*"
    consumer_durable: str = "scheduler_worker"
    poll_batch: int = 10
    poll_timeout_seconds: float = 1.0
    idle_sleep_seconds: float = 0.2


class SchedulerWorkerService(BaseService):
    def __init__(self, name: str, container, config: SchedulerWorkerConfig | None = None):
        super().__init__(name, container)
        self._config = config or SchedulerWorkerConfig()
        self._bus: MessageBusClient | None = None
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def initialize(self) -> None:
        return

    async def start(self) -> None:
        if self._task and not self._task.done():
            return

        self._stop.clear()
        self._bus = MessageBusClient("scheduler_worker")
        await self._bus.connect()

        js = JetStreamManager(self._bus._nats)
        await js.ensure_stream(
            JetStreamStreamSpec(
                name=self._config.stream_name,
                subjects=[self._config.subject_filter],
            )
        )
        await js.ensure_consumer(
            JetStreamConsumerSpec(
                stream=self._config.stream_name,
                durable_name=self._config.consumer_durable,
                filter_subject=self._config.subject_filter,
            )
        )

        self._task = asyncio.create_task(self._run_loop())
        self.logger.info("Scheduler worker started")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except Exception:
                pass
        if self._bus:
            await self._bus.disconnect()
            self._bus = None
        self.logger.info("Scheduler worker stopped")

    async def _run_loop(self) -> None:
        assert self._bus and self._bus._nats
        js = self._bus._nats.jetstream()

        sub = await js.pull_subscribe(
            self._config.subject_filter,
            durable=self._config.consumer_durable,
            stream=self._config.stream_name,
        )

        while not self._stop.is_set():
            try:
                msgs = await sub.fetch(self._config.poll_batch, timeout=self._config.poll_timeout_seconds)
            except asyncio.TimeoutError:
                await asyncio.sleep(self._config.idle_sleep_seconds)
                continue
            except Exception as e:
                self.logger.error(f"JetStream fetch failed: {e}")
                await asyncio.sleep(1.0)
                continue

            for msg in msgs:
                try:
                    payload = json.loads(msg.data.decode("utf-8"))
                    task_id = payload["task_id"]
                    task_config = payload["task_config"]
                    run_key = payload.get("run_key")
                    scheduled_for = payload.get("scheduled_for")

                    scheduler = self.container.get_service("task_scheduler")
                    if scheduler is None:
                        self.logger.warning("Scheduler worker could not find task_scheduler service; nacking message")
                        await msg.nak()
                        continue

                    task_class = scheduler.task_registry.get_task_class(task_id)
                    if task_class is None:
                        self.logger.warning(
                            f"Scheduler worker dropping job with unknown task class: "
                            f"task_id={task_id}, run_key={run_key}, scheduled_for={scheduled_for}"
                        )
                        await msg.ack()
                        continue

                    self.logger.info(
                        f"Scheduler worker executing job: task_id={task_id}, "
                        f"run_key={run_key}, scheduled_for={scheduled_for}"
                    )
                    result = await scheduler.task_executor.execute_task(task_class, task_config, run_key=run_key)
                    self.logger.info(
                        f"Scheduler worker completed job: task_id={task_id}, run_key={run_key}, "
                        f"success={result.success}, skipped={result.skipped}, message={result.message}"
                    )
                    await msg.ack()

                except Exception as e:
                    self.logger.error(f"Failed to process scheduler job: {e}")
                    try:
                        await msg.nak()
                    except Exception:
                        pass
