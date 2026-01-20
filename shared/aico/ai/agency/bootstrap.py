from __future__ import annotations

"""Agency bootstrap utilities.

This module centralizes initialization for agency-related registries
(skills, tools, etc.) so that multiple backend processes (API, scheduler,
workers) can share a consistent set of registered capabilities.

Import this module and call ``initialize()`` early in process startup to
ensure all core tools/skills are registered in the local registries.
"""

from typing import NoReturn

from aico.core.logging import get_logger


logger = get_logger("shared.ai.agency.bootstrap")


async def initialize() -> None:
    """Initialize agency registries for the current process.

    Currently this ensures that core connectivity tools are registered in
    the ToolRegistry by importing their module, which performs
    registration via import-time side effects.
    """

    try:
        # Import connectivity tools so they self-register in ToolRegistry.
        # The import is idempotent and safe to call multiple times.
        import aico.ai.agency.tools.connectivity  # noqa: F401
        logger.debug("[AGENCY_BOOTSTRAP] Connectivity tools initialized")
    except Exception as exc:  # pragma: no cover - defensive safeguard
        logger.warning(
            "[AGENCY_BOOTSTRAP] Failed to initialize connectivity tools: %s",
            exc,
        )

    try:
        # Import agency maintenance tools (execution cleanup) so they register
        # in the ToolRegistry at process startup.
        import aico.ai.agency.tools.agency_cleanup  # noqa: F401
        logger.debug("[AGENCY_BOOTSTRAP] Agency cleanup tools initialized")
    except Exception as exc:  # pragma: no cover - defensive safeguard
        logger.warning(
            "[AGENCY_BOOTSTRAP] Failed to initialize agency cleanup tools: %s",
            exc,
        )
