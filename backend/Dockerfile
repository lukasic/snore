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

RUN echo "GIT_COMMIT_HASH = '${GIT_COMMIT_SHORT_SHA}'" > /app/app/version.py && \
    echo "GIT_COMMIT_TIME = '${GIT_COMMIT_TIME}'" >> /app/app/version.py && \
    echo "GIT_COMMIT_INFO = '${GIT_COMMIT_INFO}'" >> /app/app/version.py && \
    echo "GIT_COMMIT_BRANCH = '${GIT_COMMIT_BRANCH}'" >> /app/app/version.py && \
    echo "GIT_COMMIT_COUNT = '${GIT_COMMIT_COUNT}'" >> /app/app/version.py && \
    echo "PIPELINE_ID = '${GITLAB_PIPELINE_ID}'" >> /app/app/version.py && \
    echo "ENVIRONMENT = 'production'" >> /app/app/version.py

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
