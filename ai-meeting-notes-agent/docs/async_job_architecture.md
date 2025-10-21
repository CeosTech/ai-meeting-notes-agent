# Asynchronous Job Orchestration

This document captures the proposed changes to move the meeting notes workflow away from the current synchronous Lambda invocation toward a resilient, production-friendly asynchronous design.

## High-Level Flow

1. **Client upload**  
   - Frontend requests a presigned POST from the backend and uploads the media/transcript file to the ingest bucket.  
   - Frontend creates a job by calling `POST /api/jobs`, passing metadata (source type, key, participants, localization hints).

2. **Job acceptance (FastAPI backend)**  
   - Generate a `job_id` (UUID).  
   - Persist an item in `ResultsTable` with `status="PENDING"`, initial metadata, and timestamps.  
   - Invoke Step Functions `StartExecution` with a payload containing the `job_id`, S3 object info, and participant details.  
   - Return immediately to the frontend with `{ id, status: "PENDING" }`.

3. **State machine execution (AWS Step Functions)**  
   - **Acquire transcript**  
     - Choice: call Amazon Transcribe for audio/video, or fetch S3 object directly for text.  
     - Wait for transcription completion with a backoff/sleep loop (using `Wait` states) and store transcript URI or inline text for downstream steps.  
     - Update DynamoDB status to `PROCESSING` after transcription succeeds.
   - **Summarization with Bedrock**  
     - Invoke a dedicated Lambda (`SummarizeTask`) that loads the prompt, calls Claude Sonnet, and returns the raw summary.
   - **Language detection and translation**  
     - Lambda uses Comprehend/Translate to detect source language and optionally translate to `target_language`.  
     - Store `detected_language`, `final_language`, and `translation_applied` in the execution context.
   - **Email dispatch**  
     - Lambda (`SendEmailTask`) renders localized templates and calls SES unless `SKIP_EMAIL` is set.  
     - Collect failed recipients in the response payload.
   - **Persist result**  
     - Final Task state updates DynamoDB with `status="COMPLETED"` or `status="FAILED"` and writes the summary, metadata, and message.  
     - Optional: emit an EventBridge event for observability or downstream consumers.

4. **Frontend polling**  
   - `useJobStatus` continues to poll `GET /api/jobs/{id}`.  
   - Backend now simply returns the DynamoDB item—no direct Lambda invocation is required.

## Backend Code Changes (FastAPI)

- Replace the synchronous `lambda:InvokeFunction` call with Step Functions `StartExecution`.  
  ```python
  stepfunctions = boto3.client("stepfunctions")
  execution = stepfunctions.start_execution(
      stateMachineArn=SUMMARY_STATE_MACHINE_ARN,
      name=f"{job_id}",
      input=json.dumps({...})
  )
  ```
- Introduce environment variables for the state machine ARN and the SQS queue (if used for retries).  
- Add helper functions to update DynamoDB status when exceptions occur during request handling.  
- Ensure `POST /api/jobs` returns 202-style semantics (accepted) rather than blocking for completion.

## Lambda / Task Breakdown

| Task | Implementation | Notes |
|------|----------------|-------|
| `AcquireTranscript` | `lambda/acquire_transcript/handler.py` | Returns transcript text + detected language |
| `SummarizeTask` | `lambda/summarize_task/handler.py` | Calls Bedrock with the shared prompt |
| `TranslateTask` | `lambda/translate_task/handler.py` | Optional translation + language bookkeeping |
| `SendEmailTask` | `lambda/send_email_task/handler.py` | Sends localized emails (respects `SKIP_EMAIL`) |
| `FinalizeTask` | `lambda/finalize_task/handler.py` | Persists success state in DynamoDB |
| `HandleFailure` | `lambda/handle_failure/handler.py` | Records failure state and error message |

Package the functions with `infra/package_async_lambdas.sh`. The script zips every task together with `lambda/common` helpers and the email templates under `dist/lambdas/`.

> For cost-sensitive setups a single monolithic Lambda can still be used inside the state machine, but make sure the state machine handles timeouts and retries, rather than the API layer.

## DynamoDB Schema

- Table name: `ResultsTable` (partition key `id`).  
- Attributes: `status`, `sourceType`, `sourceKey`, `participants`, `targetLanguage`, `emailLocale`, `detectedLanguage`, `finalLanguage`, `translationApplied`, `summary`, `message`, `createdAt`, `updatedAt`, `failedRecipients`.  
- Streams (optional): enable for audit or alerting pipelines.

## Step Functions Definition Sketch

```json
{
  "StartAt": "Prepare",
  "States": {
    "Prepare": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {...},
      "Next": "AcquireTranscript"
    },
    "AcquireTranscript": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Retry": [{ "ErrorEquals": ["States.ALL"], "MaxAttempts": 2, "IntervalSeconds": 15 }],
      "Next": "Summarize"
    },
    "Summarize": { "...": "..." },
    "Translate": { "...": "..." },
    "SendEmail": { "...": "..." },
    "Finalize": {
      "Type": "Task",
      "Resource": "...",
      "End": true
    }
  }
}
```

Adjust the exact layout based on whether translation is optional (use `Choice` states).

The repository ships a starter definition in `infra/state_machine_definition.asl.json` that references each Lambda task with template placeholders (e.g. `{{SummarizeTaskArn}}`). Replace the placeholders with the real ARNs during deployment or synthesise them via IaC.

## Frontend Impact

- No breaking changes to the polling hook—just ensure it handles `PENDING`/`PROCESSING` statuses longer.  
- Consider surfacing intermediate progress messages (e.g., transcription in progress) returned by the Step Functions tasks via DynamoDB updates.

## Observability

- Enable Step Functions execution logging and X-Ray tracing.  
- Create CloudWatch alarms on state machine failures, Lambda DLQ depth, and SES bounce/complaint metrics.  
- Persist execution ARN in the DynamoDB item to assist with troubleshooting.
