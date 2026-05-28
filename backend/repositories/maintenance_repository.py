from __future__ import annotations

from sqlalchemy.orm import Session

from database import models


class MaintenanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def clear_rag_data(self) -> dict:
        counts = {
            "background_jobs": self.db.query(models.BackgroundJob).delete(synchronize_session=False),
            "chat_messages": self.db.query(models.ChatMessage).delete(synchronize_session=False),
            "session_doc_attachments": self.db.query(models.SessionDocAttachment).delete(synchronize_session=False),
            "shared_documents": self.db.query(models.SharedDocument).delete(synchronize_session=False),
            "sqp_proposals": self.db.query(models.SQPProposal).delete(synchronize_session=False),
            "document_tags": self.db.query(models.DocumentTag).delete(synchronize_session=False),
            "document_versions": self.db.query(models.DocumentVersion).delete(synchronize_session=False),
            "documents": self.db.query(models.Document).delete(synchronize_session=False),
            "chat_sessions": self.db.query(models.ChatSession).delete(synchronize_session=False),
        }
        self.db.commit()
        return counts
