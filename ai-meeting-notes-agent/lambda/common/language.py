from __future__ import annotations

import logging
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError


LOGGER = logging.getLogger(__name__)

_comprehend_client = boto3.client("comprehend")


def normalize_language_code(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    return code.replace("_", "-").lower()


def detect_language_from_text(text: str) -> Optional[str]:
    snippet = text[:4500]
    if not snippet.strip():
        return None
    try:
        result = _comprehend_client.detect_dominant_language(Text=snippet)
        languages = result.get("Languages", [])
        if not languages:
            return None
        languages.sort(key=lambda item: item.get("Score", 0), reverse=True)
        return languages[0].get("LanguageCode")
    except (ClientError, BotoCoreError):
        LOGGER.exception("Impossible de détecter la langue via Comprehend")
    return None
