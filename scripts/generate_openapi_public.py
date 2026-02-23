from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable

from fastapi import FastAPI


EXCLUDED_PATH_PREFIXES: tuple[str, ...] = (
    "/api/v1/admin",
    "/api/v1/system",
    "/api/v1/operations",
    "/api/v1/users-sessions",
)


def _build_public_app() -> FastAPI:
    from aico.core.version import get_backend_version
    from aico.core.config import ConfigurationManager

    repo_root = Path(__file__).resolve().parents[1]
    repo_config_dir = repo_root / "config"
    os.environ.setdefault("AICO_CONFIG_DIR", str(repo_config_dir))
    ConfigurationManager(config_dir=repo_config_dir).initialize(lightweight=True)

    app = FastAPI(
        title="AICO Backend API",
        version=get_backend_version(),
        description="AICO Backend REST API with clean architecture",
    )

    from backend.api.health.router import router as health_router
    from backend.api.echo.router import router as echo_router
    from backend.api.users.router import router as users_router
    from backend.api.logs.router import router as logs_router
    from backend.api.conversation.router import router as conversation_router
    from backend.api.interactions.router import router as interactions_router
    from backend.api.memory.router import router as memory_router
    from backend.api.kg.router import router as kg_router
    from backend.api.emotion.router import router as emotion_router
    from backend.api.tts.router import router as tts_router
    from backend.api.agency.router import router as agency_router
    from backend.api.scheduler.router import router as scheduler_router
    from backend.api.handshake.router import router as handshake_router

    app.include_router(health_router, prefix="/api/v1/health", tags=["health"])
    app.include_router(echo_router, prefix="/api/v1/echo", tags=["echo"])
    app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
    app.include_router(logs_router, prefix="/api/v1/logs", tags=["logs"])
    app.include_router(conversation_router, prefix="/api/v1/conversation", tags=["conversation"])
    app.include_router(interactions_router, prefix="/api/v1/interactions", tags=["interactions"])
    app.include_router(memory_router, prefix="/api/v1", tags=["memory"])
    app.include_router(kg_router, prefix="/api/v1/kg", tags=["knowledge-graph"])
    app.include_router(emotion_router, prefix="/api/v1/emotion", tags=["emotion"])
    app.include_router(tts_router, prefix="/api/v1/tts", tags=["tts"])
    app.include_router(agency_router, prefix="/api/v1/agency", tags=["agency"])
    app.include_router(scheduler_router, prefix="/api/v1/scheduler", tags=["scheduler"])
    app.include_router(handshake_router, prefix="/api/v1/handshake", tags=["handshake"])

    return app


def _filter_openapi_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    paths: Dict[str, Any] = schema.get("paths") or {}
    filtered_paths = {
        path: item
        for path, item in paths.items()
        if not any(path.startswith(prefix) for prefix in EXCLUDED_PATH_PREFIXES)
    }

    schema = dict(schema)
    schema["paths"] = filtered_paths

    return schema


def _stable_json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _read_text_if_exists(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate public OpenAPI spec (golden artifact)")
    parser.add_argument(
        "--output",
        default="contracts/openapi/v1.json",
        help="Output path for generated OpenAPI spec (json)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the generated spec differs from the existing artifact",
    )
    args = parser.parse_args()

    output_path = Path(args.output)

    app = _build_public_app()
    schema = app.openapi()
    schema = _filter_openapi_schema(schema)

    rendered = _stable_json_dumps(schema)

    if args.check:
        existing = _read_text_if_exists(output_path)
        if existing is None:
            raise SystemExit(f"OpenAPI artifact missing: {output_path}")
        if existing != rendered:
            raise SystemExit(
                "OpenAPI artifact differs from generated spec. "
                "Run scripts/generate_openapi_public.py to update contracts/openapi/v1.json"
            )
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
