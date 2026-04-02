from fastapi import APIRouter
from app import version

router = APIRouter(tags=["version"])


@router.get("/")
def get_version() -> dict:
    return {
        "commit_hash": version.GIT_COMMIT_HASH,
        "commit_time": version.GIT_COMMIT_TIME,
        "commit_info": version.GIT_COMMIT_INFO,
        "commit_branch": version.GIT_COMMIT_BRANCH,
        "commit_count": version.GIT_COMMIT_COUNT,
        "pipeline_id": version.PIPELINE_ID,
        "environment": version.ENVIRONMENT,
    }
