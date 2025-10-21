from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional


LOGGER = logging.getLogger(__name__)

_PROMPT_TEMPLATE_CACHE: Optional[str] = None


def resolve_default_prompt_path() -> Path:
    """Locate the bundled prompt template in both local dev and Lambda bundles."""

    candidates = [
        Path(__file__).resolve().parent.parent / "summarize_prompt.txt",
        Path(__file__).resolve().parent.parent / "prompts" / "summarize_prompt.txt",
        Path(__file__).resolve().parent.parent.parent / "prompts" / "summarize_prompt.txt",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    # Default to the first option so downstream errors mention a deterministic path
    return candidates[0]


DEFAULT_PROMPT_TEMPLATE_PATH = resolve_default_prompt_path()


def load_prompt_template(path_override: Optional[str] = None) -> str:
    """Load the prompt template from disk and cache it for subsequent calls."""

    global _PROMPT_TEMPLATE_CACHE

    if _PROMPT_TEMPLATE_CACHE is not None and not path_override:
        return _PROMPT_TEMPLATE_CACHE

    prompt_path = Path(path_override) if path_override else Path(os.environ.get("PROMPT_TEMPLATE_PATH", DEFAULT_PROMPT_TEMPLATE_PATH))

    try:
        template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        LOGGER.error("Prompt template introuvable à l'emplacement %s", prompt_path)
        raise RuntimeError("Prompt template file is missing") from exc

    if not path_override:
        _PROMPT_TEMPLATE_CACHE = template
    return template
