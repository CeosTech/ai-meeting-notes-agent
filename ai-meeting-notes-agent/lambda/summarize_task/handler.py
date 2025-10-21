from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from common import DEFAULT_PROMPT_TEMPLATE_PATH
from common.prompt import load_prompt_template
from common.summary import invoke_bedrock

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], _context) -> Dict[str, Any]:
    LOGGER.info("SummarizeTask: job_id=%s", event.get("job_id"))

    transcript = event.get("transcript")
    if not transcript:
        raise ValueError("Missing transcript in event payload")

    prompt_path = os.environ.get("PROMPT_TEMPLATE_PATH", str(DEFAULT_PROMPT_TEMPLATE_PATH))
    load_prompt_template(prompt_path)

    summary = invoke_bedrock(transcript)

    return {**event, "summary": summary}


def handler(event, context):
    try:
        payload = event if isinstance(event, dict) else json.loads(event)
    except json.JSONDecodeError as exc:
        raise ValueError("Event payload must be a JSON object") from exc
    return lambda_handler(payload, context)
