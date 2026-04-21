import json
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import models


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
    dept_id = user_model.department_id if user_model else -1
    normalized_scope = "sqp" if scope == "company" else scope

    # Lấy doc_ids đính kèm thủ công vào session (từ Folder Tree picker)
    attached_doc_ids = [
        a.doc_id for a in db.query(models.SessionDocAttachment).filter(
            models.SessionDocAttachment.session_id == session.id
        ).all()
    ]

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

    items = [
        {
            "id": m.id,
            "sender": m.sender,
            "content": m.content,
            "sources": m.sources,
            "created_at": str(m.created_at),
        }
        for m in selected
    ]

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
