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

RUN python3 -c "
import sys
def q(s): return repr(str(s))
lines = [
    'GIT_COMMIT_HASH = ' + q('${GIT_COMMIT_SHORT_SHA}'),
    'GIT_COMMIT_TIME = ' + q('${GIT_COMMIT_TIME}'),
    'GIT_COMMIT_INFO = ' + q('''${GIT_COMMIT_INFO}'''),
    'GIT_COMMIT_BRANCH = ' + q('${GIT_COMMIT_BRANCH}'),
    'GIT_COMMIT_COUNT = ' + q('${GIT_COMMIT_COUNT}'),
    'PIPELINE_ID = ' + q('${GITLAB_PIPELINE_ID}'),
    'ENVIRONMENT = ' + q('production'),
]
open('/app/app/version.py', 'w').write('\n'.join(lines) + '\n')
"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
