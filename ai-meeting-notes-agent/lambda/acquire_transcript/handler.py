from __future__ import annotations

import json
import logging
from typing import Any, Dict

from common import detect_language_from_text, infer_media_format, normalize_language_code, transcribe_media
from common.transcription import fetch_transcript_from_s3

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], _context) -> Dict[str, Any]:
    LOGGER.info(
        "AcquireTranscript: job_id=%s bucket=%s key=%s content_type=%s",
        event.get("job_id"),
        event.get("bucket"),
        event.get("key"),
        event.get("content_type"),
    )

    content_type = (event.get("content_type") or "text").lower()
    bucket = event.get("bucket")
    key = event.get("key")

    if content_type == "text" and event.get("text") and not bucket:
        transcript_text = event["text"]
        detected_language = event.get("language")
    else:
        if not bucket or not key:
            raise ValueError("bucket and key are required for S3-based content")

        if content_type in {"audio", "video"}:
            transcript_text, detected_language = transcribe_media(
                bucket,
                key,
                event.get("media_format") or infer_media_format(key),
            )
        else:
            transcript_text = fetch_transcript_from_s3(bucket, key)
            detected_language = event.get("language")

    if not detected_language:
        detected_language = detect_language_from_text(transcript_text)

    normalized_detected = normalize_language_code(detected_language)

    return {
        **event,
        "transcript": transcript_text,
        "detected_language": normalized_detected,
    }


def handler(event, context):
    """Compatibility wrapper when invoked via Lambda console tests."""

    try:
        payload = event if isinstance(event, dict) else json.loads(event)
    except json.JSONDecodeError as exc:
        raise ValueError("Event payload must be a JSON object") from exc
    return lambda_handler(payload, context)
