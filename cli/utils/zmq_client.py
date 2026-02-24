"""Legacy compatibility shim.

This module used to host the ZMQ-based CLI client, but the codebase is now
NATS-only.

Import paths are preserved to avoid breaking older CLI modules.
"""

from cli.utils.nats_client import (  # noqa: F401
    CLINATSClient as CLIZMQClient,
    get_modelservice_health,
    get_modelservice_status,
    get_ollama_status,
    get_ollama_models,
    pull_ollama_model,
    get_embeddings,
)


__all__ = [
    "CLIZMQClient",
    "get_modelservice_health",
    "get_modelservice_status",
    "get_ollama_status",
    "get_ollama_models",
    "pull_ollama_model",
    "get_embeddings",
]
