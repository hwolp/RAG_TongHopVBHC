"""
folder_service.py — Cung cấp cấu trúc cây thư mục tài liệu theo scope và quyền.
"""
from sqlalchemy.orm import Session
from database import models
from repositories.chat_repository import ChatRepository
from repositories.department_repository import DepartmentRepository
from repositories.document_repository import DocumentRepository
from repositories.job_repository import BackgroundJobRepository
from repositories.user_repository import UserRepository
from services.documents.document_service import DocumentIndexCoordinator
from services.jobs import job_service
from services.policies.access_policy import can_access_document
from utils.enum_utils import enum_value


def _index_status(db: Session, doc: models.Document) -> str:
    return DocumentIndexCoordinator(db).index_status(doc)


def _doc_to_dict(db: Session, doc: models.Document) -> dict:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "scope": enum_value(doc.scope),
        "is_indexed": doc.is_indexed,
        "index_status": _index_status(db, doc),
        "uploaded_at": str(doc.uploaded_at),
        "owner_id": doc.owner_id,
        "department_id": doc.department_id,
    }


def _ensure_index_job(db: Session, doc: models.Document, created_by: int | None) -> models.BackgroundJob | None:
    if doc.is_indexed:
        return None
    current_job = BackgroundJobRepository(db).latest_active_for_document(
        doc.id,
        job_service.JOB_TYPE_INDEX_DOCUMENT,
        [job_service.STATUS_QUEUED, job_service.STATUS_RUNNING],
    )
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
    users = UserRepository(db)
    documents = DocumentRepository(db)
    departments = DepartmentRepository(db)
    user = users.get(user_id)
    if not user:
        return {"personal": [], "department": {}, "company": []}
    dept_id = user.department_id if user else None

    # ── 1. Tài liệu cá nhân ──
    personal_docs = documents.list_personal_library(user_id)

    # ── 2. Tài liệu phòng ban ──
    dept_tree: dict[str, list] = {}
    if user.role == models.RoleEnum.admin:
        dept_docs = documents.list_department()

        all_departments = departments.list_business_departments()
        for department in all_departments:
            department_docs = [doc for doc in dept_docs if doc.department_id == department.id]
            dept_tree[department.name] = [_doc_to_dict(db, doc) for doc in department_docs]
    elif user.role == models.RoleEnum.manager and dept_id:
        dept_docs = documents.list_department(dept_id)

        dept_obj = departments.get(dept_id)
        dept_name = dept_obj.name if dept_obj else f"Phòng ban #{dept_id}"
        dept_tree[dept_name] = [_doc_to_dict(db, d) for d in dept_docs]
    elif user.role == models.RoleEnum.employee:
        if dept_id:
            dept_docs = documents.list_department(dept_id)
            dept_obj = departments.get(dept_id)
            dept_name = dept_obj.name if dept_obj else f"Phòng ban #{dept_id}"
            dept_tree[dept_name] = [_doc_to_dict(db, d) for d in dept_docs]

        shared_docs = documents.list_shared_with_user(user)
        dept_tree["Được chia sẻ liên phòng"] = [_doc_to_dict(db, d) for d in shared_docs]
    else:
        dept_tree = {}

    # ── 3. Tài liệu công ty (SQP) ──
    company_docs = documents.list_sqp()

    return {
        "personal": [_doc_to_dict(db, d) for d in personal_docs],
        "department": dept_tree,
        "company": [_doc_to_dict(db, d) for d in company_docs],
    }


def get_session_attached_doc_ids(db: Session, session_id: int) -> list[int]:
    """Trả về danh sách doc_id được đính kèm thủ công vào session."""
    chat = ChatRepository(db)
    session = chat.get_session(session_id)
    if not session:
        return []

    attachments = chat.list_attachments(session_id)
    return [a.doc_id for a in attachments]


def attach_doc_to_session(db: Session, user_id: int, session_id: int, doc_id: int) -> dict:
    """Đính kèm một tài liệu có sẵn vào session chat."""
    # Verify session ownership
    chat = ChatRepository(db)
    documents = DocumentRepository(db)
    users = UserRepository(db)
    session = chat.get_session(session_id, user_id)
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session không tồn tại")

    # Verify doc access
    doc = documents.get_active(doc_id)
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại")

    user = users.get(user_id)
    if not can_access_document(db, user, doc):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Khong co quyen dinh kem tai lieu nay")

    # Kiểm tra đã attach chưa
    existing = chat.get_attachment(session_id, doc_id)
    if existing:
        index_job = _ensure_index_job(db, doc, user_id)
        return {
            "status": "already_attached",
            "doc_id": doc_id,
            "index_status": _index_status(db, doc),
            "index_job_id": index_job.id if index_job else None,
        }

    attachment = models.SessionDocAttachment(session_id=session_id, doc_id=doc_id)
    chat.add(attachment)
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
    chat = ChatRepository(db)
    session = chat.get_session(session_id, user_id)
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session không tồn tại")

    attachment = chat.get_attachment(session_id, doc_id)
    if attachment:
        chat.delete(attachment)

    return {"status": "detached", "doc_id": doc_id}


def list_session_attachments(db: Session, user_id: int, session_id: int) -> list[dict]:
    """Liệt kê tài liệu đã đính kèm vào session."""
    chat = ChatRepository(db)
    documents = DocumentRepository(db)
    users = UserRepository(db)
    session = chat.get_session(session_id, user_id)
    if not session:
        return []

    user = users.get(user_id)
    attachments = chat.list_attachments(session_id)

    result = []
    for att in attachments:
        doc = documents.get_active(att.doc_id)
        if doc and can_access_document(db, user, doc):
            result.append({
                "doc_id": att.doc_id,
                "filename": doc.filename,
                "scope": enum_value(doc.scope),
                "is_indexed": doc.is_indexed,
                "index_status": _index_status(db, doc),
            })
    return result
