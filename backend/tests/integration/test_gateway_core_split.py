import pytest

from aico.core.config import ConfigurationManager
from aico.ai import ai_registry

from backend.core.lifecycle_manager import BackendLifecycleManager


@pytest.mark.asyncio
async def test_gateway_role_does_not_register_core_services_or_ai_processors():
    # Ensure a clean registry for this test
    ai_registry.unregister("memory")
    ai_registry.unregister("agency")

    cfg = ConfigurationManager()
    cfg.initialize(lightweight=True)

    lifecycle = BackendLifecycleManager(cfg, role="gateway")
    await lifecycle._initialize_container()

    registered = set(getattr(lifecycle.container, "_definitions", {}).keys())
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


def test_backend_lifecycle_manager_rejects_monolith_role():
    cfg = ConfigurationManager()
    cfg.initialize(lightweight=True)

    with pytest.raises(ValueError):
        BackendLifecycleManager(cfg, role="monolith")
