from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Optional, Tuple
from urllib import error as urllib_error
from urllib import request as urllib_request

import boto3
from botocore.exceptions import BotoCoreError, ClientError


LOGGER = logging.getLogger(__name__)

_s3_client = boto3.client("s3")
_transcribe_client = boto3.client("transcribe")


SUPPORTED_MEDIA_FORMATS = {
    "mp3",
    "mp4",
    "wav",
    "flac",
    "ogg",
    "amr",
    "webm",
    "m4a",
}


def infer_media_format(key: str) -> Optional[str]:
    extension = key.split(".")[-1].lower()
    if extension in SUPPORTED_MEDIA_FORMATS:
        return extension
    return None


def transcribe_media(bucket: str, key: str, media_format: Optional[str]) -> Tuple[str, Optional[str]]:
    job_name = f"{os.environ.get('TRANSCRIBE_JOB_PREFIX', 'meeting-notes-agent')}-{uuid.uuid4()}"
    job_args = {
        "TranscriptionJobName": job_name,
        "Media": {"MediaFileUri": f"s3://{bucket}/{key}"},
        "IdentifyLanguage": True,
        "OutputBucketName": os.environ.get("TRANSCRIBE_OUTPUT_BUCKET"),
    }

    if not job_args["OutputBucketName"]:
        job_args.pop("OutputBucketName")

    if media_format:
        job_args["MediaFormat"] = media_format

    LOGGER.info("Démarrage de la transcription pour %s/%s", bucket, key)
    _transcribe_client.start_transcription_job(**job_args)

    timeout_seconds = int(os.environ.get("TRANSCRIBE_TIMEOUT", 900))
    poll_interval = 5
    elapsed = 0

    while elapsed < timeout_seconds:
        job = _transcribe_client.get_transcription_job(TranscriptionJobName=job_name)[
            "TranscriptionJob"
        ]
        status = job["TranscriptionJobStatus"]
        if status == "COMPLETED":
            transcript_uri = job["Transcript"]["TranscriptFileUri"]
            detected_language = job.get("LanguageCode")
            LOGGER.info(
                "Transcription terminée (langue=%s). Récupération du transcript depuis %s",
                detected_language,
                transcript_uri,
            )
            try:
                with urllib_request.urlopen(transcript_uri, timeout=30) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
            except (urllib_error.URLError, urllib_error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
                LOGGER.exception("Impossible de récupérer ou parser le fichier de transcription")
                raise RuntimeError("Failed to download transcription result") from exc
            transcripts = payload.get("results", {}).get("transcripts", [])
            transcript_text = "\n".join(
                item.get("transcript", "").strip() for item in transcripts if item.get("transcript")
            )
            return transcript_text, detected_language

        if status == "FAILED":
            reason = job.get("FailureReason", "Unknown reason")
            LOGGER.error("Transcription échouée: %s", reason)
            raise RuntimeError(f"Transcription failed: {reason}")

        time.sleep(poll_interval)
        elapsed += poll_interval

    LOGGER.error("Transcription non terminée après %s secondes", timeout_seconds)
    raise TimeoutError("Transcription job did not complete in time")


def fetch_transcript_from_s3(bucket: str, key: str) -> str:
    try:
        file_obj = _s3_client.get_object(Bucket=bucket, Key=key)
        return file_obj["Body"].read().decode("utf-8")
    except (ClientError, BotoCoreError) as exc:
        LOGGER.exception("Impossible de récupérer le fichier S3 %s/%s", bucket, key)
        raise RuntimeError(f"Failed to retrieve transcript: {exc}") from exc
