import datetime
import os
import shutil
from typing import Optional

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from config import UPLOAD_DIR_DEPARTMENT, UPLOAD_DIR_PERSONAL, UPLOAD_DIR_SQP
from database import models
from services.access_policy import can_access_document


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


def list_personal_documents(db: Session, user_id: int, search: str = ""):
    query = db.query(models.Document).filter(
        models.Document.owner_id == user_id,
        models.Document.scope == models.ScopeEnum.personal,
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
            "uploaded_at": str(doc.uploaded_at),
        }
        for doc in docs
    ]


async def upload_personal_document(db: Session, user_id: int, file: UploadFile):
    os.makedirs(UPLOAD_DIR_PERSONAL, exist_ok=True)
    safe_filename = _safe_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR_PERSONAL, safe_filename)

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

    if safe_filename.lower().endswith(".pdf"):
        try:
            from rag_engine.chroma_manager import ChromaDBManager

            manager = ChromaDBManager()
            chunks = manager.process_and_store_pdf(file_path, doc.id, user_id, -1, "personal", "", None)
            doc.is_indexed = True
            db.commit()
            return {"status": "success", "doc_id": doc.id, "chunks": chunks}
        except Exception as exc:
            return {
                "status": "success",
                "doc_id": doc.id,
                "warning": f"Luu file OK nhung index loi: {str(exc)}",
            }

    return {"status": "success", "doc_id": doc.id}


async def upload_session_personal_document(db: Session, user_id: int, session_id: int, file: UploadFile):
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Phien khong ton tai")

    session_dir = os.path.join(UPLOAD_DIR_PERSONAL, f"session_{session_id}")
    os.makedirs(session_dir, exist_ok=True)
    safe_filename = _safe_filename(file.filename)
    safe_name = f"{int(datetime.datetime.utcnow().timestamp())}_{safe_filename}"
    file_path = os.path.join(session_dir, safe_name)

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

    if safe_filename.lower().endswith(".pdf"):
        try:
            from rag_engine.chroma_manager import ChromaDBManager

            manager = ChromaDBManager()
            chunks = manager.process_and_store_pdf(
                file_path,
                doc.id,
                user_id,
                -1,
                "personal",
                "",
                session_id,
            )
            doc.is_indexed = True
            db.commit()
            return {"status": "success", "doc_id": doc.id, "chunks": chunks}
        except Exception as exc:
            return {
                "status": "success",
                "doc_id": doc.id,
                "warning": f"Luu file OK nhung index loi: {str(exc)}",
            }

    return {"status": "success", "doc_id": doc.id}


def list_department_documents(db: Session, user_id: int, search: str = ""):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    query = db.query(models.Document).filter(models.Document.scope == models.ScopeEnum.department)
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

    return {"status": "success", "doc_id": doc.id}


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
    return {"status": "success", "doc_id": doc.id}


def delete_personal_document(db: Session, user_id: int, doc_id: int):
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.owner_id == user_id,
        models.Document.scope == models.ScopeEnum.personal,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Tai lieu khong ton tai")

    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.delete(doc)
    db.commit()
    return {"status": "success"}


def delete_department_document(db: Session, manager_user_id: int, doc_id: int):
    manager = db.query(models.User).filter(models.User.id == manager_user_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    doc_query = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.scope == models.ScopeEnum.department,
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
    if not doc:
        raise HTTPException(status_code=404, detail="Tai lieu khong ton tai")

    if not can_access_document(db, user_model, doc):
        raise HTTPException(status_code=403, detail="Khong co quyen tai tai lieu nay")

    return FileResponse(doc.file_path, filename=doc.filename)


def list_sqp_documents(db: Session, search: str = ""):
    query = db.query(models.Document).filter(models.Document.scope == models.ScopeEnum.sqp)
    if search:
        query = query.filter(models.Document.filename.contains(search))

    docs = query.order_by(models.Document.uploaded_at.desc()).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "uploaded_at": str(doc.uploaded_at),
            "owner_id": doc.owner_id,
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
    return {"status": "success", "doc_id": doc.id}


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
