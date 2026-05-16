import json
from typing import Optional

from sqlalchemy.orm import Session

from database import models
from repositories.chat_repository import ChatRepository
from repositories.user_repository import UserRepository
from services.chat.context_service import accessible_attachment_ids, build_recent_chat_history
from services.chat.models import ChatAnswerResult, GeneratedAnswer, RetrievedContext
from services.jobs import job_service
from utils.errors import forbidden, not_found


def normalize_chat_scope(scope: str) -> str:
    return "sqp" if scope == "company" else scope


def ensure_chat_scope_allowed(user: models.User, normalized_scope: str) -> None:
    if normalized_scope == "department" and user.role == models.RoleEnum.employee:
        raise forbidden("Nhan vien chi duoc chat tren tai lieu ca nhan va tai lieu cong ty")


class ChatSessionService:
    def __init__(self, db: Session):
        self.db = db
        self.chat = ChatRepository(db)

    def get_or_create_for_question(
        self,
        user_id: int,
        question: str,
        session_id: Optional[int] = None,
        require_existing: bool = False,
    ) -> models.ChatSession:
        session = None
        if session_id:
            session = self.chat.get_session(session_id, user_id)
            if require_existing and not session:
                raise not_found("Phien khong ton tai")

        if session:
            return session
        title = question[:50] or "Phiên hội thoại mới"
        return self.chat.create_session(user_id, title)

    def create_session(self, user_id: int, title: str | None = None):
        if not title or not title.strip():
            title = f"Phiên mới {self.chat.count_sessions(user_id) + 1}"
        session = self.chat.create_session(user_id, title.strip())
        return {"id": session.id, "title": session.title, "created_at": str(session.created_at)}

    def list_sessions(self, user_id: int):
        return [
            {"id": session.id, "title": session.title, "created_at": str(session.created_at)}
            for session in self.chat.list_sessions(user_id)
        ]

    def get_session_messages(self, user_id: int, session_id: int):
        self._require_session(user_id, session_id)
        return [
            {
                "id": message.id,
                "sender": message.sender,
                "content": message.content,
                "sources": message.sources,
                "created_at": str(message.created_at),
            }
            for message in self.chat.list_messages(session_id)
        ]

    def get_session_messages_paginated(
        self,
        user_id: int,
        session_id: int,
        limit: int = 5,
        before_id: Optional[int] = None,
    ):
        self._require_session(user_id, session_id)
        safe_limit = max(1, min(limit, 50))
        query = self.db.query(models.ChatMessage).filter(models.ChatMessage.session_id == session_id)
        if before_id is not None:
            query = query.filter(models.ChatMessage.id < before_id)

        rows = query.order_by(models.ChatMessage.id.desc()).limit(safe_limit + 1).all()
        has_more = len(rows) > safe_limit
        selected = rows[:safe_limit]
        selected.reverse()
        active_jobs_by_message = self._active_jobs_by_message([message.id for message in selected])

        items = []
        for message in selected:
            item = {
                "id": message.id,
                "sender": message.sender,
                "content": message.content,
                "sources": message.sources,
                "created_at": str(message.created_at),
            }
            job = active_jobs_by_message.get(message.id)
            if job:
                item.update(
                    {
                        "job_id": job.id,
                        "job_status": job.status,
                        "job_progress": job.progress or 0,
                    }
                )
            items.append(item)

        next_before_id = items[0]["id"] if has_more and items else None
        return {"items": items, "has_more": has_more, "next_before_id": next_before_id}

    def rename_session(self, user_id: int, session_id: int, title: str):
        session = self._require_session(user_id, session_id)
        session.title = title
        self.db.commit()
        return {"status": "success"}

    def delete_session(self, user_id: int, session_id: int):
        session = self._require_session(user_id, session_id)
        self.db.delete(session)
        self.db.commit()
        return {"status": "success"}

    def _require_session(self, user_id: int, session_id: int) -> models.ChatSession:
        session = self.chat.get_session(session_id, user_id)
        if not session:
            raise not_found("Phien khong ton tai")
        return session

    def _active_jobs_by_message(self, message_ids: list[int]) -> dict[int, models.BackgroundJob]:
        if not message_ids:
            return {}
        active_jobs = self.db.query(models.BackgroundJob).filter(
            models.BackgroundJob.message_id.in_(message_ids),
            models.BackgroundJob.type == job_service.JOB_TYPE_CHAT_ANSWER,
            models.BackgroundJob.status.in_([
                job_service.STATUS_QUEUED,
                job_service.STATUS_RUNNING,
            ]),
        ).order_by(models.BackgroundJob.created_at.desc()).all()
        result = {}
        for job in active_jobs:
            result.setdefault(job.message_id, job)
        return result


