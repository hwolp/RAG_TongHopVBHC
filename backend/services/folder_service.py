"""
folder_service.py — Cung cấp cấu trúc cây thư mục tài liệu theo scope và quyền.
"""
from sqlalchemy.orm import Session
from database import models


def _doc_to_dict(doc: models.Document) -> dict:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "scope": doc.scope.value if hasattr(doc.scope, "value") else str(doc.scope),
        "is_indexed": doc.is_indexed,
        "uploaded_at": str(doc.uploaded_at),
        "owner_id": doc.owner_id,
        "department_id": doc.department_id,
    }


def get_folder_tree(db: Session, user_id: int) -> dict:
    """
    Trả về cấu trúc cây thư mục tài liệu của user.

    Cấu trúc trả về:
    {
        "personal": [ {doc}, ... ],
        "department": {
            "dept_name": [ {doc}, ... ]
        },
        "company": [ {doc}, ... ]
    }
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    dept_id = user.department_id if user else None

    # ── 1. Tài liệu cá nhân ──
    personal_docs = db.query(models.Document).filter(
        models.Document.owner_id == user_id,
        models.Document.scope == models.ScopeEnum.personal,
        models.Document.chat_session_id == None,  # Chỉ file thư viện, bỏ session temp
    ).order_by(models.Document.uploaded_at.desc()).all()

    # ── 2. Tài liệu phòng ban ──
    dept_tree: dict[str, list] = {}
    if dept_id:
        dept_docs = db.query(models.Document).filter(
            models.Document.department_id == dept_id,
            models.Document.scope == models.ScopeEnum.department,
        ).order_by(models.Document.uploaded_at.desc()).all()

        dept_obj = db.query(models.Department).filter(models.Department.id == dept_id).first()
        dept_name = dept_obj.name if dept_obj else f"Phòng ban #{dept_id}"
        dept_tree[dept_name] = [_doc_to_dict(d) for d in dept_docs]
    else:
        dept_tree = {}

    # ── 3. Tài liệu công ty (SQP) ──
    company_docs = db.query(models.Document).filter(
        models.Document.scope == models.ScopeEnum.sqp,
    ).order_by(models.Document.uploaded_at.desc()).all()

    return {
        "personal": [_doc_to_dict(d) for d in personal_docs],
        "department": dept_tree,
        "company": [_doc_to_dict(d) for d in company_docs],
    }


def get_session_attached_doc_ids(db: Session, session_id: int) -> list[int]:
    """Trả về danh sách doc_id được đính kèm thủ công vào session."""
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        return []

    # Lấy doc_ids từ SessionAttachment (nếu có bảng riêng)
    # Hiện tại dùng model SessionDocAttachment
    attachments = db.query(models.SessionDocAttachment).filter(
        models.SessionDocAttachment.session_id == session_id
    ).all()
    return [a.doc_id for a in attachments]


def attach_doc_to_session(db: Session, user_id: int, session_id: int, doc_id: int) -> dict:
    """Đính kèm một tài liệu có sẵn vào session chat."""
    # Verify session ownership
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == user_id,
    ).first()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session không tồn tại")

    # Verify doc access
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại")

    # Kiểm tra đã attach chưa
    existing = db.query(models.SessionDocAttachment).filter(
        models.SessionDocAttachment.session_id == session_id,
        models.SessionDocAttachment.doc_id == doc_id,
    ).first()
    if existing:
        return {"status": "already_attached", "doc_id": doc_id}

    attachment = models.SessionDocAttachment(session_id=session_id, doc_id=doc_id)
    db.add(attachment)
    db.commit()

    return {
        "status": "attached",
        "doc_id": doc_id,
        "filename": doc.filename,
        "session_id": session_id,
    }


def detach_doc_from_session(db: Session, user_id: int, session_id: int, doc_id: int) -> dict:
    """Gỡ đính kèm tài liệu khỏi session chat."""
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == user_id,
    ).first()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session không tồn tại")

    attachment = db.query(models.SessionDocAttachment).filter(
        models.SessionDocAttachment.session_id == session_id,
        models.SessionDocAttachment.doc_id == doc_id,
    ).first()
    if attachment:
        db.delete(attachment)
        db.commit()

    return {"status": "detached", "doc_id": doc_id}


def list_session_attachments(db: Session, user_id: int, session_id: int) -> list[dict]:
    """Liệt kê tài liệu đã đính kèm vào session."""
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == user_id,
    ).first()
    if not session:
        return []

    attachments = db.query(models.SessionDocAttachment).filter(
        models.SessionDocAttachment.session_id == session_id
    ).all()

    result = []
    for att in attachments:
        doc = db.query(models.Document).filter(models.Document.id == att.doc_id).first()
        if doc:
            result.append({
                "doc_id": att.doc_id,
                "filename": doc.filename,
                "scope": doc.scope.value if hasattr(doc.scope, "value") else str(doc.scope),
                "is_indexed": doc.is_indexed,
            })
    return result
