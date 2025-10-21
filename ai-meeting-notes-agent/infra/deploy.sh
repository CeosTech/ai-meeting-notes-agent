#!/bin/bash

# 🚀 Configuration
LAMBDA_NAME="meeting-notes-lambda"
ROLE_NAME="meeting-notes-lambda-role"
HANDLER="summarize_and_send.lambda_handler"
RUNTIME="python3.10"
ZIP_FILE="lambda.zip"
REGION="us-east-1"  # Change this to your desired region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
FUNCTION_TIMEOUT=900
INLINE_POLICY_NAME="meeting-notes-lambda-inline"

set -euo pipefail

echo "🔁 Packaging Lambda code..."
TMP_DIR=$(mktemp -d)
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

cp -R lambda/. "$TMP_DIR"/
mkdir -p "$TMP_DIR/prompts"
cp prompts/summarize_prompt.txt "$TMP_DIR/prompts/"

(cd "$TMP_DIR" && zip -r "$OLDPWD/$ZIP_FILE" . >/dev/null)

echo "🔍 Checking if IAM role exists..."
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null)

if [ -z "$ROLE_ARN" ]; then
  echo "🔨 Creating IAM role $ROLE_NAME..."
  aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file://infra/lambda-trust-policy.json

  echo "🔗 Attaching AWSLambdaBasicExecutionRole..."
  aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

  sleep 10  # Give IAM some time to propagate

  ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
else
  echo "✅ IAM role already exists: $ROLE_ARN"
fi

echo "🛡️ Updating inline permissions policy..."
aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name $INLINE_POLICY_NAME \
  --policy-document file://infra/lambda-execution-policy.json

echo "🚀 Deploying Lambda function: $LAMBDA_NAME"

# Check if the function exists
if aws lambda get-function --function-name $LAMBDA_NAME 2>/dev/null; then
  echo "🔁 Updating existing Lambda..."
  aws lambda update-function-code \
    --function-name $LAMBDA_NAME \
    --zip-file fileb://$ZIP_FILE

  echo "⚙️ Updating Lambda configuration (timeout=$FUNCTION_TIMEOUT s)..."
  aws lambda update-function-configuration \
    --function-name $LAMBDA_NAME \
    --timeout $FUNCTION_TIMEOUT

else
  echo "🆕 Creating new Lambda function..."
  aws lambda create-function \
    --function-name $LAMBDA_NAME \
    --runtime $RUNTIME \
    --role $ROLE_ARN \
    --handler $HANDLER \
    --zip-file fileb://$ZIP_FILE \
    --timeout $FUNCTION_TIMEOUT \
    --region $REGION
fi

echo "✅ Lambda '$LAMBDA_NAME' is deployed."
