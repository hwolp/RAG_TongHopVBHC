import datetime
import os
import shutil
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from config import UPLOAD_DIR_DEPARTMENT, UPLOAD_DIR_PERSONAL, UPLOAD_DIR_SQP
from database import models
from services.access_policy import can_access_document
from services import job_service


def _scope_str(scope_value) -> str:
    return scope_value.value if hasattr(scope_value, "value") else str(scope_value)


def _safe_filename(filename: str) -> str:
    candidate = (filename or "").strip()
    if not candidate:
        raise HTTPException(status_code=400, detail="Ten file khong hop le")

    base_name = os.path.basename(candidate)
    if base_name != candidate or base_name in {".", ".."} or ".." in base_name:
        raise HTTPException(status_code=400, detail="Ten file khong hop le")
    return base_name


def _stored_filename(original_filename: str) -> str:
    stem, extension = os.path.splitext(original_filename)
    return f"{stem}_{uuid4().hex}{extension}"


def _upload_response_with_index_job(
    db: Session,
    doc: models.Document,
    created_by: int | None,
    force_admin_chunking: bool = False,
) -> dict:
    job = job_service.create_index_job(db, doc, created_by, force_admin_chunking)
    if not job:
        return {"status": "success", "doc_id": doc.id, "job_id": None}
    return {"status": "queued", "doc_id": doc.id, "job_id": job.id}


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


def list_personal_documents(db: Session, user_id: int, search: str = ""):
    query = db.query(models.Document).filter(
        models.Document.owner_id == user_id,
        models.Document.scope == models.ScopeEnum.personal,
        models.Document.is_deleted == False,
        models.Document.chat_session_id == None,
    )
    if search:
        query = query.filter(models.Document.filename.contains(search))

    docs = query.order_by(models.Document.uploaded_at.desc()).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "scope": _scope_str(doc.scope),
            "is_indexed": doc.is_indexed,
            "index_status": _index_status(db, doc),
            "uploaded_at": str(doc.uploaded_at),
        }
        for doc in docs
    ]


async def upload_personal_document(db: Session, user_id: int, file: UploadFile):
    safe_filename = _safe_filename(file.filename)
    user_dir = os.path.join(UPLOAD_DIR_PERSONAL, f"user_{user_id}")
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, _stored_filename(safe_filename))

    with open(file_path, "wb+") as handle:
        shutil.copyfileobj(file.file, handle)

    doc = models.Document(
        filename=safe_filename,
        file_path=file_path,
        owner_id=user_id,
        scope=models.ScopeEnum.personal,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return _upload_response_with_index_job(db, doc, user_id)


async def upload_session_personal_document(db: Session, user_id: int, session_id: int, file: UploadFile):
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Phien khong ton tai")

    safe_filename = _safe_filename(file.filename)
    session_dir = os.path.join(UPLOAD_DIR_PERSONAL, f"user_{user_id}", "sessions", f"session_{session_id}")
    os.makedirs(session_dir, exist_ok=True)
    file_path = os.path.join(session_dir, _stored_filename(safe_filename))

    with open(file_path, "wb+") as handle:
        shutil.copyfileobj(file.file, handle)

    doc = models.Document(
        filename=safe_filename,
        file_path=file_path,
        owner_id=user_id,
        scope=models.ScopeEnum.personal,
        chat_session_id=session_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return _upload_response_with_index_job(db, doc, user_id)


def list_department_documents(db: Session, user_id: int, search: str = ""):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    query = db.query(models.Document).filter(models.Document.scope == models.ScopeEnum.department)
    query = query.filter(models.Document.is_deleted == False)
    if user.role == models.RoleEnum.admin:
        pass
    elif user.role == models.RoleEnum.manager:
        query = query.filter(models.Document.department_id == user.department_id)
    else:
        raise HTTPException(status_code=403, detail="Chi manager/admin duoc xem danh sach tai lieu phong ban")

    if search:
        query = query.filter(models.Document.filename.contains(search))

    docs = query.order_by(models.Document.uploaded_at.desc()).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "uploaded_at": str(doc.uploaded_at),
            "owner_id": doc.owner_id,
            "department_id": doc.department_id,
            "is_indexed": doc.is_indexed,
            "index_status": _index_status(db, doc),
        }
        for doc in docs
    ]


