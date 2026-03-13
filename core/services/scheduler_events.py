from aico.core.logging import get_logger

logger = get_logger("core.services.scheduler_events")


async def broadcast_scheduler_event(event: dict) -> None:
    logger.debug("Scheduler event broadcast requested", extra={"event_type": event.get("type")})
