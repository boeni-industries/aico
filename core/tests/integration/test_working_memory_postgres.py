import pytest

from aico.data.uow import UnitOfWork
from aico.core.config import ConfigurationManager

from aico.ai.memory.working_postgres import PostgresWorkingMemoryStore


@pytest.mark.asyncio
async def test_postgres_working_memory_store_store_and_retrieve(session_factory):
    config = ConfigurationManager()
    config.initialize(lightweight=True)

    def uow_factory():
        return UnitOfWork(session_factory)

    store = PostgresWorkingMemoryStore(config, uow_factory=uow_factory)
    await store.initialize()

    conv_id = "conv-1"
    await store.store_message(conv_id, {"user_id": "u1", "content": "hello", "role": "user"})
    await store.store_message(conv_id, {"user_id": "u1", "content": "hi", "role": "assistant"})

    history = await store.retrieve_conversation_history(conv_id, limit=10)
    assert len(history) == 2
    assert {h.get("content") for h in history} == {"hello", "hi"}

    user_history = await store.retrieve_user_history("u1", limit=10)
    assert len(user_history) >= 2


@pytest.mark.asyncio
async def test_postgres_working_memory_store_cleanup_expired(session_factory):
    config = ConfigurationManager()
    config.initialize(lightweight=True)

    def uow_factory():
        return UnitOfWork(session_factory)

    store = PostgresWorkingMemoryStore(config, uow_factory=uow_factory)
    store._ttl_seconds = 0
    await store.initialize()

    await store.store_message("conv-exp", {"user_id": "u-exp", "content": "x"})
    deleted = await store.cleanup_expired()

    assert deleted >= 1
