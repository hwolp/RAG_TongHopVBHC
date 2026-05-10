from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.db_config import get_db
from database import models
from middleware.auth_middleware import require_manager, require_manager_only
from services import share_service, sqp_service

router = APIRouter(prefix="/manager", tags=["Trưởng phòng"])


@router.get("/sqp/proposals")
def list_my_proposals(db: Session = Depends(get_db), user: dict = Depends(require_manager)):
    return sqp_service.list_manager_proposals(db, user["id"])


@router.get("/departments")
def list_departments(db: Session = Depends(get_db), user: dict = Depends(require_manager_only)):
    departments = db.query(models.Department).order_by(models.Department.name.asc()).all()
    return [{"id": department.id, "name": department.name} for department in departments]


@router.post("/sqp/propose/{document_id}")
def propose_sqp(document_id: int, db: Session = Depends(get_db), user: dict = Depends(require_manager)):
    return sqp_service.propose_document_to_sqp(db, user["id"], document_id)


@router.delete("/sqp/proposals/{proposal_id}")
def cancel_proposal(proposal_id: int, db: Session = Depends(get_db), user: dict = Depends(require_manager)):
    return sqp_service.cancel_pending_proposal(db, user["id"], proposal_id)


@router.post("/share/document/{doc_id}/to-dept/{dept_id}")
def share_doc_to_dept(doc_id: int, dept_id: int, db: Session = Depends(get_db), user: dict = Depends(require_manager_only)):
    return share_service.share_document_to_department(db, user["id"], doc_id, dept_id)


@router.post("/share/document/{doc_id}/to-user/{username}")
def share_doc_to_user(doc_id: int, username: str, db: Session = Depends(get_db), user: dict = Depends(require_manager_only)):
    return share_service.share_document_to_user(db, user["id"], doc_id, username)


@router.delete("/share/{share_id}")
def revoke_share(share_id: int, db: Session = Depends(get_db), user: dict = Depends(require_manager_only)):
    return share_service.revoke_share(db, user["id"], share_id)


@router.get("/shares")
def list_my_shares(db: Session = Depends(get_db), user: dict = Depends(require_manager_only)):
    return share_service.list_manager_shares(db, user["id"])


@router.get("/contributors")
def list_contributors(db: Session = Depends(get_db), user: dict = Depends(require_manager_only)):
    return share_service.list_contributors(db, user["id"])


@router.post("/contributors/{user_id}")
def add_contributor(user_id: int, db: Session = Depends(get_db), user: dict = Depends(require_manager_only)):
    return share_service.add_contributor(db, user["id"], user_id)


@router.delete("/contributors/{contrib_id}")
def remove_contributor(contrib_id: int, db: Session = Depends(get_db), user: dict = Depends(require_manager_only)):
    return share_service.remove_contributor(db, user["id"], contrib_id)


@router.post("/department/documents/{doc_id}/index")
def index_department_document(doc_id: int, db: Session = Depends(get_db), user: dict = Depends(require_manager_only)):
    """Kích hoạt index RAG cho tài liệu phòng ban chưa được index."""
    manager_user = db.query(models.User).filter(models.User.id == user["id"]).first()
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.department_id == manager_user.department_id,
        models.Document.scope == models.ScopeEnum.department,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại hoặc không thuộc phòng ban")

    if doc.is_indexed:
        return {"status": "already_indexed", "doc_id": doc_id}

    try:
        from rag_engine.chroma_manager import ChromaDBManager
        mgr = ChromaDBManager()
        chunks = mgr.process_and_store_pdf(
            doc.file_path, doc.id, doc.owner_id,
            manager_user.department_id, "department", ""
        )
        doc.is_indexed = True
        db.commit()
        return {"status": "indexed", "doc_id": doc_id, "chunks": chunks}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi index: {str(exc)}")