class ChatAnswerService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.sessions = ChatSessionService(db)

    def ask_ai(self, user_id: int, question: str, scope: str = "personal", session_id: Optional[int] = None):
        user = self._require_user(user_id)
        normalized_scope = normalize_chat_scope(scope)
        ensure_chat_scope_allowed(user, normalized_scope)
        session = self.sessions.get_or_create_for_question(user_id, question, session_id)
        attached_doc_ids = accessible_attachment_ids(self.db, user, session.id)
        chat_history = build_recent_chat_history(self.db, session.id)
        retrieved = self._retrieve_context(user_id, user, question, normalized_scope, session.id, attached_doc_ids)
        generated = self._generate_answer(question, retrieved, chat_history)

        user_message = models.ChatMessage(session_id=session.id, sender="user", content=question)
        ai_message = models.ChatMessage(
            session_id=session.id,
            sender="ai",
            content=generated.answer,
            sources=json.dumps(generated.sources, ensure_ascii=False),
        )
        self.db.add_all([user_message, ai_message])
        self.db.commit()

        result = ChatAnswerResult(
            answer=generated.answer,
            sources=generated.sources,
            session_id=session.id,
            session_title=session.title,
            attached_docs=len(attached_doc_ids),
        )
        return result.__dict__

    def queue_ai_answer(
        self,
        user_id: int,
        question: str,
        scope: str = "personal",
        session_id: Optional[int] = None,
    ):
        user = self._require_user(user_id)
        ensure_chat_scope_allowed(user, normalize_chat_scope(scope))
        session = self.sessions.get_or_create_for_question(
            user_id, question, session_id, require_existing=bool(session_id)
        )

        user_message = models.ChatMessage(session_id=session.id, sender="user", content=question)
        ai_message = models.ChatMessage(
            session_id=session.id,
            sender="ai",
            content="Đang xử lý câu trả lời...",
            sources="[]",
        )
        self.db.add_all([user_message, ai_message])
        self.db.commit()
        self.db.refresh(user_message)
        self.db.refresh(ai_message)

        job = job_service.create_job(
            db=self.db,
            job_type=job_service.JOB_TYPE_CHAT_ANSWER,
            created_by=user_id,
            session_id=session.id,
            message_id=ai_message.id,
            payload={
                "question": question,
                "scope": scope,
                "user_message_id": user_message.id,
            },
        )
        return {
            "status": "queued",
            "job_id": job.id,
            "session_id": session.id,
            "session_title": session.title,
            "user_message_id": user_message.id,
            "ai_message_id": ai_message.id,
        }

    def _retrieve_context(
        self,
        user_id: int,
        user: models.User,
        question: str,
        normalized_scope: str,
        session_id: int,
        attached_doc_ids: list[int],
    ) -> RetrievedContext:
        from rag_engine.chroma_manager import ChromaDBManager

        manager = ChromaDBManager()
        context, sources = manager.search_context_with_filter(
            query=question,
            user_id=user_id,
            user_dept_id=user.department_id if user.department_id is not None else -1,
            search_scope=normalized_scope,
            session_id=session_id if normalized_scope == "personal" else None,
            extra_doc_ids=attached_doc_ids if attached_doc_ids else None,
        )
        return RetrievedContext(context=context, sources=sources)

    def _generate_answer(self, question: str, retrieved: RetrievedContext, chat_history: str) -> GeneratedAnswer:
        from rag_engine.ollama_ai import OllamaAI

        answer = OllamaAI().generate_answer(question, retrieved.context, chat_history)
        return GeneratedAnswer(answer=answer, sources=retrieved.sources)

    def _require_user(self, user_id: int) -> models.User:
        user = self.users.get(user_id)
        if not user:
            raise not_found("Khong tim thay nguoi dung")
        return user


