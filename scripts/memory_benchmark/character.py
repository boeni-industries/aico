"""Character specification loader for memory benchmarks.

The benchmark must verify the assistant stays in character.
We auto-detect the active conversation model from effective runtime config and load
its deployed Modelfile from the OS-specific config directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import re

from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths


@dataclass
class CharacterSpec:
    model_name: str
    modelfile_path: Optional[Path]
    system_prompt: str
    character_name: Optional[str]
    forbidden_phrases: List[str]


_SYSTEM_BLOCK_RE = re.compile(r'\bSYSTEM\s+"""(.*?)"""', re.DOTALL)


def get_active_conversation_model_name() -> str:
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    value = config.get("modelservice.ollama.default_models.conversation.name")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing config key: modelservice.ollama.default_models.conversation.name")
    return value.strip()


def resolve_deployed_modelfile(*, model_name: str) -> Optional[Path]:
    modelfiles_dir = AICOPaths.get_config_directory() / "modelfiles"
    candidate = modelfiles_dir / f"Modelfile.{model_name}"
    if candidate.exists():
        return candidate
    return None


def _extract_system_prompt(modelfile_text: str) -> str:
    m = _SYSTEM_BLOCK_RE.search(modelfile_text)
    return m.group(1).strip() if m else ""


def _infer_character_name(system_prompt: str) -> Optional[str]:
    # Heuristic: "You are Eve." -> Eve
    m = re.search(r"\bYou are\s+([A-Za-z0-9_\- ]{1,40})\.", system_prompt)
    if m:
        name = m.group(1).strip()
        return name if name else None
    return None


def _extract_forbidden_phrases(system_prompt: str) -> List[str]:
    # Heuristic: parse a "Never:" block with dash-lines.
    forbidden: List[str] = []
    if not system_prompt:
        return forbidden

    never_idx = system_prompt.lower().find("never:")
    if never_idx == -1:
        return forbidden

    tail = system_prompt[never_idx:]
    for line in tail.splitlines()[1:]:
        stripped = line.strip()
        if not stripped:
            # Stop once we hit an empty line after collecting some items
            if forbidden:
                break
            continue
        if stripped.startswith("-"):
            item = stripped.lstrip("-").strip()
            if not item:
                continue
            forbidden.append(item)
        else:
            # Stop when the list ends
            if forbidden:
                break

    return forbidden


def load_active_character_spec() -> CharacterSpec:
    model_name = get_active_conversation_model_name()
    path = resolve_deployed_modelfile(model_name=model_name)

    system_prompt = ""
    if path and path.exists():
        system_prompt = _extract_system_prompt(path.read_text(encoding="utf-8"))

    character_name = _infer_character_name(system_prompt)
    forbidden_phrases = _extract_forbidden_phrases(system_prompt)

    return CharacterSpec(
        model_name=model_name,
        modelfile_path=path,
        system_prompt=system_prompt,
        character_name=character_name,
        forbidden_phrases=forbidden_phrases,
    )


def character_violation_checks(*, spec: CharacterSpec, response_text: str) -> List[str]:
    """Return a list of human-readable violations found in the response."""

    violations: List[str] = []
    text = (response_text or "").strip()
    lower = text.lower()

    if not text:
        violations.append("empty_response")
        return violations

    # Generic hard failures (persona drift / role reversal)
    role_reversal_patterns: List[Tuple[str, str]] = [
        (r"\byou are\s+eve\b", "role_reversal_you_are_eve"),
        (r"\bi am\s+michael\b", "role_reversal_i_am_user"),
        (r"\byou are\s+the user\b", "role_reversal_you_are_user"),
    ]
    for pattern, label in role_reversal_patterns:
        if re.search(pattern, lower):
            violations.append(label)

    # If Modelfile explicitly forbids calling self AI/assistant, enforce via simple keyword checks.
    never_ai = any("refer to yourself" in fp.lower() and ("ai" in fp.lower() or "assistant" in fp.lower()) for fp in spec.forbidden_phrases)
    if never_ai:
        if re.search(r"\b(ai|assistant|companion)\b", lower):
            violations.append("forbidden_self_reference_ai_assistant")

    # If we know the character name, enforce no first-person identity mismatch.
    if spec.character_name:
        # If response explicitly claims to be someone else.
        m = re.search(r"\bi am\s+([A-Za-z0-9_\- ]{1,40})\b", text)
        if m:
            claimed = m.group(1).strip()
            if claimed and spec.character_name.lower() not in claimed.lower():
                violations.append("identity_mismatch_i_am")

    return violations
