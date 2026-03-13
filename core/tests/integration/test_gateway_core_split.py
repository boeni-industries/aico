import pytest

from aico.core.config import ConfigurationManager
from aico.ai import ai_registry

from gateway.core.gateway_core import GatewayCore


@pytest.mark.asyncio
async def test_gateway_role_does_not_register_core_services_or_ai_processors():
    # Ensure a clean registry for this test
    ai_registry.unregister("memory")
    ai_registry.unregister("agency")

    cfg = ConfigurationManager()
    cfg.initialize(lightweight=True)

    gateway = GatewayCore(cfg)
    # Start only far enough to register services; avoid binding ports.
    await gateway._register_core_services()
    registered = set(getattr(gateway.service_container, "_definitions", {}).keys())
    forbidden = {
        "task_scheduler",
        "scheduler_worker",
        "emotion_engine",
        "conversation_engine",
        "outbox_publisher",
    }
    assert forbidden.intersection(registered) == set()

    assert ai_registry.get("memory") is None
    assert ai_registry.get("agency") is None
