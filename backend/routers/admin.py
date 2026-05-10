from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import models
from database.db_config import get_db
from middleware.auth_middleware import require_admin
from services import document_service, share_service, sqp_service

router = APIRouter(prefix="/admin", tags=["Quản trị hệ thống"])


class UpdateDepartmentDocumentRequest(BaseModel):
    filename: str | None = None
    department_id: int | None = None


class ShareByUsernameRequest(BaseModel):
    username: str


@router.get("/departments")
def list_departments(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    departments = db.query(models.Department).all()
    return [{"id": department.id, "name": department.name} for department in departments]


@router.get("/sqp/documents")
def list_sqp_documents(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return document_service.list_sqp_documents(db)


@router.get("/sqp/proposals")
def list_proposals(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return sqp_service.list_all_proposals(db)


@router.post("/sqp/approve/{proposal_id}")
def approve_proposal(proposal_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return sqp_service.approve_proposal(db, proposal_id)


@router.post("/sqp/reject/{proposal_id}")
def reject_proposal(proposal_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return sqp_service.reject_proposal(db, proposal_id)


@router.get("/documents/department")
def list_all_department_documents(
    search: str = "",
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    return document_service.list_department_documents(db, admin_user["id"], search)


@router.post("/documents/department/upload")
async def upload_department_document(
    department_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    return await document_service.upload_department_document_for_admin(db, admin_user["id"], department_id, file)


@router.put("/documents/department/{doc_id}")
def update_department_document(
    doc_id: int,
    payload: UpdateDepartmentDocumentRequest,
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    return document_service.update_department_document_for_admin(
        db=db,
        admin_user_id=admin_user["id"],
        doc_id=doc_id,
        filename=payload.filename,
        department_id=payload.department_id,
    )


@router.delete("/documents/department/{doc_id}")
def delete_department_document(
    doc_id: int,
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    return document_service.delete_department_document(db, admin_user["id"], doc_id)


@router.get("/shares")
def list_all_shares(
    search: str = "",
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    return share_service.list_all_shares(db, search)


@router.post("/documents/{doc_id}/share/department/{dept_id}")
def share_document_to_department(
    doc_id: int,
    dept_id: int,
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    return share_service.share_document_to_department_as_admin(db, admin_user["id"], doc_id, dept_id)


@router.post("/documents/{doc_id}/share/user")
def share_document_to_user(
    doc_id: int,
    payload: ShareByUsernameRequest,
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    return share_service.share_document_to_user_as_admin(db, admin_user["id"], doc_id, payload.username)


@router.delete("/shares/{share_id}")
def revoke_share(
    share_id: int,
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    return share_service.revoke_share_as_admin(db, admin_user["id"], share_id)


@router.get("/vector/status")
def vector_status(_: dict = Depends(require_admin)):
    from rag_engine.chroma_manager import ChromaDBManager

    manager = ChromaDBManager()
    total = manager.vectordb._collection.count()
    return {"total_vectors": total, "persist_dir": manager.persist_directory}


@router.post("/vector/reindex")
def reindex_vector(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    from rag_engine.chroma_manager import ChromaDBManager

    manager = ChromaDBManager()
    manager.admin_clear_db()

    docs = db.query(models.Document).filter(models.Document.is_indexed == False).all()
    total_chunks = 0
    for doc in docs:
        if not doc.file_path.lower().endswith(".pdf"):
            continue

        chunks = manager.process_and_store_pdf(
            doc.file_path,
            doc.id,
            doc.owner_id or 0,
            doc.department_id or -1,
            doc.scope.value if hasattr(doc.scope, "value") else doc.scope,
            "",
        )
        doc.is_indexed = True
        total_chunks += chunks

    db.commit()
    return {"status": "success", "reindexed_docs": len(docs), "total_chunks": total_chunks}


@router.post("/vector/clear")
def clear_vector(_: dict = Depends(require_admin)):
    from rag_engine.chroma_manager import ChromaDBManager

    manager = ChromaDBManager()
    manager.admin_clear_db()
    return {"status": "success", "message": "Da xoa toan bo Vector DB"}
