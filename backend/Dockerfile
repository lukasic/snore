# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

ARG GIT_COMMIT_SHORT_SHA
ARG GIT_COMMIT_TIME
ARG GIT_COMMIT_INFO
ARG GIT_COMMIT_BRANCH
ARG GIT_COMMIT_COUNT
ARG GITLAB_PIPELINE_ID

RUN python3 - <<'EOF'
import os
q = lambda s: repr(str(s))
lines = [
    "GIT_COMMIT_HASH = " + q(os.environ.get("GIT_COMMIT_SHORT_SHA", "dev")),
    "GIT_COMMIT_TIME = " + q(os.environ.get("GIT_COMMIT_TIME", "")),
    "GIT_COMMIT_INFO = " + q(os.environ.get("GIT_COMMIT_INFO", "")),
    "GIT_COMMIT_BRANCH = " + q(os.environ.get("GIT_COMMIT_BRANCH", "local")),
    "GIT_COMMIT_COUNT = " + q(os.environ.get("GIT_COMMIT_COUNT", "0")),
    "PIPELINE_ID = " + q(os.environ.get("GITLAB_PIPELINE_ID", "")),
    "ENVIRONMENT = " + q("production"),
]
open("/app/app/version.py", "w").write("\n".join(lines) + "\n")
EOF

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
