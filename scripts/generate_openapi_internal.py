from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _build_internal_app() -> FastAPI:
    from aico.core.version import get_backend_version
    from aico.core.config import ConfigurationManager
    from aico.security.key_manager import AICOKeyManager
    from gateway.adapters.rest_adapter import RESTAdapter

    repo_root = Path(__file__).resolve().parents[1]
    repo_config_dir = repo_root / "config"
    os.environ.setdefault("AICO_CONFIG_DIR", str(repo_config_dir))
    config_manager = ConfigurationManager(config_dir=repo_config_dir)
    config_manager.initialize(lightweight=True)

    api_gateway_config = config_manager.get("api_gateway", {})
    key_manager = AICOKeyManager(config_manager)
    app = RESTAdapter(config=api_gateway_config, key_manager=key_manager).get_app()
    app.title = "AICO Backend API (Internal)"
    app.version = get_backend_version()
    app.description = "AICO Backend REST API including internal endpoints (admin/system/operations)."
    return app


def _stable_json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _read_text_if_exists(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate internal OpenAPI spec (golden artifact)")
    parser.add_argument(
        "--output",
        default="contracts/openapi/internal-v1.json",
        help="Output path for generated OpenAPI spec (json)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the generated spec differs from the existing artifact",
    )
    args = parser.parse_args()

    output_path = Path(args.output)

    app = _build_internal_app()
    schema = app.openapi()

    rendered = _stable_json_dumps(schema)

    if args.check:
        existing = _read_text_if_exists(output_path)
        if existing is None:
            raise SystemExit(f"OpenAPI artifact missing: {output_path}")
        if existing != rendered:
            raise SystemExit(
                "OpenAPI artifact differs from generated spec. "
                "Run scripts/generate_openapi_internal.py to update contracts/openapi/internal-v1.json"
            )
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
