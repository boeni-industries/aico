from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _stable_json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _read_text_if_exists(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _is_topic_value(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if value.startswith("http"):
        return False
    if "/" not in value:
        return False
    # Exclude prefix constants like "logs/" and wildcard patterns like "auth/*"
    if value.endswith("/"):
        return False
    if "*" in value:
        return False
    return True


def _topic_to_subject(topic: str) -> str:
    return topic.replace("/", ".")


def _collect_topics() -> List[Tuple[str, str]]:
    from aico.core.topics import AICOTopics

    topics: List[Tuple[str, str]] = []
    for name in dir(AICOTopics):
        if name.startswith("_"):
            continue
        value = getattr(AICOTopics, name)
        if _is_topic_value(value):
            topics.append((name, value))

    topics.sort(key=lambda kv: kv[1])
    return topics


def _infer_request_reply_pairs(topics: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
    by_value = {value: name for name, value in topics}

    pairs: List[Dict[str, Any]] = []
    for name, value in topics:
        if "/request/" not in value:
            continue
        response_value = value.replace("/request/", "/response/")
        if response_value in by_value:
            pairs.append(
                {
                    "request_topic": value,
                    "request_subject": _topic_to_subject(value),
                    "response_topic": response_value,
                    "response_subject": _topic_to_subject(response_value),
                    "notes": "inferred from /request/ -> /response/ convention",
                }
            )

    pairs.sort(key=lambda p: p["request_topic"])
    return pairs


def _build_nats_contract() -> Dict[str, Any]:
    topics = _collect_topics()
    pairs = _infer_request_reply_pairs(topics)

    return {
        "version": "v1",
        "nats": {
            "subject_policy": {
                "source": "shared.aico.core.topics.AICOTopics",
                "mapping": "topic.replace('/', '.')",
                "example": {
                    "topic": "conversation/user/input/v1",
                    "subject": "conversation.user.input.v1",
                },
            },
            "envelope": {
                "protobuf": "aico.proto.aico_core_envelope.AicoMessage",
                "required_metadata_attributes": [
                    "correlation_id",
                    "reply_to",
                    "tenant_id",
                    "user_id",
                    "request_id",
                    "idempotency_key",
                ],
                "notes": "Attributes are enforced by the gateway perimeter; core treats them as required invariants.",
            },
            "subjects": [
                {
                    "name": name,
                    "topic": value,
                    "subject": _topic_to_subject(value),
                }
                for name, value in topics
            ],
            "request_reply": pairs,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate frozen NATS contract (golden artifact)")
    parser.add_argument(
        "--output",
        default="contracts/nats/v1.json",
        help="Output path for generated NATS contract (json)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the generated contract differs from the existing artifact",
    )
    args = parser.parse_args()

    output_path = Path(args.output)

    contract = _build_nats_contract()
    rendered = _stable_json_dumps(contract)

    if args.check:
        existing = _read_text_if_exists(output_path)
        if existing is None:
            raise SystemExit(f"NATS contract artifact missing: {output_path}")
        if existing != rendered:
            raise SystemExit(
                "NATS contract artifact differs from generated contract. "
                "Run scripts/generate_nats_contract.py to update contracts/nats/v1.json"
            )
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
