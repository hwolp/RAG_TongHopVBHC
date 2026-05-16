import traceback

from database import models
from database.db_config import SessionLocal
from services.jobs import job_service
from services.jobs.handlers import ChatAnswerJobHandler, IndexDocumentJobHandler, JobDispatcher


def _set_chat_message_failed(db, job: models.BackgroundJob, error: str) -> None:
    if job.type != job_service.JOB_TYPE_CHAT_ANSWER or not job.message_id:
        return
    ai_message = db.query(models.ChatMessage).filter(
        models.ChatMessage.id == job.message_id,
    ).first()
    if not ai_message:
        return

    clean_error = (error or "Không rõ lỗi.").strip()
    ai_message.content = f"Xử lý AI thất bại.\n\n{clean_error}"
    ai_message.sources = "[]"
    db.commit()


def run_job(job_id: int, db=None) -> None:
    owns_session = db is None
    db = db or SessionLocal()
    try:
        job = job_service.claim_for_run(db, job_id)
        if not job:
            return

        JobDispatcher(db).dispatch(job)
    except Exception as exc:
        job = db.query(models.BackgroundJob).filter(models.BackgroundJob.id == job_id).first()
        if job:
            error = f"{exc}\n{traceback.format_exc()}"
            _set_chat_message_failed(db, job, str(exc))
            job_service.mark_failed(db, job, error)
    finally:
        if owns_session:
            db.close()


def _run_index_document(db, job: models.BackgroundJob) -> None:
    """Backward-compatible test hook; new code dispatches through JobDispatcher."""
    IndexDocumentJobHandler(db).run(job)


def _run_chat_answer(db, job: models.BackgroundJob) -> None:
    """Backward-compatible test hook; new code dispatches through JobDispatcher."""
    ChatAnswerJobHandler(db).run(job)