async def upload_department_document(db: Session, manager_user_id: int, file: UploadFile):
    manager = db.query(models.User).filter(models.User.id == manager_user_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    os.makedirs(UPLOAD_DIR_DEPARTMENT, exist_ok=True)
    safe_filename = _safe_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR_DEPARTMENT, safe_filename)
    with open(file_path, "wb+") as handle:
        shutil.copyfileobj(file.file, handle)

    doc = models.Document(
        filename=safe_filename,
        file_path=file_path,
        owner_id=manager_user_id,
        department_id=manager.department_id,
        scope=models.ScopeEnum.department,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return _upload_response_with_index_job(db, doc, manager_user_id)


async def upload_department_document_for_admin(db: Session, admin_user_id: int, department_id: int, file: UploadFile):
    admin_user = db.query(models.User).filter(models.User.id == admin_user_id).first()
    if not admin_user or admin_user.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Chi admin duoc thao tac")

    dept = db.query(models.Department).filter(models.Department.id == department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Phong ban khong ton tai")

    os.makedirs(UPLOAD_DIR_DEPARTMENT, exist_ok=True)
    safe_filename = _safe_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR_DEPARTMENT, safe_filename)
    with open(file_path, "wb+") as handle:
        shutil.copyfileobj(file.file, handle)

    doc = models.Document(
        filename=safe_filename,
        file_path=file_path,
        owner_id=admin_user_id,
        department_id=department_id,
        scope=models.ScopeEnum.department,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _upload_response_with_index_job(db, doc, admin_user_id)


def delete_personal_document(db: Session, user_id: int, doc_id: int):
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.owner_id == user_id,
        models.Document.scope == models.ScopeEnum.personal,
        models.Document.is_deleted == False,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Tai lieu khong ton tai")

    doc.is_deleted = True
    doc.deleted_at = datetime.datetime.utcnow()
    db.commit()
    return {"status": "success"}


def delete_department_document(db: Session, manager_user_id: int, doc_id: int):
    manager = db.query(models.User).filter(models.User.id == manager_user_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    doc_query = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.scope == models.ScopeEnum.department,
        models.Document.is_deleted == False,
    )
    if manager.role != models.RoleEnum.admin:
        doc_query = doc_query.filter(models.Document.department_id == manager.department_id)
    doc = doc_query.first()
    if not doc:
        raise HTTPException(status_code=404, detail="Tai lieu khong ton tai trong phong ban")

    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.delete(doc)
    db.commit()
    return {"status": "success"}


def update_department_document_for_admin(
    db: Session,
    admin_user_id: int,
    doc_id: int,
    filename: Optional[str] = None,
    department_id: Optional[int] = None,
):
    admin_user = db.query(models.User).filter(models.User.id == admin_user_id).first()
    if not admin_user or admin_user.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Chi admin duoc thao tac")

    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.scope == models.ScopeEnum.department,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Tai lieu phong ban khong ton tai")

    if filename is not None and filename.strip():
        new_name = _safe_filename(filename)
        current_dir = os.path.dirname(doc.file_path)
        new_path = os.path.join(current_dir, new_name)
        if os.path.exists(doc.file_path) and doc.file_path != new_path:
            os.replace(doc.file_path, new_path)
        doc.filename = new_name
        doc.file_path = new_path

    if department_id is not None:
        dept = db.query(models.Department).filter(models.Department.id == department_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Phong ban khong ton tai")
        doc.department_id = department_id

    db.commit()
    db.refresh(doc)
    return {
        "status": "success",
        "id": doc.id,
        "filename": doc.filename,
        "department_id": doc.department_id,
    }


def download_document(db: Session, user_id: int, doc_id: int):
    user_model = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Tai lieu khong ton tai")

    if not can_access_document(db, user_model, doc):
        raise HTTPException(status_code=403, detail="Khong co quyen tai tai lieu nay")

    return FileResponse(doc.file_path, filename=doc.filename)


def get_document_detail(db: Session, user_id: int, doc_id: int):
    user_model = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Tai lieu khong ton tai")

    if not can_access_document(db, user_model, doc):
        raise HTTPException(status_code=403, detail="Khong co quyen xem tai lieu nay")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_path": doc.file_path,
        "scope": _scope_str(doc.scope),
        "summary": doc.summary,
        "is_indexed": doc.is_indexed,
        "version_number": doc.version_number or 1,
        "uploaded_at": str(doc.uploaded_at),
        "owner_id": doc.owner_id,
        "department_id": doc.department_id,
    }


def list_document_versions(db: Session, user_id: int, doc_id: int):
    get_document_detail(db, user_id, doc_id)
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    versions = db.query(models.DocumentVersion).filter(
        models.DocumentVersion.document_id == doc_id,
    ).order_by(models.DocumentVersion.version_number.asc()).all()

    if not versions:
        return [
            {
                "id": None,
                "document_id": doc.id,
                "filename": doc.filename,
                "file_path": doc.file_path,
                "version_number": doc.version_number or 1,
                "created_at": str(doc.uploaded_at),
            }
        ]

    return [
        {
            "id": version.id,
            "document_id": version.document_id,
            "filename": version.filename,
            "file_path": version.file_path,
            "version_number": version.version_number,
            "created_at": str(version.created_at),
        }
        for version in versions
    ]


async def upload_document_version(db: Session, user_id: int, doc_id: int, file: UploadFile):
    user_model = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Tai lieu khong ton tai")
    if not can_access_document(db, user_model, doc):
        raise HTTPException(status_code=403, detail="Khong co quyen cap nhat tai lieu nay")

    safe_filename = _safe_filename(file.filename)
    base_dir = os.path.dirname(doc.file_path) or UPLOAD_DIR_PERSONAL
    os.makedirs(base_dir, exist_ok=True)

    if not db.query(models.DocumentVersion).filter(models.DocumentVersion.document_id == doc_id).first():
        db.add(models.DocumentVersion(
            document_id=doc.id,
            filename=doc.filename,
            file_path=doc.file_path,
            version_number=doc.version_number or 1,
            uploaded_by=doc.owner_id,
            created_at=doc.uploaded_at,
        ))

    next_version = (doc.version_number or 1) + 1
    stored_name = f"v{next_version}_{int(datetime.datetime.utcnow().timestamp())}_{safe_filename}"
    file_path = os.path.join(base_dir, stored_name)
    with open(file_path, "wb+") as handle:
        shutil.copyfileobj(file.file, handle)

    version = models.DocumentVersion(
        document_id=doc.id,
        filename=safe_filename,
        file_path=file_path,
        version_number=next_version,
        uploaded_by=user_id,
    )
    db.add(version)
    doc.filename = safe_filename
    doc.file_path = file_path
    doc.version_number = next_version
    doc.is_indexed = False
    db.commit()
    db.refresh(version)
    job = job_service.create_index_job(db, doc, user_id)
    return {
        "status": "queued" if job else "success",
        "doc_id": doc.id,
        "version_id": version.id,
        "version_number": version.version_number,
        "job_id": job.id if job else None,
    }


def list_deleted_documents(db: Session, user_id: int):
    user_model = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    query = db.query(models.Document).filter(models.Document.is_deleted == True)
    if user_model.role != models.RoleEnum.admin:
        query = query.filter(models.Document.owner_id == user_id)

    docs = query.order_by(models.Document.deleted_at.desc()).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "scope": _scope_str(doc.scope),
            "deleted_at": str(doc.deleted_at),
            "version_number": doc.version_number or 1,
        }
        for doc in docs
    ]


