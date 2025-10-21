from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, validator

UPLOAD_BUCKET = os.environ.get("UPLOAD_BUCKET")
SUMMARY_STATE_MACHINE_ARN = os.environ.get("SUMMARY_STATE_MACHINE_ARN")
RESULTS_TABLE = os.environ.get("RESULTS_TABLE")
DEFAULT_TARGET_LANGUAGE = os.environ.get("DEFAULT_TARGET_LANGUAGE", "")
DEFAULT_EMAIL_LOCALE = os.environ.get("DEFAULT_EMAIL_LOCALE", "en")

if not UPLOAD_BUCKET:
    raise RuntimeError("UPLOAD_BUCKET environment variable is required")
if not SUMMARY_STATE_MACHINE_ARN:
    raise RuntimeError("SUMMARY_STATE_MACHINE_ARN environment variable is required")
if not RESULTS_TABLE:
    raise RuntimeError("RESULTS_TABLE environment variable is required")

s3_client = boto3.client("s3")
stepfunctions_client = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(RESULTS_TABLE)


class PresignRequest(BaseModel):
    filename: str
    contentType: str = Field(alias="contentType")


class PresignResponse(BaseModel):
    uploadUrl: str
    objectKey: str
    fields: Optional[Dict[str, str]] = None


class JobCreateRequest(BaseModel):
    sourceType: str = Field(pattern=r"^(text|audio|video)$")
    sourceKey: Optional[str]
    participants: list[EmailStr]
    targetLanguage: Optional[str] = Field(default=None, alias="targetLanguage")
    emailLocale: Optional[str] = Field(default=None, alias="emailLocale")
    language: Optional[str] = None
    text: Optional[str] = None

    @validator("participants")
    def participants_not_empty(cls, v: list[EmailStr]) -> list[EmailStr]:
        if not v:
            raise ValueError("At least one participant email is required")
        return v


class MeetingJob(BaseModel):
    id: str
    status: str
    sourceType: str
    sourceKey: str
    participants: list[EmailStr]
    executionArn: Optional[str] = None
    targetLanguage: Optional[str] = None
    emailLocale: Optional[str] = None
    detectedLanguage: Optional[str] = None
    finalLanguage: Optional[str] = None
    translationApplied: Optional[bool] = None
    summary: Optional[str] = None
    message: Optional[str] = None
    failed: Optional[list[EmailStr]] = None
    createdAt: str
    updatedAt: Optional[str] = None


app = FastAPI(title="AI Meeting Notes API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/presign", response_model=PresignResponse)
async def create_presigned_post(payload: PresignRequest) -> PresignResponse:
    object_key = f"uploads/{uuid.uuid4()}_{payload.filename}"
    try:
        presigned = s3_client.generate_presigned_post(
            Bucket=UPLOAD_BUCKET,
            Key=object_key,
            Fields={"Content-Type": payload.contentType},
            Conditions=[["starts-with", "$Content-Type", ""]],
            ExpiresIn=3600,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to presign upload: {exc}") from exc

    return PresignResponse(uploadUrl=presigned["url"], objectKey=object_key, fields=presigned.get("fields"))


@app.post("/api/jobs", response_model=MeetingJob)
async def create_job(payload: JobCreateRequest) -> MeetingJob:
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    if payload.sourceType == "text" and payload.text and not payload.sourceKey:
        object_key = f"uploads/{job_id}.txt"
        try:
            s3_client.put_object(
                Bucket=UPLOAD_BUCKET,
                Key=object_key,
                Body=payload.text.encode("utf-8"),
                ContentType="text/plain",
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=500, detail=f"Failed to upload transcript: {exc}") from exc
    else:
        if not payload.sourceKey:
            raise HTTPException(status_code=400, detail="sourceKey is required when no inline text provided")
        object_key = payload.sourceKey

    job_record = {
        "id": job_id,
        "status": "PROCESSING",
        "sourceType": payload.sourceType,
        "sourceKey": object_key,
        "participants": payload.participants,
        "createdAt": now,
        "updatedAt": now,
    }
    target_language = payload.targetLanguage or (DEFAULT_TARGET_LANGUAGE or None)
    email_locale = payload.emailLocale or (DEFAULT_EMAIL_LOCALE or None)
    if target_language:
        job_record["targetLanguage"] = target_language
    if email_locale:
        job_record["emailLocale"] = email_locale

    try:
        table.put_item(Item=job_record)
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist job record: {exc}") from exc

    execution_input: Dict[str, Any] = {
        "job_id": job_id,
        "bucket": UPLOAD_BUCKET,
        "key": object_key,
        "participants": payload.participants,
        "content_type": payload.sourceType,
        "createdAt": now,
    }

    if target_language:
        execution_input["target_language"] = target_language
    if email_locale:
        execution_input["email_locale"] = email_locale
    if payload.language:
        execution_input["language"] = payload.language

    try:
        execution = stepfunctions_client.start_execution(
            stateMachineArn=SUMMARY_STATE_MACHINE_ARN,
            name=job_id,
            input=json.dumps(execution_input),
        )
    except (BotoCoreError, ClientError) as exc:
        table.update_item(
            Key={"id": job_id},
            UpdateExpression="SET #status = :status, #message = :message, updatedAt = :updatedAt",
            ExpressionAttributeNames={"#status": "status", "#message": "message"},
            ExpressionAttributeValues={
                ":status": "FAILED",
                ":message": f"Failed to start pipeline: {exc}",
                ":updatedAt": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise HTTPException(status_code=500, detail=f"Failed to start Step Functions execution: {exc}") from exc

    job_record["executionArn"] = execution.get("executionArn")
    job_record["targetLanguage"] = target_language
    job_record["emailLocale"] = email_locale
    job_record["updatedAt"] = datetime.now(timezone.utc).isoformat()
    table.update_item(
        Key={"id": job_id},
        UpdateExpression="SET executionArn = :arn, updatedAt = :updatedAt",
        ExpressionAttributeValues={
            ":arn": job_record["executionArn"],
            ":updatedAt": job_record["updatedAt"],
        },
    )

    return MeetingJob(**job_record)


@app.get("/api/jobs/{job_id}", response_model=MeetingJob)
async def get_job(job_id: str) -> MeetingJob:
    try:
        result = table.get_item(Key={"id": job_id})
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve job: {exc}") from exc

    item = result.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")

    return MeetingJob(**item)


@app.get("/-/health")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}
