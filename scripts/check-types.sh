#!/usr/bin/env bash
# Fails if the website's types no longer match the backend's Pydantic models.
# Fix by running this script and committing the two changed files.
set -euo pipefail
cd "$(dirname "$0")/.."
python backend/scripts/export_openapi.py
(cd frontend && npm run -s types:gen)
if ! git diff --exit-code -- frontend/types/openapi.json frontend/types/api.gen.ts; then
  echo "Trip types changed in the backend. Commit frontend/types/openapi.json and api.gen.ts." >&2
  exit 1
fi
echo "Frontend types match the backend."
