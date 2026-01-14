"""
Integration tests for SystemEventMetricsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.system.metrics_models import SystemEventMetric
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


@pytest.fixture
async def session_factory():
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow


class TestSystemEventMetricsRepository:
    
    @pytest.mark.asyncio
    async def test_create_metric(self, uow):
        metric = SystemEventMetric(
            metric_id=str(uuid.uuid4()),
            metric_name="test_counter",
            metric_type="counter",
            time_bucket="hourly",
            bucket_start="2026-01-14T10:00:00Z",
            value=100.0,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.system_event_metrics.create(metric)
        await uow.commit()
        
        assert created.metric_id == metric.metric_id
        assert created.metric_name == "test_counter"
    
    @pytest.mark.asyncio
    async def test_get_metric_by_id(self, uow):
        metric = SystemEventMetric(
            metric_id=str(uuid.uuid4()),
            metric_name="test_gauge",
            metric_type="gauge",
            time_bucket="daily",
            bucket_start="2026-01-14T00:00:00Z",
            value=50.0,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.system_event_metrics.create(metric)
        await uow.commit()
        
        found = await uow.system_event_metrics.get_by_id(metric.metric_id)
        assert found is not None
        assert found.metric_type == "gauge"
    
    @pytest.mark.asyncio
    async def test_update_metric(self, uow):
        metric = SystemEventMetric(
            metric_id=str(uuid.uuid4()),
            metric_name="test_histogram",
            metric_type="histogram",
            time_bucket="hourly",
            bucket_start="2026-01-14T10:00:00Z",
            value=10.0,
            count=1,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.system_event_metrics.create(metric)
        await uow.commit()
        
        metric.value = 20.0
        metric.count = 2
        updated = await uow.system_event_metrics.update(metric)
        await uow.commit()
        
        assert updated.value == 20.0
        
        found = await uow.system_event_metrics.get_by_id(metric.metric_id)
        assert found.count == 2
    
    @pytest.mark.asyncio
    async def test_delete_metric(self, uow):
        metric = SystemEventMetric(
            metric_id=str(uuid.uuid4()),
            metric_name="test_delete",
            metric_type="counter",
            time_bucket="hourly",
            bucket_start="2026-01-14T10:00:00Z",
            value=5.0,
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.system_event_metrics.create(metric)
        await uow.commit()
        
        success = await uow.system_event_metrics.delete(metric.metric_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.system_event_metrics.get_by_id(metric.metric_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_metrics(self, uow):
        for i in range(3):
            metric = SystemEventMetric(
                metric_id=str(uuid.uuid4()),
                metric_name=f"test_list_{i}",
                metric_type="counter",
                time_bucket="hourly",
                bucket_start="2026-01-14T10:00:00Z",
                value=float(i),
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.system_event_metrics.create(metric)
        
        await uow.commit()
        
        all_metrics = await uow.system_event_metrics.list()
        assert len(all_metrics) >= 3
    
    @pytest.mark.asyncio
    async def test_count_metrics(self, uow):
        for i in range(3):
            metric = SystemEventMetric(
                metric_id=str(uuid.uuid4()),
                metric_name=f"test_count_{i}",
                metric_type="counter",
                time_bucket="hourly",
                bucket_start="2026-01-14T10:00:00Z",
                value=float(i),
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.system_event_metrics.create(metric)
        
        await uow.commit()
        
        count = await uow.system_event_metrics.count()
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_metrics_by_bucket(self, uow):
        bucket_start = "2026-01-14T11:00:00Z"
        for i in range(3):
            metric = SystemEventMetric(
                metric_id=str(uuid.uuid4()),
                metric_name=f"test_bucket_{i}",
                metric_type="counter",
                time_bucket="hourly",
                bucket_start=bucket_start,
                value=float(i),
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.system_event_metrics.create(metric)
        
        await uow.commit()
        
        metrics = await uow.system_event_metrics.get_metrics_by_bucket("hourly", bucket_start)
        assert len(metrics) >= 3
        for m in metrics:
            assert m.time_bucket == "hourly"
            assert m.bucket_start == bucket_start
