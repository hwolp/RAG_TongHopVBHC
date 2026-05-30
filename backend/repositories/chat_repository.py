from __future__ import annotations

from sqlalchemy.orm import Session

from database import models


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_session(self, session_id: int, user_id: int | None = None) -> models.ChatSession | None:
        query = self.db.query(models.ChatSession).filter(models.ChatSession.id == session_id)
        if user_id is not None:
            query = query.filter(models.ChatSession.user_id == user_id)
        return query.first()

    def count_sessions(self, user_id: int) -> int:
        return self.db.query(models.ChatSession).filter(models.ChatSession.user_id == user_id).count()

    def create_session(self, user_id: int, title: str) -> models.ChatSession:
        session = models.ChatSession(user_id=user_id, title=title)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def list_sessions(self, user_id: int) -> list[models.ChatSession]:
        return (
            self.db.query(models.ChatSession)
            .filter(models.ChatSession.user_id == user_id)
            .order_by(models.ChatSession.created_at.desc())
            .all()
        )

    def list_messages(self, session_id: int) -> list[models.ChatMessage]:
        session = self.db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
        return list(session.messages) if session else []

    def list_recent_messages(
        self,
        session_id: int,
        limit: int,
        exclude_message_id: int | None = None,
    ) -> list[models.ChatMessage]:
        query = self.db.query(models.ChatMessage).filter(models.ChatMessage.session_id == session_id)
        if exclude_message_id is not None:
            query = query.filter(models.ChatMessage.id != exclude_message_id)
        return query.order_by(models.ChatMessage.id.desc()).limit(limit).all()

    def list_messages_before(
        self,
        session_id: int,
        limit: int,
        before_id: int | None = None,
    ) -> list[models.ChatMessage]:
        query = self.db.query(models.ChatMessage).filter(models.ChatMessage.session_id == session_id)
        if before_id is not None:
            query = query.filter(models.ChatMessage.id < before_id)
        return query.order_by(models.ChatMessage.id.desc()).limit(limit).all()

    def get_message(self, message_id: int, session_id: int | None = None) -> models.ChatMessage | None:
        query = self.db.query(models.ChatMessage).filter(models.ChatMessage.id == message_id)
        if session_id is not None:
            query = query.filter(models.ChatMessage.session_id == session_id)
        return query.first()

    def get_message_for_user(self, message_id: int, user_id: int) -> models.ChatMessage | None:
        return (
            self.db.query(models.ChatMessage)
            .join(models.ChatSession)
            .filter(models.ChatMessage.id == message_id, models.ChatSession.user_id == user_id)
            .first()
        )

    def list_saved_prompts(self, user_id: int) -> list[models.SavedPrompt]:
        return self.db.query(models.SavedPrompt).filter(models.SavedPrompt.user_id == user_id).all()

    def get_saved_prompt(self, user_id: int, prompt_id: int) -> models.SavedPrompt | None:
        return (
            self.db.query(models.SavedPrompt)
            .filter(models.SavedPrompt.id == prompt_id, models.SavedPrompt.user_id == user_id)
            .first()
        )

    def get_attachment(self, session_id: int, doc_id: int) -> models.SessionDocAttachment | None:
        return (
            self.db.query(models.SessionDocAttachment)
            .filter(
                models.SessionDocAttachment.session_id == session_id,
                models.SessionDocAttachment.doc_id == doc_id,
            )
            .first()
        )

    def list_attachments(self, session_id: int) -> list[models.SessionDocAttachment]:
        return (
            self.db.query(models.SessionDocAttachment)
            .filter(models.SessionDocAttachment.session_id == session_id)
            .all()
        )

    def add(self, item):
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_many(self, items: list) -> None:
        self.db.add_all(items)
        self.db.commit()

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, item) -> None:
        self.db.refresh(item)

    def delete(self, item) -> None:
        self.db.delete(item)
        self.db.commit()
