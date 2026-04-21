from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import models
from database.db_config import get_db
from middleware.auth_middleware import require_admin
from services import document_service, sqp_service

router = APIRouter(prefix="/admin", tags=["Quản trị hệ thống"])


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
