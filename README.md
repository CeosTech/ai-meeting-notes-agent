# AI Meeting Notes Agent

AI Meeting Notes Agent ingests meeting transcripts or recordings, creates concise summaries and action items, and delivers the results to participants by email. The solution is built for the AWS AI Agent Hackathon and showcases Amazon Bedrock, Transcribe, Translate, Comprehend, SES, and AgentCore working together.

---

## Key Features
- Accepts raw text transcripts or audio/video files stored in Amazon S3
- Uses Amazon Transcribe with automatic language detection to produce transcripts from media assets
- Summarizes discussions and extracts action items with Amazon Bedrock (Claude 3 Sonnet)
- Detects language, optionally translates the summary to a target language, and annotates the delivery metadata
- Sends localized, HTML-formatted reports via Amazon SES with configurable greetings and headings
- Orchestrates the end-to-end workflow through AgentCore

---

## Architecture
The repository includes `diagram.svg` (and the editable `diagram.drawio`) to illustrate the end-to-end architecture.

![Architecture Diagram](diagram.svg)

| Component | Responsibility |
|-----------|----------------|
| Amazon S3 | Stores transcripts or media inputs and (optionally) transcription outputs |
| AWS Lambda | Orchestrates retrieval, transcription, summarization, translation, and email delivery |
| Amazon Bedrock | Hosts Claude 3 Sonnet for summarization and action-item extraction |
| Amazon Transcribe | Converts audio/video recordings into text |
| Amazon Translate | Translates the final summary on demand |
| Amazon Comprehend | Detects the dominant language in text inputs |
| Amazon SES | Emails the generated report to participants |
| AgentCore | Drives the autonomous workflow and exposes the agent to users |

---

## Tech Stack
- Python 3.10 (AWS Lambda runtime)
- Amazon Bedrock (Claude 3 Sonnet)
- AgentCore
- Amazon S3, Transcribe, Translate, Comprehend, SES
- boto3 / botocore
- AWS CLI for deployment scripts

---

## Repository Structure
```
ai-meeting-notes-agent/
├── agent_manifest.json          # Agent metadata and schemas for AgentCore
├── agentcore/flow_definition.yaml # AgentCore flow pointing to the Lambda action
├── infra/
│   ├── deploy.sh                # Packaging and deployment helper
│   ├── lambda-trust-policy.json # Assume-role trust policy for Lambda
│   └── lambda-execution-policy.json # Inline permissions used by deploy.sh
├── lambda/
│   └── summarize_and_send.py    # Main Lambda handler
├── prompts/
│   └── summarize_prompt.txt     # Prompt template consumed by the Lambda
├── local_test.py                # Bedrock + SES smoke test for transcripts
├── send_email.py                # Reusable SES helper with SKIP_EMAIL guard
├── event.json                   # Sample payload for a video meeting
├── requirements.txt             # Python dependencies
├── sample_transcript.txt        # Transcript used by local_test.py
├── .env.example                 # Suggested environment variables
├── diagram.drawio               # Editable architecture diagram
├── diagram.svg                  # Ready-to-use architecture graphic
├── frontend/                    # React demo web app for the hackathon
└── backend/                     # FastAPI service powering the demo endpoints
```

---

## Prerequisites
- Python 3.10+
- AWS CLI configured with credentials that can manage Lambda, IAM, S3, Bedrock, Transcribe, Translate, Comprehend, and SES
- An AWS account with Bedrock access to Claude 3 Sonnet and SES identities verified (sender and recipients)

---

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Update values before running
```

---

## Environment Variables
Define these variables in `.env`, the Lambda console, and AgentCore as appropriate:

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_REGION` | ✅ | Region where Bedrock/Transcribe/Translate/Comprehend/SES are available |
| `SENDER_EMAIL` | ✅ | Verified SES email address used to send the report |
| `SKIP_EMAIL` | ➖ | Set to `1` to disable SES sends during local tests |
| `TRANSCRIBE_JOB_PREFIX` | ➖ | Prefix applied to Transcribe job names (defaults to `meeting-notes-agent`) |
| `TRANSCRIBE_TIMEOUT` | ➖ | Maximum wait time in seconds for Transcribe jobs (defaults to 900) |
| `TRANSCRIBE_OUTPUT_BUCKET` | ➖ | S3 bucket for Transcribe outputs; leave empty to use the service-managed bucket |
| `PROMPT_TEMPLATE_PATH` | ➖ | Optional override pointing to a custom prompt template |
| `TARGET_LANGUAGE` | ➖ | Used by `local_test.py` to request translation (for example `fr`) |
| `DEFAULT_EMAIL_LOCALE` | ➖ | Default locale for email templates (defaults to `en`) |
| `EMAIL_SUBJECT_<LOCALE>`, `EMAIL_GREETING_<LOCALE>`, `EMAIL_INTRO_<LOCALE>`, `EMAIL_SUMMARY_HEADING_<LOCALE>`, `EMAIL_CLOSING_<LOCALE>`, `EMAIL_META_DETECTED_<LOCALE>`, `EMAIL_META_TRANSLATED_<LOCALE>` | ➖ | Optional overrides for localized email copy (example: `EMAIL_SUBJECT_FR="Résumé automatique"`) |

---

## Localization
- Email locale is resolved in this order: `email_locale` from the event payload → `target_language` (when translation succeeds) → detected transcript language → `DEFAULT_EMAIL_LOCALE` (fallback to `en`).
- Each locale uses reusable copy for subject, greeting, intro, summary heading, closing, and metadata (detected/translated language). Override any string via the environment variables listed above.
- Emails ship as both plain text and HTML. The HTML view preserves line breaks and highlights the summary in a `<pre>` block for readability.
- To introduce a new locale, extend `lambda/email_templates.py` with localized text and deploy.

