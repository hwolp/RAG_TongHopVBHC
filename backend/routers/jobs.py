from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.db_config import get_db
from middleware.auth_middleware import get_current_user
from services import job_service


router = APIRouter(prefix="/jobs", tags=["Background jobs"])


@router.get("")
def list_jobs(
    status: str | None = None,
    type: str | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return job_service.list_jobs(db, user, status, type)


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return job_service.get_job(db, job_id, user)