def restore_document(db: Session, user_id: int, doc_id: int):
    user_model = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc or not doc.is_deleted:
        raise HTTPException(status_code=404, detail="Tai lieu trong thung rac khong ton tai")
    if user_model.role != models.RoleEnum.admin and doc.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Khong co quyen khoi phuc tai lieu nay")

    doc.is_deleted = False
    doc.deleted_at = None
    db.commit()
    return {"status": "success", "doc_id": doc.id}


def list_sqp_documents(db: Session, search: str = ""):
    query = db.query(models.Document).filter(
        models.Document.scope == models.ScopeEnum.sqp,
        models.Document.is_deleted == False,
    )
    if search:
        query = query.filter(models.Document.filename.contains(search))

    docs = query.order_by(models.Document.uploaded_at.desc()).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "uploaded_at": str(doc.uploaded_at),
            "owner_id": doc.owner_id,
            "is_indexed": doc.is_indexed,
            "index_status": _index_status(db, doc),
        }
        for doc in docs
    ]


def list_company_documents(db: Session, search: str = ""):
    return list_sqp_documents(db, search)


async def upload_sqp_document_for_admin(db: Session, admin_user_id: int, file: UploadFile):
    admin_user = db.query(models.User).filter(models.User.id == admin_user_id).first()
    if not admin_user or admin_user.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Chi admin duoc thao tac")

    os.makedirs(UPLOAD_DIR_SQP, exist_ok=True)
    safe_filename = _safe_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR_SQP, safe_filename)
    with open(file_path, "wb+") as handle:
        shutil.copyfileobj(file.file, handle)

    doc = models.Document(
        filename=safe_filename,
        file_path=file_path,
        owner_id=admin_user_id,
        scope=models.ScopeEnum.sqp,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return _upload_response_with_index_job(db, doc, admin_user_id, force_admin_chunking=True)


def update_sqp_document_for_admin(
    db: Session,
    admin_user_id: int,
    doc_id: int,
    filename: Optional[str] = None,
):
    admin_user = db.query(models.User).filter(models.User.id == admin_user_id).first()
    if not admin_user or admin_user.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Chi admin duoc thao tac")

    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.scope == models.ScopeEnum.sqp,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Tai lieu SQP khong ton tai")

    if filename is not None and filename.strip():
        new_name = _safe_filename(filename)
        new_path = os.path.join(os.path.dirname(doc.file_path), new_name)
        if os.path.exists(doc.file_path) and doc.file_path != new_path:
            os.replace(doc.file_path, new_path)
        doc.filename = new_name
        doc.file_path = new_path

    db.commit()
    db.refresh(doc)
    return {"status": "success", "id": doc.id, "filename": doc.filename}


def delete_sqp_document_for_admin(db: Session, admin_user_id: int, doc_id: int):
    admin_user = db.query(models.User).filter(models.User.id == admin_user_id).first()
    if not admin_user or admin_user.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Chi admin duoc thao tac")

    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.scope == models.ScopeEnum.sqp,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Tai lieu SQP khong ton tai")

    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.delete(doc)
    db.commit()
    return {"status": "success"}


def get_sqp_document_detail(db: Session, doc_id: int):
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.scope == models.ScopeEnum.sqp,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Quy dinh khong ton tai")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_path": doc.file_path,
        "summary": doc.summary,
        "uploaded_at": str(doc.uploaded_at),
    }


