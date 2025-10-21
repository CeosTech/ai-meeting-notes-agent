from __future__ import annotations

import json
import logging
from typing import Any, Dict

from common import normalize_language_code, translate_summary

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], _context) -> Dict[str, Any]:
    LOGGER.info("TranslateTask: job_id=%s target=%s", event.get("job_id"), event.get("target_language"))

    summary = event.get("summary")
    if summary is None:
        raise ValueError("Missing summary in event payload")

    detected_language = event.get("detected_language")
    target_language = event.get("target_language")

    translated_summary, translation_applied, final_language = translate_summary(
        summary,
        detected_language,
        target_language,
    )

    result = {
        **event,
        "summary": translated_summary,
        "translation_applied": translation_applied,
        "final_language": final_language or normalize_language_code(detected_language),
    }

    if target_language:
        result["target_language"] = normalize_language_code(target_language)

    return result


def handler(event, context):
    try:
        payload = event if isinstance(event, dict) else json.loads(event)
    except json.JSONDecodeError as exc:
        raise ValueError("Event payload must be a JSON object") from exc
    return lambda_handler(payload, context)
