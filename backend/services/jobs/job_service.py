import json
import logging
import os
import time
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from config import REDIS_URL, RQ_QUEUE_NAME
from database import models
from repositories.job_repository import BackgroundJobRepository
from utils.time_utils import utc_now


JOB_TYPE_INDEX_DOCUMENT = "index_document"
JOB_TYPE_CHAT_ANSWER = "chat_answer"

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
TERMINAL_STATUSES = {STATUS_SUCCESS, STATUS_FAILED}


def _env_enabled(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def serialize_job(job: models.BackgroundJob) -> dict:
    return {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "progress": job.progress or 0,
        "created_by": job.created_by,
        "document_id": job.document_id,
        "session_id": job.session_id,
        "message_id": job.message_id,
        "result": _json_loads(job.result, None),
        "error": job.error,
        "created_at": str(job.created_at),
        "updated_at": str(job.updated_at),
        "finished_at": str(job.finished_at) if job.finished_at else None,
    }


def enqueue_job(job_id: int) -> bool:
    try:
        from redis import Redis
        from rq import Queue

        redis_connection = Redis.from_url(REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        queue = Queue(RQ_QUEUE_NAME, connection=redis_connection)
        queue.enqueue("services.jobs.worker.run_job", job_id, job_timeout="30m")
        return True
    except Exception as exc:
        if _env_enabled("ENABLE_INTERNAL_JOB_WORKER", True):
            logging.info(
                "Could not enqueue background job %s to Redis; internal worker will pick it up: %s",
                job_id,
                exc,
            )
        else:
            logging.warning("Could not enqueue background job %s: %s", job_id, exc)
        return False


def create_job(
    db: Session,
    job_type: str,
    created_by: int | None,
    document_id: int | None = None,
    session_id: int | None = None,
    message_id: int | None = None,
    payload: dict | None = None,
    auto_enqueue: bool = True,
) -> models.BackgroundJob:
    job = models.BackgroundJob(
        type=job_type,
        status=STATUS_QUEUED,
        progress=0,
        created_by=created_by,
        document_id=document_id,
        session_id=session_id,
        message_id=message_id,
        payload=_json_dumps(payload or {}),
    )
    BackgroundJobRepository(db).add(job)
    if auto_enqueue:
        enqueue_job(job.id)
    return job


def create_index_job(
    db: Session,
    doc: models.Document,
    created_by: int | None,
    force_admin_chunking: bool = False,
) -> models.BackgroundJob | None:
    ext = (doc.filename or "").lower()
    if not ext.endswith((".pdf", ".docx", ".doc")):
        return None
    return create_job(
        db=db,
        job_type=JOB_TYPE_INDEX_DOCUMENT,
        created_by=created_by,
        document_id=doc.id,
        payload={"force_admin_chunking": force_admin_chunking},
    )


def mark_running(db: Session, job: models.BackgroundJob, progress: int = 5) -> None:
    job.status = STATUS_RUNNING
    job.progress = progress
    job.error = None
    BackgroundJobRepository(db).commit()


def claim_for_run(db: Session, job_id: int) -> models.BackgroundJob | None:
    return BackgroundJobRepository(db).claim_for_run(job_id, STATUS_QUEUED, STATUS_RUNNING)


def update_progress(db: Session, job: models.BackgroundJob, progress: int, result: dict | None = None) -> None:
    job.progress = progress
    job.updated_at = utc_now()
    if result is not None:
        job.result = _json_dumps(result)
    BackgroundJobRepository(db).commit()


def mark_success(db: Session, job: models.BackgroundJob, result: dict | None = None) -> None:
    now = utc_now()
    job.status = STATUS_SUCCESS
    job.progress = 100
    job.error = None
    job.result = _json_dumps(result or {})
    job.updated_at = now
    job.finished_at = now
    BackgroundJobRepository(db).commit()


def mark_failed(db: Session, job: models.BackgroundJob, error: str) -> None:
    now = utc_now()
    job.status = STATUS_FAILED
    job.progress = max(job.progress or 0, 100)
    job.error = error
    job.updated_at = now
    job.finished_at = now
    BackgroundJobRepository(db).commit()


def get_job(db: Session, job_id: int, user: dict) -> dict:
    job = _require_visible_job(db, job_id, user)
    return serialize_job(job)


def wait_for_job(
    db: Session,
    job_id: int,
    user: dict,
    timeout_seconds: int = 600,
    interval_seconds: float = 1.0,
) -> dict:
    deadline = time.monotonic() + max(1, min(timeout_seconds, 1800))
    safe_interval = max(0.2, min(interval_seconds, 5.0))

    while True:
        db.rollback()
        db.expire_all()
        job = _require_visible_job(db, job_id, user)
        if job.status in TERMINAL_STATUSES or time.monotonic() >= deadline:
            return serialize_job(job)
        time.sleep(safe_interval)


def _require_visible_job(db: Session, job_id: int, user: dict) -> models.BackgroundJob:
    job = BackgroundJobRepository(db).get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job khong ton tai")
    if user.get("role") != "admin" and job.created_by != user.get("id"):
        raise HTTPException(status_code=403, detail="Khong co quyen xem job nay")
    return job


def list_jobs(
    db: Session,
    user: dict,
    status: str | None = None,
    job_type: str | None = None,
) -> list[dict]:
    jobs = BackgroundJobRepository(db).list_for_user(user, status, job_type)
    return [serialize_job(job) for job in jobs]


def payload_for(job: models.BackgroundJob) -> dict:
    return _json_loads(job.payload, {}) or {}