class ChatPromptService:
    def __init__(self, db: Session):
        self.db = db
        self.chat = ChatRepository(db)

    def list_saved_prompts(self, user_id: int):
        return [
            {"id": prompt.id, "content": prompt.content, "created_at": str(prompt.created_at)}
            for prompt in self.chat.list_saved_prompts(user_id)
        ]

    def create_saved_prompt(self, user_id: int, content: str):
        prompt = models.SavedPrompt(user_id=user_id, content=content)
        self.db.add(prompt)
        self.db.commit()
        self.db.refresh(prompt)
        return {"status": "success", "id": prompt.id}

    def delete_saved_prompt(self, user_id: int, prompt_id: int):
        prompt = self.chat.get_saved_prompt(user_id, prompt_id)
        if not prompt:
            raise not_found("Prompt not found")
        self.db.delete(prompt)
        self.db.commit()
        return {"status": "success"}

    def get_message_citations(self, user_id: int, message_id: int):
        message = self.chat.get_message_for_user(message_id, user_id)
        if not message:
            raise not_found("Tin nhan khong ton tai")
        try:
            sources = json.loads(message.sources or "[]")
        except json.JSONDecodeError:
            sources = []
        return {"message_id": message.id, "sources": [str(source) for source in sources]}

    def execute_saved_prompt(
        self,
        user_id: int,
        prompt_id: int,
        scope: str = "personal",
        session_id: Optional[int] = None,
    ):
        prompt = self.chat.get_saved_prompt(user_id, prompt_id)
        if not prompt:
            raise not_found("Prompt not found")
        return ChatAnswerService(self.db).queue_ai_answer(user_id, prompt.content, scope, session_id)


def ask_ai(db: Session, user_id: int, question: str, scope: str = "personal", session_id: Optional[int] = None):
    return ChatAnswerService(db).ask_ai(user_id, question, scope, session_id)


def queue_ai_answer(db: Session, user_id: int, question: str, scope: str = "personal", session_id: Optional[int] = None):
    return ChatAnswerService(db).queue_ai_answer(user_id, question, scope, session_id)


def create_session(db: Session, user_id: int, title: str | None = None):
    return ChatSessionService(db).create_session(user_id, title)


def list_sessions(db: Session, user_id: int):
    return ChatSessionService(db).list_sessions(user_id)


def get_session_messages(db: Session, user_id: int, session_id: int):
    return ChatSessionService(db).get_session_messages(user_id, session_id)


def get_session_messages_paginated(
    db: Session,
    user_id: int,
    session_id: int,
    limit: int = 5,
    before_id: Optional[int] = None,
):
    return ChatSessionService(db).get_session_messages_paginated(user_id, session_id, limit, before_id)


def rename_session(db: Session, user_id: int, session_id: int, title: str):
    return ChatSessionService(db).rename_session(user_id, session_id, title)


def delete_session(db: Session, user_id: int, session_id: int):
    return ChatSessionService(db).delete_session(user_id, session_id)


def list_saved_prompts(db: Session, user_id: int):
    return ChatPromptService(db).list_saved_prompts(user_id)


def create_saved_prompt(db: Session, user_id: int, content: str):
    return ChatPromptService(db).create_saved_prompt(user_id, content)


def delete_saved_prompt(db: Session, user_id: int, prompt_id: int):
    return ChatPromptService(db).delete_saved_prompt(user_id, prompt_id)


def get_message_citations(db: Session, user_id: int, message_id: int):
    return ChatPromptService(db).get_message_citations(user_id, message_id)


def execute_saved_prompt(
    db: Session,
    user_id: int,
    prompt_id: int,
    scope: str = "personal",
    session_id: Optional[int] = None,
):
    return ChatPromptService(db).execute_saved_prompt(user_id, prompt_id, scope, session_id)
