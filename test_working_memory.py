#!/usr/bin/env python3
import asyncio
from aico.core.config import ConfigurationManager
from aico.data.uow import UnitOfWork
from sqlalchemy import select, func, or_
from aico.data.tables import working_memory_messages
from datetime import datetime, UTC

async def check_working_memory():
    config = ConfigurationManager()
    uow = UnitOfWork(config)
    await uow.__aenter__()
    
    try:
        # Count total messages
        count_stmt = select(func.count()).select_from(working_memory_messages)
        total = (await uow._session.execute(count_stmt)).scalar() or 0
        print(f'Total working memory messages: {total}')
        
        # Count active (non-expired) messages
        now = datetime.now(UTC)
        active_stmt = select(func.count()).select_from(working_memory_messages).where(
            or_(working_memory_messages.c.expires_at.is_(None), working_memory_messages.c.expires_at > now)
        )
        active = (await uow._session.execute(active_stmt)).scalar() or 0
        print(f'Active (non-expired) messages: {active}')
        
        # Get sample messages
        sample_stmt = select(working_memory_messages).order_by(working_memory_messages.c.stored_at.desc()).limit(5)
        result = await uow._session.execute(sample_stmt)
        rows = result.fetchall()
        
        print(f'\nMost recent messages:')
        for row in rows:
            m = row._mapping
            content = m['content'][:50] if m['content'] else '(empty)'
            print(f'  - {m["role"]}: {content}...')
            print(f'    conversation_id: {m["conversation_id"]}')
            print(f'    stored_at: {m["stored_at"]}')
            print(f'    expires_at: {m["expires_at"]}')
            print()
    finally:
        await uow.__aexit__(None, None, None)

if __name__ == "__main__":
    asyncio.run(check_working_memory())
