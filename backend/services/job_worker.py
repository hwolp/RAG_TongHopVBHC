import json
import traceback

from database import models
from database.db_config import SessionLocal
from services import job_service
from services.access_policy import can_access_document


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

        if job.type == job_service.JOB_TYPE_INDEX_DOCUMENT:
            _run_index_document(db, job)
        elif job.type == job_service.JOB_TYPE_CHAT_ANSWER:
            _run_chat_answer(db, job)
        else:
            raise ValueError(f"Unsupported job type: {job.type}")
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
    from rag_engine.chroma_manager import ChromaDBManager

    doc = db.query(models.Document).filter(models.Document.id == job.document_id).first()
    if not doc or doc.is_deleted:
        raise ValueError("Tai lieu khong ton tai hoac da bi xoa")

    payload = job_service.payload_for(job)
    force_admin_chunking = bool(payload.get("force_admin_chunking"))
    scope = doc.scope.value if hasattr(doc.scope, "value") else str(doc.scope)
    ext = (doc.filename or "").lower()
    manager = ChromaDBManager()

    job_service.update_progress(db, job, 20)
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
    db.commit()
    job_service.mark_success(db, job, {"doc_id": doc.id, "chunks": chunks})


def _run_chat_answer(db, job: models.BackgroundJob) -> None:
    from rag_engine.chroma_manager import ChromaDBManager
    from rag_engine.ollama_ai import OllamaAI

    payload = job_service.payload_for(job)
    question = payload.get("question", "")
    scope = payload.get("scope", "personal")
    user_id = job.created_by
    user_model = db.query(models.User).filter(models.User.id == user_id).first()
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == job.session_id,
        models.ChatSession.user_id == user_id,
    ).first()
    ai_message = db.query(models.ChatMessage).filter(
        models.ChatMessage.id == job.message_id,
        models.ChatMessage.session_id == job.session_id,
    ).first()
    if not user_model or not session or not ai_message:
        raise ValueError("Du lieu chat job khong hop le")

    normalized_scope = "sqp" if scope == "company" else scope
    if normalized_scope == "department" and user_model.role == models.RoleEnum.employee:
        raise ValueError("Nhan vien chi duoc chat tren tai lieu ca nhan va tai lieu cong ty")

    recent_messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.session_id == session.id,
        models.ChatMessage.id != ai_message.id,
    ).order_by(models.ChatMessage.created_at.desc()).limit(10).all()
    recent_messages.reverse()
    chat_history = ""
    for message in recent_messages:
        role = "Nguoi dung" if message.sender == "user" else "AI"
        chat_history += f"{role}: {message.content}\n"

    attached_doc_ids = []
    attached_waiting = []
    for attachment in db.query(models.SessionDocAttachment).filter(
        models.SessionDocAttachment.session_id == session.id
    ).all():
        doc = db.query(models.Document).filter(models.Document.id == attachment.doc_id).first()
        if can_access_document(db, user_model, doc):
            if doc.is_indexed:
                attached_doc_ids.append(attachment.doc_id)
            else:
                attached_waiting.append(doc.filename)

    if attached_waiting and not attached_doc_ids:
        answer = (
            "Tài liệu đính kèm chưa index xong nên tôi chưa thể đọc nội dung để trả lời.\n\n"
            "Vui lòng đợi trạng thái tài liệu chuyển sang \"Đã index\" rồi hỏi lại."
        )
        ai_message.content = answer
        ai_message.sources = "[]"
        db.commit()
        job_service.mark_success(
            db,
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
        return

    job_service.update_progress(db, job, 25)
    manager = ChromaDBManager()
    context, sources = manager.search_context_with_filter(
        query=question,
        user_id=user_id,
        user_dept_id=user_model.department_id if user_model.department_id is not None else -1,
        search_scope=normalized_scope,
        session_id=session.id if normalized_scope == "personal" else None,
        extra_doc_ids=attached_doc_ids if attached_doc_ids else None,
    )

    job_service.update_progress(db, job, 60)
    ai = OllamaAI()
    answer = ai.generate_answer(question, context, chat_history)

    job_service.update_progress(db, job, 90)
    ai_message.content = answer
    ai_message.sources = json.dumps(sources, ensure_ascii=False)
    db.commit()
    job_service.mark_success(
        db,
        job,
        {
            "answer": answer,
            "sources": sources,
            "session_id": session.id,
            "message_id": ai_message.id,
            "attached_docs": len(attached_doc_ids),
        },
    )