---

## Deployment
1. Review `infra/lambda-execution-policy.json` and replace wildcard resources with the exact ARNs for your environment (S3 buckets, SES identities, etc.).
2. Run the deployment helper:
   ```bash
   chmod +x infra/deploy.sh
   ./infra/deploy.sh
   ```
   The script packages the Lambda together with the prompt template, applies the execution policy to the IAM role, and sets a 15-minute function timeout to accommodate long transcriptions.

2. For the asynchronous Step Functions pipeline, package each Lambda task before uploading the ZIPs:
   ```bash
   ./infra/package_async_lambdas.sh
   ```
   The artifacts are written to `dist/lambdas/` with one ZIP per task (`acquire_transcript.zip`, `summarize_task.zip`, etc.). You can publish them individually through your IaC stack or the console.

---

## Local Testing
```bash
export SKIP_EMAIL=1            # Avoid SES sends during tests
export TARGET_LANGUAGE=fr      # Optional translation target
# export EMAIL_LOCALE=fr       # Optional explicit email locale override
python local_test.py
```
The script prints the summary generated by Bedrock and either sends (or skips) the SES email depending on the `SKIP_EMAIL` flag.

---

## Demo Frontend (React)
The `frontend/` directory contains a lightweight React + Vite application tailored for the hackathon demo. It lets judges upload transcripts or recordings, choose target/email languages, submit participant emails, and monitor processing status.

### Quick start
```bash
cd frontend
npm install
npm run dev
```

The development server proxies `/api/*` requests to `http://localhost:4000` (configurable in `vite.config.ts`). Adjust the target to match your API Gateway / AppSync endpoint or local mock.

### Expected backend endpoints
- `POST /api/presign` → returns `{ uploadUrl, objectKey, fields? }` for S3 uploads
- `POST /api/jobs` → accepts the job payload and starts the Step Functions pipeline
- `GET /api/jobs/{id}` → returns job status plus summary once available

Implement these routes using API Gateway + Lambda (or AppSync) backed by DynamoDB/Step Functions to mirror the workflow from the README. The React app polls `/api/jobs/{id}` until status reaches `COMPLETED` or `FAILED`.

The frontend ships with a custom gradient logo (`frontend/public/logo.svg`) and polished styling for presentation-ready demos.

---

## Demo Backend (FastAPI)
The `backend/` directory contains a FastAPI application that implements the `/api` endpoints expected by the frontend.

### Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
export UPLOAD_BUCKET=your-upload-bucket
export SUMMARY_STATE_MACHINE_ARN=arn:aws:states:region:account:stateMachine:MeetingNotesPipeline
export RESULTS_TABLE=meeting-notes-jobs
uvicorn app:app --reload --host 0.0.0.0 --port 4000
```

The service requires AWS credentials with access to S3 (uploads), Step Functions (`states:StartExecution`), and DynamoDB (job storage). The frontend’s proxy sends `/api/*` calls to this server during development.

---

## Sample Agent Invocation
`event.json` demonstrates how to run the Lambda on a video meeting:
```json
{
  "bucket": "ai-meeting-transcripts",
  "key": "media/q1_allhands.mp4",
  "content_type": "video",
  "target_language": "en",
  "email_locale": "en",
  "participants": [
    "participant1@example.com",
    "participant2@example.com"
  ]
}
```

---

## Production Checklist
- **IAM:** Ensure the Lambda roles include permissions for `s3:GetObject`, `bedrock:InvokeModel`, `transcribe:StartTranscriptionJob`, `transcribe:GetTranscriptionJob`, `translate:TranslateText`, `comprehend:DetectDominantLanguage`, SES delivery, DynamoDB writes, and that the Step Functions role can invoke each Lambda. Scope the ARNs to your resources where possible.
- **SES:** Verify the sender domain/address and recipient emails (or move the account out of the SES sandbox).
- **Transcribe/Translate Access:** Confirm the services are enabled in the target region and quotas cover the expected workload.
- **AgentCore:** Register the updated `agent_manifest.json`, point the flow step to the Step Functions pipeline entry point, and expose the desired outputs.
- **End-to-End Test:** Upload a transcript or media file, trigger the agent, confirm the detected/final languages, and verify that emails send successfully when `SKIP_EMAIL` is disabled.

---

## Contact
Project maintained by Laurent Goulenok for the AWS AI Agent Hackathon 2025. Reach out at `laurentgoulenok@gmail.com` for questions or collaboration opportunities.




# Hackathon Demo Frontend

React + Vite single-page app to showcase the AI Meeting Notes Agent.

## Prerequisites
- Node.js 18+
- Backend endpoints (API Gateway/AppSync) exposing:
  - `POST /api/presign`
  - `POST /api/jobs`
  - `GET /api/jobs/{id}`

## Getting Started
```bash
npm install
npm run dev
```

The dev server proxies `/api` calls to `http://localhost:4000`. Update `vite.config.ts` if your backend lives elsewhere.

## Build
```bash
npm run build
```

Outputs static assets under `dist/`, deployable to S3 + CloudFront or Amplify Hosting.

## Customization
- Update `src/components/UploadForm.tsx` to tweak form fields.
- Adjust branding/styling in `src/styles.css` and `public/logo.svg`.
- Extend `src/lib/api.ts` if you add new backend routes.