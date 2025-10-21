#!/bin/bash

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BUILD_DIR="$ROOT_DIR/dist/lambdas"
COMMON_DIR="$ROOT_DIR/lambda/common"
EMAIL_TEMPLATES="$ROOT_DIR/lambda/email_templates.py"

TASKS=(
  "acquire_transcript"
  "summarize_task"
  "translate_task"
  "send_email_task"
  "finalize_task"
  "handle_failure"
)

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

for task in "${TASKS[@]}"; do
  TASK_SRC="$ROOT_DIR/lambda/$task"
  if [ ! -d "$TASK_SRC" ]; then
    echo "⚠️  Skipping $task (directory not found)"
    continue
  fi

  TMP_DIR=$(mktemp -d)
  trap 'rm -rf "$TMP_DIR"' EXIT

  cp -R "$TASK_SRC/." "$TMP_DIR/"
  cp -R "$COMMON_DIR" "$TMP_DIR/common"
  cp "$EMAIL_TEMPLATES" "$TMP_DIR/"

  ZIP_PATH="$BUILD_DIR/${task}.zip"
  (cd "$TMP_DIR" && zip -r "$ZIP_PATH" . >/dev/null)
  echo "✅ Packaged $task → $ZIP_PATH"

  rm -rf "$TMP_DIR"
  trap - EXIT
done
