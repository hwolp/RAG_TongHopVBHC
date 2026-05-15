import json
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import models
from services.access_policy import can_access_document
from services import job_service


def ask_ai(db: Session, user_id: int, question: str, scope: str = "personal", session_id: Optional[int] = None):
    from rag_engine.chroma_manager import ChromaDBManager
    from rag_engine.ollama_ai import OllamaAI

    session = None
    if session_id:
        session = db.query(models.ChatSession).filter(
            models.ChatSession.id == session_id,
            models.ChatSession.user_id == user_id,
        ).first()

    if not session:
        session = models.ChatSession(user_id=user_id, title=question[:50])
        db.add(session)
        db.commit()
        db.refresh(session)

    recent_messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.session_id == session.id
    ).order_by(models.ChatMessage.created_at.desc()).limit(10).all()
    recent_messages.reverse()

    chat_history = ""
    for message in recent_messages:
        role = "Nguoi dung" if message.sender == "user" else "AI"
        chat_history += f"{role}: {message.content}\n"

    manager = ChromaDBManager()
    user_model = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")
    dept_id = user_model.department_id if user_model else -1
    normalized_scope = "sqp" if scope == "company" else scope
    if normalized_scope == "department" and user_model.role == models.RoleEnum.employee:
        raise HTTPException(status_code=403, detail="Nhan vien chi duoc chat tren tai lieu ca nhan va tai lieu cong ty")

    # Lấy doc_ids đính kèm thủ công vào session (từ Folder Tree picker)
    attached_doc_ids = []
    for attachment in db.query(models.SessionDocAttachment).filter(
        models.SessionDocAttachment.session_id == session.id
    ).all():
        doc = db.query(models.Document).filter(models.Document.id == attachment.doc_id).first()
        if can_access_document(db, user_model, doc):
            attached_doc_ids.append(attachment.doc_id)

    context, sources = manager.search_context_with_filter(
        query=question,
        user_id=user_id,
        user_dept_id=dept_id,
        search_scope=normalized_scope,
        session_id=session.id if normalized_scope == "personal" else None,
        extra_doc_ids=attached_doc_ids if attached_doc_ids else None,
    )

    ai = OllamaAI()
    answer = ai.generate_answer(question, context, chat_history)

    user_message = models.ChatMessage(session_id=session.id, sender="user", content=question)
    ai_message = models.ChatMessage(
        session_id=session.id,
        sender="ai",
        content=answer,
        sources=json.dumps(sources, ensure_ascii=False),
    )
    db.add_all([user_message, ai_message])
    db.commit()

    return {
        "answer": answer,
        "sources": sources,
        "session_id": session.id,
        "session_title": session.title,
        "attached_docs": len(attached_doc_ids),
    }


