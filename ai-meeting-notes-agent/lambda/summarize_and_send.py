import json
import logging
import os

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from email_templates import get_email_template, render_email_body

from common import (
    DEFAULT_PROMPT_TEMPLATE_PATH,
    detect_language_from_text,
    infer_media_format,
    normalize_language_code,
    transcribe_media,
    translate_summary,
)
from common.prompt import load_prompt_template
from common.summary import invoke_bedrock
from common.transcription import fetch_transcript_from_s3

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

# AWS clients are created at module load so they can be reused across invocations.
ses = boto3.client("ses")

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "no-reply@yourdomain.com")
DEFAULT_EMAIL_LOCALE = os.environ.get("DEFAULT_EMAIL_LOCALE", "en")

PROMPT_TEMPLATE_PATH = os.environ.get("PROMPT_TEMPLATE_PATH", str(DEFAULT_PROMPT_TEMPLATE_PATH))


def lambda_handler(event, context):
    LOGGER.info(
        "Traitement de la requête: bucket=%s, key=%s, content_type=%s",
        event.get("bucket"),
        event.get("key"),
        event.get("content_type", "text"),
    )

    try:
        participants = event["participants"]
    except KeyError as exc:
        LOGGER.error("Événement invalide, champ manquant: %s", exc)
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing required field: {exc}"}),
        }

    if not isinstance(participants, list):
        LOGGER.error("Champ 'participants' invalide: %s", participants)
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "'participants' must be a list of email addresses"}),
        }

    content_type = event.get("content_type", "text").lower()
    bucket = event.get("bucket")
    key = event.get("key")
    media_format = event.get("media_format")
    target_language = event.get("target_language")

    skip_email = os.getenv("SKIP_EMAIL", "").strip().lower() in {"1", "true", "yes"}

    if content_type == "text" and not bucket and "text" in event:
        content = event["text"]
    else:
        if not bucket or not key:
            LOGGER.error("Les champs bucket et key sont requis pour content_type=%s", content_type)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "'bucket' and 'key' are required for S3-based content"}),
            }

        if content_type in {"audio", "video"}:
            try:
                transcript_text, detected_language = transcribe_media(
                    bucket, key, media_format or infer_media_format(key)
                )
            except Exception as exc:  # noqa: BLE001 - surface exact error upstream
                LOGGER.exception("Échec de la transcription pour %s/%s", bucket, key)
                return {
                    "statusCode": 502,
                    "body": json.dumps({"error": f"Transcription failed: {exc}"}),
                }
        else:
            try:
                transcript_text = fetch_transcript_from_s3(bucket, key)
            except RuntimeError as exc:
                return {
                    "statusCode": 500,
                    "body": json.dumps({"error": str(exc)}),
                }
            detected_language = event.get("language")

        content = transcript_text
    if content_type not in {"audio", "video"}:
        detected_language = event.get("language")

    if not detected_language:
        detected_language = detect_language_from_text(content)

    normalized_detected_language = normalize_language_code(detected_language)

    try:
        load_prompt_template(PROMPT_TEMPLATE_PATH)
        output = invoke_bedrock(content)
    except (ClientError, BotoCoreError) as exc:
        LOGGER.exception("Erreur lors de l'appel Bedrock")
        return {
            "statusCode": 502,
            "body": json.dumps({"error": f"Bedrock invocation failed: {exc}"}),
        }

    translation_applied = False
    final_language = normalized_detected_language
    normalized_target_language = None
    if target_language:
        output, translation_applied, normalized_target_language = translate_summary(
            output, normalized_detected_language, target_language
        )
        if translation_applied:
            final_language = normalized_target_language
        elif not final_language and normalized_target_language:
            final_language = normalized_target_language

    if not final_language:
        final_language = normalized_detected_language

    preferred_email_locale = (
        event.get("email_locale")
        or normalized_target_language
        or normalized_detected_language
        or DEFAULT_EMAIL_LOCALE
    )
    email_locale, email_template = get_email_template(
        preferred_email_locale, DEFAULT_EMAIL_LOCALE
    )
    body_text, body_html = render_email_body(
        summary=output,
        template=email_template,
        detected_language=normalized_detected_language,
        translated_language=(
            normalized_target_language if translation_applied else None
        ),
    )
    email_subject = email_template.get("subject", "Automated Meeting Summary")

    failed_emails = []
    if skip_email:
        LOGGER.info("Envoi email désactivé via SKIP_EMAIL. Aucun email ne sera envoyé.")

    for email in participants:
        if skip_email:
            LOGGER.debug("Envoi email ignoré pour %s (mode SKIP_EMAIL)", email)
            continue
        try:
            ses.send_email(
                Source=SENDER_EMAIL,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": email_subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": body_text, "Charset": "UTF-8"},
                        "Html": {"Data": body_html, "Charset": "UTF-8"},
                    },
                },
            )
        except (ClientError, BotoCoreError):
            LOGGER.exception("Échec d'envoi de l'email à %s", email)
            failed_emails.append(email)

    response_payload = {
        "summary": output,
        "message": "Résumé envoyé aux participants." if not skip_email else "Résumé généré (emails non envoyés : mode SKIP_EMAIL)",
        "content_type": content_type,
        "detected_language": normalized_detected_language,
        "final_language": final_language,
        "translation_applied": translation_applied,
        "target_language": normalized_target_language,
        "email_locale": email_locale,
    }

    if failed_emails:
        response_payload["message"] = "Résumé généré, mais certains emails n'ont pas été envoyés."
        response_payload["failed"] = failed_emails
        return {
            "statusCode": 207,
            "body": json.dumps(response_payload),
        }

    return {
        "statusCode": 200,
        "body": json.dumps(response_payload),
    }
