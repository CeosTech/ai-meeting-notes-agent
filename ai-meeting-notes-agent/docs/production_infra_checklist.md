# Production Infrastructure & IaC Checklist

The following steps capture the infrastructure changes required before releasing the AI Meeting Notes Agent into production. Use your preferred IaC tool (AWS CDK, Terraform, or CloudFormation/SAM) to codify each component and maintain version control.

## Core AWS Resources

- **S3 buckets**
  - `meeting-notes-uploads`: ingest bucket for transcript/audio/video uploads.  
  - `meeting-notes-artifacts` (optional): store transcription outputs, summaries, and prompt templates.  
  - Apply bucket policies to restrict access to the Lambda/Step Functions roles, enforce TLS, and configure event notifications if needed.  
  - Configure CORS for browser uploads (`POST`, `PUT`, `GET`) with allowed origins set to the frontend domain.

- **DynamoDB**
  - Table `meeting-notes-jobs` with partition key `id`.  
  - Enable point-in-time recovery.  
  - Define IAM policy statements limiting access to `dynamodb:PutItem`, `GetItem`, `UpdateItem` on this table only.

- **State machine & Lambda functions**
  - Step Functions state machine orchestrating transcription, summarization, translation, and email tasks.  
  - Individual Lambda functions (or a single orchestrator) deployed via IaC with environment variables sourced from SSM parameters.  
  - Attach log groups with retention (e.g., 30 days) and enable X-Ray tracing.

- **API layer**
  - Production FastAPI deployment (e.g., Amazon ECS Fargate, Lambda + API Gateway, or AWS App Runner).  
  - Configure environment variables via SSM Parameter Store/Secrets Manager (no plaintext `.env`).  
  - Provision ALB/API Gateway, TLS certificates (ACM), and WAF as required.  
  - Update `frontend/src/lib/api.ts` base URL through environment-driven config for prod vs. dev.

- **Frontend hosting**
  - Build artifacts deployed to Amazon S3 + CloudFront or to an SPA hosting service.  
  - Configure CloudFront cache policies, logging, and TLS certificates.

- **Email (Amazon SES)**
  - Verify sending domain and production-mode SES access.  
  - Create configuration set and monitoring for bounces/complaints.  
  - Limit IAM policy to `ses:SendEmail` on the verified identity ARN (`arn:aws:ses:region:account:identity/your-domain`).

## IAM Hardening

- Replace wildcard resources in `infra/lambda-execution-policy.json` with specific ARNs:
  - `arn:aws:s3:::meeting-notes-uploads/*`
  - `arn:aws:bedrock:REGION::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0`
  - `arn:aws:ses:REGION:ACCOUNT:identity/your-domain.com`
  - `arn:aws:dynamodb:REGION:ACCOUNT:table/meeting-notes-jobs`
  - `arn:aws:states:REGION:ACCOUNT:stateMachine:MeetingNotesPipeline`
- Create separate execution roles for:
  - Step Functions state machine (`states:StartExecution` permissions controlled from backend role).  
  - Lambda tasks (least privilege per function).  
  - API backend service (S3 presign, DynamoDB read/write, Step Functions start).  
  - CI/CD pipeline (assume role limited to deployment actions).

- Store secrets (e.g., `SENDER_EMAIL`, third-party API keys) in AWS Secrets Manager and grant read access only to the components that need them.

## Observability & Operations

- CloudWatch dashboards for:
  - Step Functions execution metrics (success/failure counts, duration).  
  - Lambda errors/throttles.  
  - SES bounce/complaint rates.  
  - DynamoDB throttles/capacity usage.
- CloudWatch alarms wired to SNS/Slack for high-priority failures.  
- Structured logging in all Lambdas and the FastAPI backend; include `job_id` in every log entry.  
- Enable AWS Backup or lifecycle rules for critical data (DynamoDB PITR, S3 versioning).  
- Set cost monitors/budgets for Bedrock, Transcribe, and SES usage.

## Deployment Pipeline

- Implement CI workflows for:
  - Running unit tests (Python + frontend) and linting on every commit.  
  - Building Lambda bundles, Docker images (if using ECS/App Runner), and frontend assets.  
  - Synthesizing/deploying IaC stacks in a staging environment before production.
- Enforce manual approval gates or automated integration tests before promoting to production.

## AgentCore Integration

- Update `agentcore/flow_definition.yaml` and `agent_manifest.json` with the final Lambda alias/ARNs.  
- Store AgentCore credentials and environment configuration in Secrets Manager.  
- Smoke-test the agent end-to-end in staging using the asynchronous pipeline before cutover.

