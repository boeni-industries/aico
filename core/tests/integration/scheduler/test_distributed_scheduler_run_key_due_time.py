import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from core.services.scheduler.core import TaskScheduler
from core.services.scheduler.tasks.base import BaseTask, TaskResult


class _DistributedRunKeyTask(BaseTask):
    task_id = "test.distributed_run_key_due_time"

    async def execute(self, context):
        return TaskResult(success=True, message="ok")


@pytest.mark.asyncio
async def test_distributed_scheduler_run_key_uses_due_time_not_advanced_next_run(monkeypatch):
    due_run_at = datetime(2030, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    advanced_next_run_at = datetime(2030, 1, 2, 12, 0, 0, tzinfo=timezone.utc)

    published = {}

    class _FakeJetStreamManager:
        def __init__(self, nats_client):
            self._nats_client = nats_client

        async def ensure_stream(self, spec):
            return

        async def publish(self, subject: str, payload: bytes, *, headers=None):
            published["subject"] = subject
            published["payload"] = payload
            published["headers"] = headers

    import aico.core.jetstream as jetstream_mod
    import aico.data.postgres.connection as pg_connection_mod
    import aico.data.uow as uow_mod
    import aico.services.scheduler_service as scheduler_service_mod

    monkeypatch.setattr(jetstream_mod, "JetStreamManager", _FakeJetStreamManager)

    class _Cfg:
        def get(self, key, default=None):
            if key == "scheduler":
                return {
                    "distributed": {
                        "enabled": True,
                        "stream_name": "SCHEDULER_JOBS",
                        "subject_filter": "scheduler.jobs.*",
                        "publish_subject": "scheduler.jobs.run",
                    }
                }
            return default

    container = SimpleNamespace(config=_Cfg())
    container.get_service = lambda name: None

    scheduler = TaskScheduler("test_scheduler", container)
    await scheduler.initialize()

    # Register the task class so _enqueue_task can resolve it.
    scheduler.task_registry.tasks[_DistributedRunKeyTask.task_id] = _DistributedRunKeyTask

    # Set due run time (this is what should be used for run_key and scheduled_for)
    scheduler.next_run_times[_DistributedRunKeyTask.task_id] = due_run_at

    # Force the next_run advancement codepath to run and change next_run_times,
    # to ensure we don't accidentally build run_key from the advanced value.
    scheduler.cron_parser.next_run_time = lambda *_args, **_kwargs: advanced_next_run_at

    # Provide a fake bus client so distributed publishing can proceed.
    scheduler._bus_client = SimpleNamespace(_nats=object())

    async def _fake_get_task(task_id: str):
        assert task_id == _DistributedRunKeyTask.task_id
        return SimpleNamespace(
            task_id=task_id,
            task_class=_DistributedRunKeyTask.__name__,
            schedule="0 3 * * *",
            config=json.dumps({"task_id": task_id, "queue": "default"}),
            enabled=True,
        )

    class _FakeSchedulerService:
        def __init__(self, uow):
            self._uow = uow

        async def get_task(self, task_id: str):
            return await _fake_get_task(task_id)

    class _FakeUnitOfWork:
        def __init__(self, session_factory):
            self._session_factory = session_factory

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def _fake_get_session_factory():
        async def _sf():
            return None

        return _sf

    monkeypatch.setattr(pg_connection_mod, "get_session_factory", _fake_get_session_factory)
    monkeypatch.setattr(uow_mod, "UnitOfWork", _FakeUnitOfWork)
    monkeypatch.setattr(scheduler_service_mod, "SchedulerService", _FakeSchedulerService)

    await scheduler._enqueue_task(_DistributedRunKeyTask.task_id, is_scheduled=True)

    assert published["subject"] == "scheduler.jobs.run"

    job = json.loads(published["payload"].decode("utf-8"))
    assert job["task_id"] == _DistributedRunKeyTask.task_id
    assert job["scheduled_for"] == due_run_at.isoformat()

    # The run_key must be derived from the due time, not the advanced next run.
    assert due_run_at.isoformat() in job["run_key"]
    assert advanced_next_run_at.isoformat() not in job["run_key"]
