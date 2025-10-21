from __future__ import annotations

import json
import logging
from typing import Optional, Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .language import normalize_language_code
from .prompt import load_prompt_template


LOGGER = logging.getLogger(__name__)

_bedrock_runtime = boto3.client(service_name="bedrock-runtime")
_translate_client = boto3.client("translate")


MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"


def build_bedrock_payload(transcript: str) -> str:
    template = load_prompt_template()
    prompt_text = template.replace("{{transcript}}", transcript)

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0.5,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text,
                    }
                ],
            }
        ],
    }

    return json.dumps(payload)


def extract_bedrock_output(response_body: bytes) -> str:
    try:
        result = json.loads(response_body.decode("utf-8"))
    except json.JSONDecodeError:
        LOGGER.exception("Réponse Bedrock invalide (JSON)")
        return "Pas de résumé généré."

    text_segments = [
        segment.get("text", "").strip()
        for segment in result.get("content", [])
        if segment.get("type") == "text"
    ]

    output = "\n".join(filter(None, text_segments)).strip()
    if output:
        return output

    completion_fallback = result.get("completion")
    if completion_fallback:
        return completion_fallback.strip()

    LOGGER.warning("Bedrock a répondu sans contenu exploitable: %s", result)
    return "Pas de résumé généré."


def invoke_bedrock(transcript: str) -> str:
    payload = build_bedrock_payload(transcript)
    response = _bedrock_runtime.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=payload,
    )
    return extract_bedrock_output(response["body"].read())


def translate_summary(summary: str, source_language: Optional[str], target_language: Optional[str]) -> Tuple[str, bool, Optional[str]]:
    if not summary.strip() or not target_language:
        return summary, False, normalize_language_code(source_language)

    normalized_target = normalize_language_code(target_language)
    if not normalized_target:
        LOGGER.error("Langue cible '%s' invalide - traduction ignorée", target_language)
        return summary, False, normalize_language_code(source_language)

    source = normalize_language_code(source_language) or "auto"
    try:
        response = _translate_client.translate_text(
            Text=summary,
            SourceLanguageCode=source,
            TargetLanguageCode=normalized_target,
        )
        translated = response.get("TranslatedText", summary)
        return translated, True, normalized_target
    except (ClientError, BotoCoreError):
        LOGGER.exception("La traduction a échoué")
    return summary, False, normalize_language_code(source_language)
