import json
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from database import models
from repositories.chat_repository import ChatRepository
from repositories.document_repository import DocumentRepository
from repositories.user_repository import UserRepository
from services.chat.chat_service import ensure_chat_scope_allowed, normalize_chat_scope
from services.chat.context_service import build_recent_chat_history, split_accessible_attachments_by_index_status
from services.jobs import job_service


class JobHandler(ABC):
    def __init__(self, db: Session):
        self.db = db
        self.documents = DocumentRepository(db)
        self.chat = ChatRepository(db)
        self.users = UserRepository(db)

    @abstractmethod
    def run(self, job: models.BackgroundJob) -> None:
        """Execute one claimed background job."""


class IndexDocumentJobHandler(JobHandler):
    def run(self, job: models.BackgroundJob) -> None:
        from rag_engine.chroma_manager import ChromaDBManager

        doc = self.documents.get(job.document_id)
        if not doc or doc.is_deleted:
            raise ValueError("Tai lieu khong ton tai hoac da bi xoa")

        payload = job_service.payload_for(job)
        force_admin_chunking = bool(payload.get("force_admin_chunking"))
        scope = doc.scope.value if hasattr(doc.scope, "value") else str(doc.scope)
        ext = (doc.filename or "").lower()
        manager = ChromaDBManager()

        job_service.update_progress(self.db, job, 20)
        if ext.endswith(".pdf"):
            chunks = manager.process_and_store_pdf(
                doc.file_path,
                doc.id,
                doc.owner_id or 0,
                doc.department_id or -1,
                scope,
                "",
                doc.chat_session_id,
                force_admin_chunking,
            )
        elif ext.endswith((".docx", ".doc")):
            chunks = manager.process_and_store_word(
                doc.file_path,
                doc.id,
                doc.owner_id or 0,
                doc.department_id or -1,
                scope,
                "",
                doc.chat_session_id,
                force_admin_chunking,
            )
        else:
            raise ValueError("Dinh dang file chua ho tro index")

        doc.is_indexed = True
        self.documents.commit()
        job_service.mark_success(self.db, job, {"doc_id": doc.id, "chunks": chunks})


class ChatAnswerJobHandler(JobHandler):
    WAITING_ATTACHMENT_MESSAGE = (
        "Tài liệu đính kèm chưa index xong nên tôi chưa thể đọc nội dung để trả lời.\n\n"
        "Vui lòng đợi trạng thái tài liệu chuyển sang \"Đã index\" rồi hỏi lại."
    )

    def run(self, job: models.BackgroundJob) -> None:
        from rag_engine.chroma_manager import ChromaDBManager
        from rag_engine.ollama_ai import OllamaAI

        payload = job_service.payload_for(job)
        question = payload.get("question", "")
        scope = payload.get("scope", "personal")
        user_id = job.created_by
        user_model, session, ai_message = self._load_job_state(job, user_id)

        normalized_scope = normalize_chat_scope(scope)
        ensure_chat_scope_allowed(user_model, normalized_scope)

        chat_history = build_recent_chat_history(self.db, session.id, exclude_message_id=ai_message.id)
        attached_doc_ids, attached_waiting = split_accessible_attachments_by_index_status(
            self.db, user_model, session.id
        )

        if attached_waiting and not attached_doc_ids:
            self._finish_waiting_for_attachments(job, ai_message, session, attached_waiting)
            return

        job_service.update_progress(self.db, job, 25)
        manager = ChromaDBManager()
        context, sources = manager.search_context_with_filter(
            query=question,
            user_id=user_id,
            user_dept_id=user_model.department_id if user_model.department_id is not None else -1,
            search_scope=normalized_scope,
            session_id=session.id if normalized_scope == "personal" else None,
            extra_doc_ids=attached_doc_ids if attached_doc_ids else None,
        )

        job_service.update_progress(self.db, job, 60)
        answer = OllamaAI().generate_answer(question, context, chat_history)

        job_service.update_progress(self.db, job, 90)
        ai_message.content = answer
        ai_message.sources = json.dumps(sources, ensure_ascii=False)
        self.chat.commit()
        job_service.mark_success(
            self.db,
            job,
            {
                "answer": answer,
                "sources": sources,
                "session_id": session.id,
                "message_id": ai_message.id,
                "attached_docs": len(attached_doc_ids),
            },
        )

    def _load_job_state(
        self,
        job: models.BackgroundJob,
        user_id: int,
    ) -> tuple[models.User, models.ChatSession, models.ChatMessage]:
        user_model = self.users.get(user_id)
        session = self.chat.get_session(job.session_id, user_id)
        ai_message = self.chat.get_message(job.message_id, job.session_id)
        if not user_model or not session or not ai_message:
            raise ValueError("Du lieu chat job khong hop le")
        return user_model, session, ai_message

    def _finish_waiting_for_attachments(
        self,
        job: models.BackgroundJob,
        ai_message: models.ChatMessage,
        session: models.ChatSession,
        attached_waiting: list[str],
    ) -> None:
        answer = self.WAITING_ATTACHMENT_MESSAGE
        ai_message.content = answer
        ai_message.sources = "[]"
        self.chat.commit()
        job_service.mark_success(
            self.db,
            job,
            {
                "answer": answer,
                "sources": [],
                "session_id": session.id,
                "message_id": ai_message.id,
                "attached_docs": 0,
                "waiting_attachments": attached_waiting,
            },
        )


class JobDispatcher:
    def __init__(self, db: Session):
        self.db = db
        self.handlers: dict[str, JobHandler] = {
            job_service.JOB_TYPE_INDEX_DOCUMENT: IndexDocumentJobHandler(db),
            job_service.JOB_TYPE_CHAT_ANSWER: ChatAnswerJobHandler(db),
        }

    def dispatch(self, job: models.BackgroundJob) -> None:
        handler = self.handlers.get(job.type)
        if not handler:
            raise ValueError(f"Unsupported job type: {job.type}")
        handler.run(job)