def queue_ai_answer(db: Session, user_id: int, question: str, scope: str = "personal", session_id: Optional[int] = None):
    user_model = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    normalized_scope = "sqp" if scope == "company" else scope
    if normalized_scope == "department" and user_model.role == models.RoleEnum.employee:
        raise HTTPException(status_code=403, detail="Nhan vien chi duoc chat tren tai lieu ca nhan va tai lieu cong ty")

    session = None
    if session_id:
        session = db.query(models.ChatSession).filter(
            models.ChatSession.id == session_id,
            models.ChatSession.user_id == user_id,
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Phien khong ton tai")

    if not session:
        session = models.ChatSession(user_id=user_id, title=question[:50] or "Phiên hội thoại mới")
        db.add(session)
        db.commit()
        db.refresh(session)

    user_message = models.ChatMessage(session_id=session.id, sender="user", content=question)
    ai_message = models.ChatMessage(
        session_id=session.id,
        sender="ai",
        content="Đang xử lý câu trả lời...",
        sources="[]",
    )
    db.add_all([user_message, ai_message])
    db.commit()
    db.refresh(user_message)
    db.refresh(ai_message)

    job = job_service.create_job(
        db=db,
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


def create_session(db: Session, user_id: int, title: str | None = None):
    """Tạo phiên hội thoại mới với tên mặc định."""
    if not title or not title.strip():
        count = db.query(models.ChatSession).filter(
            models.ChatSession.user_id == user_id
        ).count()
        title = f"Phiên mới {count + 1}"

    session = models.ChatSession(user_id=user_id, title=title.strip())
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "title": session.title, "created_at": str(session.created_at)}


def list_sessions(db: Session, user_id: int):
    sessions = db.query(models.ChatSession).filter(
        models.ChatSession.user_id == user_id
    ).order_by(models.ChatSession.created_at.desc()).all()
    return [{"id": s.id, "title": s.title, "created_at": str(s.created_at)} for s in sessions]


def get_session_messages(db: Session, user_id: int, session_id: int):
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Phien khong ton tai")

    return [
        {
            "id": m.id,
            "sender": m.sender,
            "content": m.content,
            "sources": m.sources,
            "created_at": str(m.created_at),
        }
        for m in session.messages
    ]


def get_session_messages_paginated(
    db: Session,
    user_id: int,
    session_id: int,
    limit: int = 5,
    before_id: Optional[int] = None,
):
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Phien khong ton tai")

    safe_limit = max(1, min(limit, 50))
    query = db.query(models.ChatMessage).filter(models.ChatMessage.session_id == session_id)
    if before_id is not None:
        query = query.filter(models.ChatMessage.id < before_id)

    rows = query.order_by(models.ChatMessage.id.desc()).limit(safe_limit + 1).all()
    has_more = len(rows) > safe_limit
    selected = rows[:safe_limit]
    selected.reverse()
    selected_ids = [m.id for m in selected]
    active_jobs_by_message = {}
    if selected_ids:
        active_jobs = db.query(models.BackgroundJob).filter(
            models.BackgroundJob.message_id.in_(selected_ids),
            models.BackgroundJob.type == job_service.JOB_TYPE_CHAT_ANSWER,
            models.BackgroundJob.status.in_([
                job_service.STATUS_QUEUED,
                job_service.STATUS_RUNNING,
            ]),
        ).order_by(models.BackgroundJob.created_at.desc()).all()
        for job in active_jobs:
            active_jobs_by_message.setdefault(job.message_id, job)

    items = []
    for m in selected:
        item = {
            "id": m.id,
            "sender": m.sender,
            "content": m.content,
            "sources": m.sources,
            "created_at": str(m.created_at),
        }
        job = active_jobs_by_message.get(m.id)
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
    return {
        "items": items,
        "has_more": has_more,
        "next_before_id": next_before_id,
    }


def rename_session(db: Session, user_id: int, session_id: int, title: str):
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Phien khong ton tai")

    session.title = title
    db.commit()
    return {"status": "success"}


def delete_session(db: Session, user_id: int, session_id: int):
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Phien khong ton tai")

    db.delete(session)
    db.commit()
    return {"status": "success"}


def list_saved_prompts(db: Session, user_id: int):
    prompts = db.query(models.SavedPrompt).filter(models.SavedPrompt.user_id == user_id).all()
    return [{"id": p.id, "content": p.content, "created_at": str(p.created_at)} for p in prompts]


def create_saved_prompt(db: Session, user_id: int, content: str):
    prompt = models.SavedPrompt(user_id=user_id, content=content)
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return {"status": "success", "id": prompt.id}


def delete_saved_prompt(db: Session, user_id: int, prompt_id: int):
    prompt = db.query(models.SavedPrompt).filter(
        models.SavedPrompt.id == prompt_id,
        models.SavedPrompt.user_id == user_id,
    ).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    db.delete(prompt)
    db.commit()
    return {"status": "success"}


def get_message_citations(db: Session, user_id: int, message_id: int):
    message = db.query(models.ChatMessage).join(models.ChatSession).filter(
        models.ChatMessage.id == message_id,
        models.ChatSession.user_id == user_id,
    ).first()
    if not message:
        raise HTTPException(status_code=404, detail="Tin nhan khong ton tai")

    try:
        sources = json.loads(message.sources or "[]")
    except json.JSONDecodeError:
        sources = []

    return {
        "message_id": message.id,
        "sources": [str(source) for source in sources],
    }


def execute_saved_prompt(
    db: Session,
    user_id: int,
    prompt_id: int,
    scope: str = "personal",
    session_id: Optional[int] = None,
):
    prompt = db.query(models.SavedPrompt).filter(
        models.SavedPrompt.id == prompt_id,
        models.SavedPrompt.user_id == user_id,
    ).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    return queue_ai_answer(
        db=db,
        user_id=user_id,
        question=prompt.content,
        scope=scope,
        session_id=session_id,
    )
