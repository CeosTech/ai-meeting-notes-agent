# Backend API

FastAPI service that exposes the endpoints consumed by the React demo frontend.

## Endpoints
- `POST /api/presign` — returns S3 presigned POST data to upload meeting assets.
- `POST /api/jobs` — enqueues a Step Functions execution and writes an initial job record.
- `GET /api/jobs/{id}` — retrieves the stored job payload (status, summary, metadata).
- `GET /-/health` — basic health check.

## Required environment variables
- `UPLOAD_BUCKET` — S3 bucket where files are uploaded.
- `SUMMARY_STATE_MACHINE_ARN` — ARN of the Step Functions state machine orchestrating the pipeline.
- `RESULTS_TABLE` — DynamoDB table (partition key `id`) used to persist job status.
- `DEFAULT_TARGET_LANGUAGE` *(optional)* — fallback target language when frontend does not supply one.
- `DEFAULT_EMAIL_LOCALE` *(optional)* — fallback locale for localized email templates.

AWS credentials must allow the API to call S3, Step Functions (`states:StartExecution`), and DynamoDB.

## Local development
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 4000
```

The frontend `vite.config.ts` proxies `/api` to `http://localhost:4000` by default.
