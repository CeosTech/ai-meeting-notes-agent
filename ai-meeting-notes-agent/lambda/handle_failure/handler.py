from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

import boto3
from botocore.exceptions import BotoCoreError, ClientError


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def _get_table():
    table_name = os.environ.get("RESULTS_TABLE")
    if not table_name:
        raise RuntimeError("RESULTS_TABLE environment variable is required")
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)


def lambda_handler(event: Dict[str, Any], _context) -> Dict[str, Any]:
    LOGGER.error("HandleFailure: job_id=%s reason=%s", event.get("job_id"), event.get("error"))

    job_id = event.get("job_id")
   if not job_id:
       raise ValueError("job_id is required for failure handling")

   now = datetime.now(timezone.utc).isoformat()
    failure_message = event.get("error") or "Pipeline execution failed."

    try:
        table = _get_table()
        existing = table.get_item(Key={"id": job_id}).get("Item", {})
        item = dict(existing or {})
        item.update(
            {
                "id": job_id,
                "status": "FAILED",
                "sourceType": event.get("content_type") or existing.get("sourceType"),
                "sourceKey": event.get("key") or existing.get("sourceKey"),
                "participants": event.get("participants") or existing.get("participants", []),
                "summary": event.get("summary"),
                "message": failure_message,
                "createdAt": event.get("createdAt") or existing.get("createdAt") or now,
                "updatedAt": now,
            }
        )

        optional_fields = {
            "targetLanguage": event.get("target_language"),
            "emailLocale": event.get("email_locale"),
            "detectedLanguage": event.get("detected_language"),
            "finalLanguage": event.get("final_language"),
            "translationApplied": event.get("translation_applied"),
        }
        for key, value in optional_fields.items():
            if value is not None:
                item[key] = value
            elif key in item:
                item.pop(key, None)

        sanitized = {k: v for k, v in item.items() if v is not None}
        table.put_item(Item=sanitized)
    except (ClientError, BotoCoreError) as exc:
        LOGGER.exception("Failed to persist failure result for %s", job_id)
        raise RuntimeError(f"DynamoDB write failed: {exc}") from exc

    return sanitized


def handler(event, context):
    try:
        payload = event if isinstance(event, dict) else json.loads(event)
    except json.JSONDecodeError as exc:
        raise ValueError("Event payload must be a JSON object") from exc
    return lambda_handler(payload, context)
