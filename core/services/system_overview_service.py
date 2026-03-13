import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select

from aico.core.logging import get_logger
from aico.data.tables import system_events
from aico.data.tables import agency_goals, working_memory_messages
from aico.data.uow import UnitOfWork
from core.services.runtime_info import format_uptime, start_time

logger = get_logger("core.services.system_overview_service")


async def get_system_overview(*, user_id: str, uow: UnitOfWork) -> dict:
    uptime_seconds = time.time() - start_time
    uptime_formatted = format_uptime(uptime_seconds)

    active_conversations = 0
    try:
        cutoff_time = datetime.now(UTC) - timedelta(days=1)
        stmt = (
            select(func.count(func.distinct(working_memory_messages.c.conversation_id)))
            .where(
                working_memory_messages.c.stored_at >= cutoff_time,
                or_(working_memory_messages.c.expires_at.is_(None), working_memory_messages.c.expires_at > datetime.now(UTC)),
            )
        )
        result = await uow._session.execute(stmt)
        active_conversations = int(result.scalar() or 0)
    except Exception as e:
        logger.debug(f"Conversation count unavailable: {e}")

    active_goals = 0
    try:
        count_query = select(func.count()).select_from(agency_goals).where(
            agency_goals.c.user_id == user_id,
            agency_goals.c.status.in_(["active", "in_progress"]),
        )
        result = await uow._session.execute(count_query)
        active_goals = int(result.scalar() or 0)
    except Exception as e:
        logger.debug(f"Goals count unavailable: {e}")

    recent_events: list[dict] = []
    try:
        events_stmt = (
            select(system_events)
            .order_by(system_events.c.created_at.desc())
            .limit(10)
        )
        event_rows = (await uow._session.execute(events_stmt)).fetchall()

        def _event_domain(topic: str | None) -> str:
            topic_str = str(topic or "").lower()
            if topic_str.startswith("auth."):
                return "security"
            if topic_str.startswith("audit."):
                return "admin"
            if topic_str.startswith("security."):
                return "security"
            if topic_str.startswith("scheduler.") or topic_str.startswith("agency."):
                return "agency"
            if topic_str.startswith("memory.") or topic_str.startswith("kg."):
                return "memory"
            if topic_str.startswith("system.") or topic_str.startswith("health."):
                return "system"
            return topic_str.split(".", 1)[0] or "system"

        for row in event_rows:
            event = row[0] if len(row) == 1 else row
            metadata = getattr(event, "metadata", None)
            topic = getattr(event, "topic", None)
            description = ""
            if isinstance(metadata, dict):
                description = str(
                    metadata.get("description")
                    or metadata.get("message")
                    or metadata.get("detail")
                    or ""
                )
            recent_events.append(
                {
                    "timestamp": (
                        event_timestamp.isoformat()
                        if hasattr((event_timestamp := getattr(event, "timestamp", None)), "isoformat")
                        else event_timestamp
                    ),
                    "severity": (
                        metadata.get("severity")
                        if isinstance(metadata, dict)
                        else None
                    ) or "info",
                    "title": str(
                        (metadata.get("title") if isinstance(metadata, dict) else None)
                        or topic
                        or "system.event"
                    ),
                    "description": description,
                    "domain": _event_domain(topic),
                    "count": int((metadata.get("count") if isinstance(metadata, dict) else None) or 1),
                }
            )
    except Exception as e:
        logger.debug(f"Recent system events unavailable: {e}")

    error_count = sum(1 for event in recent_events if event.get("severity") == "error")
    if error_count >= 3:
        system_status = "degraded"
    elif error_count > 0:
        system_status = "attention"
    else:
        system_status = "ok"

    return {
        "uptime_seconds": uptime_seconds,
        "uptime_formatted": uptime_formatted,
        "active_conversations": active_conversations,
        "active_goals": active_goals,
        "system_status": system_status,
        "recent_events": recent_events,
    }
