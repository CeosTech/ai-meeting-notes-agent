from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from email_templates import get_email_template, render_email_body

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

ses = boto3.client("ses")

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "no-reply@yourdomain.com")
DEFAULT_EMAIL_LOCALE = os.environ.get("DEFAULT_EMAIL_LOCALE", "en")


def _should_skip_email() -> bool:
    return os.getenv("SKIP_EMAIL", "").strip().lower() in {"1", "true", "yes"}


def _send_email(to_address: str, subject: str, body_text: str, body_html: str | None = None) -> None:
    message_body: Dict[str, Dict[str, str]] = {
        "Text": {"Data": body_text, "Charset": "UTF-8"},
    }
    if body_html:
        message_body["Html"] = {"Data": body_html, "Charset": "UTF-8"}

    ses.send_email(
        Source=SENDER_EMAIL,
        Destination={"ToAddresses": [to_address]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": message_body,
        },
    )


def lambda_handler(event: Dict[str, Any], _context) -> Dict[str, Any]:
    LOGGER.info("SendEmailTask: job_id=%s", event.get("job_id"))

    participants: List[str] = event.get("participants") or []
    if not participants:
        raise ValueError("Participants list is required to send emails")

    summary = event.get("summary")
    if summary is None:
        raise ValueError("Summary is required to send emails")

    preferred_email_locale = (
        event.get("email_locale")
        or event.get("target_language")
        or event.get("final_language")
        or event.get("detected_language")
        or DEFAULT_EMAIL_LOCALE
    )
    email_locale, email_template = get_email_template(preferred_email_locale, DEFAULT_EMAIL_LOCALE)
    body_text, body_html = render_email_body(
        summary=summary,
        template=email_template,
        detected_language=event.get("detected_language"),
        translated_language=(event.get("final_language") if event.get("translation_applied") else None),
    )
    email_subject = email_template.get("subject", "Automated Meeting Summary")

    failed: List[str] = []
    if _should_skip_email():
        LOGGER.info("SKIP_EMAIL actif : aucun envoi effectué.")
    else:
        for recipient in participants:
            try:
                _send_email(recipient, email_subject, body_text, body_html)
            except (ClientError, BotoCoreError):
                LOGGER.exception("Échec d'envoi de l'email à %s", recipient)
                failed.append(recipient)

    payload = {
        **event,
        "email_locale": email_locale,
        "failed": failed or None,
    }

    if failed:
        payload["message"] = "Résumé généré, mais certains emails n'ont pas été envoyés."
    elif _should_skip_email():
        payload["message"] = "Résumé généré (emails non envoyés : mode SKIP_EMAIL)"
    else:
        payload["message"] = "Résumé envoyé aux participants."

    return payload


def handler(event, context):
    try:
        payload = event if isinstance(event, dict) else json.loads(event)
    except json.JSONDecodeError as exc:
        raise ValueError("Event payload must be a JSON object") from exc
    return lambda_handler(payload, context)
