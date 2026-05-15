"""
folder_service.py — Cung cấp cấu trúc cây thư mục tài liệu theo scope và quyền.
"""
from sqlalchemy.orm import Session
from database import models
from services.access_policy import can_access_document
from services import job_service


def _index_status(db: Session, doc: models.Document) -> str:
    if doc.is_indexed:
        return "indexed"
    job = db.query(models.BackgroundJob).filter(
        models.BackgroundJob.document_id == doc.id,
        models.BackgroundJob.type == job_service.JOB_TYPE_INDEX_DOCUMENT,
    ).order_by(models.BackgroundJob.created_at.desc()).first()
    if job and job.status in {"queued", "running", "failed"}:
        return job.status
    return "not_indexed"


def _doc_to_dict(db: Session, doc: models.Document) -> dict:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "scope": doc.scope.value if hasattr(doc.scope, "value") else str(doc.scope),
        "is_indexed": doc.is_indexed,
        "index_status": _index_status(db, doc),
        "uploaded_at": str(doc.uploaded_at),
        "owner_id": doc.owner_id,
        "department_id": doc.department_id,
    }


def _ensure_index_job(db: Session, doc: models.Document, created_by: int | None) -> models.BackgroundJob | None:
    if doc.is_indexed:
        return None
    current_job = db.query(models.BackgroundJob).filter(
        models.BackgroundJob.document_id == doc.id,
        models.BackgroundJob.type == job_service.JOB_TYPE_INDEX_DOCUMENT,
        models.BackgroundJob.status.in_([
            job_service.STATUS_QUEUED,
            job_service.STATUS_RUNNING,
        ]),
    ).order_by(models.BackgroundJob.created_at.desc()).first()
    if current_job:
        return current_job
    return job_service.create_index_job(db, doc, created_by)


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
    if not user:
        return {"personal": [], "department": {}, "company": []}
    dept_id = user.department_id if user else None

    # ── 1. Tài liệu cá nhân ──
    personal_docs = db.query(models.Document).filter(
        models.Document.owner_id == user_id,
        models.Document.scope == models.ScopeEnum.personal,
        models.Document.is_deleted == False,
        models.Document.chat_session_id == None,  # Chỉ file thư viện, bỏ session temp
    ).order_by(models.Document.uploaded_at.desc()).all()

    # ── 2. Tài liệu phòng ban ──
    dept_tree: dict[str, list] = {}
    if user.role == models.RoleEnum.admin:
        dept_docs = db.query(models.Document).filter(
            models.Document.scope == models.ScopeEnum.department,
            models.Document.is_deleted == False,
        ).order_by(models.Document.uploaded_at.desc()).all()

        all_departments = db.query(models.Department).filter(models.Department.id != 0).order_by(models.Department.name.asc()).all()
        for department in all_departments:
            department_docs = [doc for doc in dept_docs if doc.department_id == department.id]
            dept_tree[department.name] = [_doc_to_dict(db, doc) for doc in department_docs]
    elif user.role == models.RoleEnum.manager and dept_id:
        dept_docs = db.query(models.Document).filter(
            models.Document.department_id == dept_id,
            models.Document.scope == models.ScopeEnum.department,
            models.Document.is_deleted == False,
        ).order_by(models.Document.uploaded_at.desc()).all()

        dept_obj = db.query(models.Department).filter(models.Department.id == dept_id).first()
        dept_name = dept_obj.name if dept_obj else f"Phòng ban #{dept_id}"
        dept_tree[dept_name] = [_doc_to_dict(db, d) for d in dept_docs]
    elif user.role == models.RoleEnum.employee:
        shared_doc_ids_query = db.query(models.SharedDocument.document_id).filter(
            (models.SharedDocument.shared_with_user_id == user.id)
            | (models.SharedDocument.shared_with_dept_id == user.department_id)
        )
        shared_docs = db.query(models.Document).filter(
            models.Document.id.in_(shared_doc_ids_query),
            models.Document.scope == models.ScopeEnum.department,
            models.Document.is_deleted == False,
        ).order_by(models.Document.uploaded_at.desc()).all()
        dept_tree["Duoc chia se lien phong"] = [_doc_to_dict(db, d) for d in shared_docs]
    else:
        dept_tree = {}

    # ── 3. Tài liệu công ty (SQP) ──
    company_docs = db.query(models.Document).filter(
        models.Document.scope == models.ScopeEnum.sqp,
        models.Document.is_deleted == False,
    ).order_by(models.Document.uploaded_at.desc()).all()

    return {
        "personal": [_doc_to_dict(db, d) for d in personal_docs],
        "department": dept_tree,
        "company": [_doc_to_dict(db, d) for d in company_docs],
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

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not can_access_document(db, user, doc):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Khong co quyen dinh kem tai lieu nay")

    # Kiểm tra đã attach chưa
    existing = db.query(models.SessionDocAttachment).filter(
        models.SessionDocAttachment.session_id == session_id,
        models.SessionDocAttachment.doc_id == doc_id,
    ).first()
    if existing:
        index_job = _ensure_index_job(db, doc, user_id)
        return {
            "status": "already_attached",
            "doc_id": doc_id,
            "index_status": _index_status(db, doc),
            "index_job_id": index_job.id if index_job else None,
        }

    attachment = models.SessionDocAttachment(session_id=session_id, doc_id=doc_id)
    db.add(attachment)
    db.commit()
    index_job = _ensure_index_job(db, doc, user_id)

    return {
        "status": "attached",
        "doc_id": doc_id,
        "filename": doc.filename,
        "session_id": session_id,
        "index_status": _index_status(db, doc),
        "index_job_id": index_job.id if index_job else None,
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

    user = db.query(models.User).filter(models.User.id == user_id).first()
    attachments = db.query(models.SessionDocAttachment).filter(
        models.SessionDocAttachment.session_id == session_id
    ).all()

    result = []
    for att in attachments:
        doc = db.query(models.Document).filter(models.Document.id == att.doc_id).first()
        if doc and can_access_document(db, user, doc):
            result.append({
                "doc_id": att.doc_id,
                "filename": doc.filename,
                "scope": doc.scope.value if hasattr(doc.scope, "value") else str(doc.scope),
                "is_indexed": doc.is_indexed,
                "index_status": _index_status(db, doc),
            })
    return result