def list_shared_documents(db: Session, user_id: int, search: str = ""):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    shared_doc_ids_query = db.query(models.SharedDocument.document_id).filter(
        (models.SharedDocument.shared_with_user_id == user_id)
        | (models.SharedDocument.shared_with_dept_id == user.department_id)
    )

    query = db.query(models.Document).filter(
        models.Document.id.in_(shared_doc_ids_query),
        models.Document.scope == models.ScopeEnum.department,
        models.Document.is_deleted == False,
    )
    if search:
        query = query.filter(models.Document.filename.contains(search))

    docs = query.order_by(models.Document.uploaded_at.desc()).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "uploaded_at": str(doc.uploaded_at),
            "owner_id": doc.owner_id,
            "department_id": doc.department_id,
        }
        for doc in docs
    ]


def list_session_documents(db: Session, user_id: int, session_id: int) -> list[dict]:
    """Liệt kê các tài liệu được upload trực tiếp vào session chat."""
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session không tồn tại")

    docs = db.query(models.Document).filter(
        models.Document.chat_session_id == session_id,
        models.Document.owner_id == user_id,
    ).order_by(models.Document.uploaded_at.desc()).all()

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "is_indexed": doc.is_indexed,
            "index_status": _index_status(db, doc),
            "uploaded_at": str(doc.uploaded_at),
        }
        for doc in docs
    ]


def delete_session_document(db: Session, user_id: int, session_id: int, doc_id: int) -> dict:
    """Xóa một tài liệu được upload vào session (chỉ chủ sở hữu)."""
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session không tồn tại")

    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.chat_session_id == session_id,
        models.Document.owner_id == user_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại trong session")

    # Xóa file thật
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # Xóa record từ DB
    db.delete(doc)
    db.commit()

    return {"status": "success", "message": "Đã xóa tài liệu khỏi session"}
