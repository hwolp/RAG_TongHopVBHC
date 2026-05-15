import logging
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor

from sqlalchemy import case

from database import models
from database.db_config import SessionLocal


_started = False
_start_lock = threading.Lock()


def _env_enabled(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _queued_job_ids(limit: int, exclude_ids: set[int] | None = None) -> list[int]:
    db = SessionLocal()
    try:
        query = db.query(models.BackgroundJob.id).filter(
            models.BackgroundJob.status == "queued",
        )
        if exclude_ids:
            query = query.filter(~models.BackgroundJob.id.in_(exclude_ids))
        priority = case(
            (models.BackgroundJob.type == "chat_answer", 0),
            else_=1,
        )
        rows = query.order_by(priority, models.BackgroundJob.created_at.asc()).limit(limit).all()
        return [row[0] for row in rows]
    finally:
        db.close()


def _log_finished_job(job_id: int, future: Future) -> None:
    try:
        future.result()
    except Exception:
        logging.exception("Internal background job %s crashed outside run_job", job_id)


def _worker_loop(interval_seconds: float, batch_size: int, worker_count: int) -> None:
    from services.job_worker import run_job

    in_flight: dict[int, Future] = {}
    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="rag-job") as executor:
        while True:
            try:
                finished_ids = [job_id for job_id, future in in_flight.items() if future.done()]
                for job_id in finished_ids:
                    _log_finished_job(job_id, in_flight.pop(job_id))

                free_slots = max(0, worker_count - len(in_flight))
                if free_slots:
                    for job_id in _queued_job_ids(min(batch_size, free_slots), set(in_flight)):
                        in_flight[job_id] = executor.submit(run_job, job_id)
            except Exception:
                logging.exception("Internal background worker loop failed")
            time.sleep(interval_seconds)


def start_internal_worker() -> None:
    global _started
    if not _env_enabled("ENABLE_INTERNAL_JOB_WORKER", True):
        return

    with _start_lock:
        if _started:
            return
        _started = True

        interval_seconds = float(os.getenv("INTERNAL_JOB_WORKER_INTERVAL_SECONDS", "2"))
        batch_size = int(os.getenv("INTERNAL_JOB_WORKER_BATCH_SIZE", "3"))
        worker_count = max(1, int(os.getenv("INTERNAL_JOB_WORKER_COUNT", "2")))
        thread = threading.Thread(
            target=_worker_loop,
            args=(interval_seconds, batch_size, worker_count),
            name="internal-background-worker",
            daemon=True,
        )
        thread.start()
