import pytest

from aico.core.jetstream import JetStreamConsumerSpec, JetStreamManager


class _FakeJS:
    def __init__(self):
        self.added = []

    async def consumer_info(self, stream, durable):
        raise Exception("missing")

    async def add_consumer(self, stream, cfg):
        self.added.append((stream, cfg))


class _FakeNATS:
    def __init__(self, js):
        self._js = js

    def jetstream(self):
        return self._js


@pytest.mark.asyncio
async def test_ensure_consumer_converts_ack_wait_seconds_to_nanoseconds():
    js = _FakeJS()
    nc = _FakeNATS(js)
    mgr = JetStreamManager(nc)

    spec = JetStreamConsumerSpec(
        stream="SCHEDULER_JOBS",
        durable_name="worker",
        filter_subject="scheduler.jobs.*",
        ack_wait_seconds=12,
        max_deliver=5,
    )

    await mgr.ensure_consumer(spec)

    assert len(js.added) == 1
    stream, cfg = js.added[0]
    assert stream == "SCHEDULER_JOBS"
    assert cfg.ack_wait == 12
