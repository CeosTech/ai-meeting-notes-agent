import logging
import os

import boto3
from dotenv import load_dotenv


LOGGER = logging.getLogger(__name__)

load_dotenv()


def _skip_email() -> bool:
    return os.getenv("SKIP_EMAIL", "").strip().lower() in {"1", "true", "yes"}


def send_summary_email(to_addresses, subject, body_text, body_html=None):
    """Send a summary email through SES unless SKIP_EMAIL disables delivery."""

    if _skip_email():
        LOGGER.info("SKIP_EMAIL active: skipping SES send to %s", to_addresses)
        return {
            "skipped": True,
            "message": "Email sending disabled by SKIP_EMAIL flag.",
            "recipients": to_addresses,
        }

    sender = os.getenv("SENDER_EMAIL")
    if not sender:
        raise RuntimeError("SENDER_EMAIL environment variable is required to send email")

    region = os.getenv("AWS_REGION")
    if not region:
        raise RuntimeError("AWS_REGION environment variable is required to send email")

    ses = boto3.client("ses", region_name=region)

    body = {
        "Text": {"Data": body_text, "Charset": "UTF-8"},
    }
    if body_html:
        body["Html"] = {"Data": body_html, "Charset": "UTF-8"}

    response = ses.send_email(
        Source=sender,
        Destination={"ToAddresses": to_addresses},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": body,
        }
    )
    return response
