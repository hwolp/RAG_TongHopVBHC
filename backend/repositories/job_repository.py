from __future__ import annotations

from sqlalchemy import case
from sqlalchemy.orm import Session

from database import models
from utils.time_utils import utc_now


class BackgroundJobRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, job_id: int) -> models.BackgroundJob | None:
        return self.db.query(models.BackgroundJob).filter(models.BackgroundJob.id == job_id).first()

    def latest_for_document(self, doc_id: int, job_type: str) -> models.BackgroundJob | None:
        return (
            self.db.query(models.BackgroundJob)
            .filter(
                models.BackgroundJob.document_id == doc_id,
                models.BackgroundJob.type == job_type,
            )
            .order_by(models.BackgroundJob.created_at.desc())
            .first()
        )

    def latest_active_for_document(
        self,
        doc_id: int,
        job_type: str,
        statuses: list[str],
    ) -> models.BackgroundJob | None:
        return (
            self.db.query(models.BackgroundJob)
            .filter(
                models.BackgroundJob.document_id == doc_id,
                models.BackgroundJob.type == job_type,
                models.BackgroundJob.status.in_(statuses),
            )
            .order_by(models.BackgroundJob.created_at.desc())
            .first()
        )

    def list_for_user(
        self,
        user: dict,
        status: str | None = None,
        job_type: str | None = None,
        limit: int = 100,
    ) -> list[models.BackgroundJob]:
        query = self.db.query(models.BackgroundJob)
        if user.get("role") != "admin":
            query = query.filter(models.BackgroundJob.created_by == user.get("id"))
        if status:
            query = query.filter(models.BackgroundJob.status == status)
        if job_type:
            query = query.filter(models.BackgroundJob.type == job_type)
        return query.order_by(models.BackgroundJob.created_at.desc()).limit(limit).all()

    def queued_job_ids(self, limit: int, exclude_ids: set[int] | None = None) -> list[int]:
        query = self.db.query(models.BackgroundJob.id).filter(models.BackgroundJob.status == "queued")
        if exclude_ids:
            query = query.filter(~models.BackgroundJob.id.in_(exclude_ids))
        priority = case(
            (models.BackgroundJob.type == "chat_answer", 0),
            else_=1,
        )
        rows = query.order_by(priority, models.BackgroundJob.created_at.asc()).limit(limit).all()
        return [row[0] for row in rows]

    def list_active_by_message(
        self,
        message_ids: list[int],
        job_type: str,
        statuses: list[str],
    ) -> list[models.BackgroundJob]:
        if not message_ids:
            return []
        return (
            self.db.query(models.BackgroundJob)
            .filter(
                models.BackgroundJob.message_id.in_(message_ids),
                models.BackgroundJob.type == job_type,
                models.BackgroundJob.status.in_(statuses),
            )
            .order_by(models.BackgroundJob.created_at.desc())
            .all()
        )

    def claim_for_run(self, job_id: int, queued_status: str, running_status: str) -> models.BackgroundJob | None:
        now = utc_now()
        claimed = (
            self.db.query(models.BackgroundJob)
            .filter(
                models.BackgroundJob.id == job_id,
                models.BackgroundJob.status == queued_status,
            )
            .update(
                {
                    "status": running_status,
                    "progress": 5,
                    "error": None,
                    "updated_at": now,
                },
                synchronize_session=False,
            )
        )
        self.db.commit()
        if not claimed:
            return None
        return self.get(job_id)

    def add(self, job: models.BackgroundJob) -> models.BackgroundJob:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def commit(self) -> None:
        self.db.commit()
