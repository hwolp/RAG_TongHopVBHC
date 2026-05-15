from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import models
from database.db_config import get_db
from middleware.auth_middleware import require_admin
from services import config_service, document_service, maintenance_service, share_service, sqp_service

router = APIRouter(prefix="/admin", tags=["Quản trị hệ thống"])


class UpdateDepartmentDocumentRequest(BaseModel):
    filename: str | None = None
    department_id: int | None = None


class ShareByUsernameRequest(BaseModel):
    username: str


class RoleGroupRequest(BaseModel):
    name: str
    description: str | None = None


class AssignRoleGroupRequest(BaseModel):
    role_group_id: int | None = None


class ConfigRequest(BaseModel):
    key: str | None = None
    value: str | None = None
    type: str | None = None


class DepartmentRequest(BaseModel):
    name: str


@router.get("/departments")
def list_departments(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    departments = db.query(models.Department).order_by(models.Department.name.asc()).all()
    return [{"id": department.id, "name": department.name} for department in departments]


@router.post("/departments")
def create_department(payload: DepartmentRequest, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Ten phong ban khong hop le")
    if db.query(models.Department).filter(models.Department.name == name).first():
        raise HTTPException(status_code=400, detail="Phong ban da ton tai")

    department = models.Department(name=name)
    db.add(department)
    db.commit()
    db.refresh(department)
    return {"status": "success", "id": department.id, "name": department.name}


@router.put("/departments/{department_id}")
def update_department(
    department_id: int,
    payload: DepartmentRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    department = db.query(models.Department).filter(models.Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Phong ban khong ton tai")
    if department.id == 0:
        raise HTTPException(status_code=400, detail="Khong the doi ten phong ban he thong")

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Ten phong ban khong hop le")
    existed = db.query(models.Department).filter(
        models.Department.name == name,
        models.Department.id != department_id,
    ).first()
    if existed:
        raise HTTPException(status_code=400, detail="Phong ban da ton tai")

    department.name = name
    db.commit()
    return {"status": "success", "id": department.id, "name": department.name}


@router.delete("/departments/{department_id}")
def delete_department(department_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    department = db.query(models.Department).filter(models.Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Phong ban khong ton tai")
    if department.id == 0:
        raise HTTPException(status_code=400, detail="Khong the xoa phong ban he thong")

    users_count = db.query(models.User).filter(models.User.department_id == department_id).count()
    docs_count = db.query(models.Document).filter(models.Document.department_id == department_id).count()
    if users_count or docs_count:
        raise HTTPException(
            status_code=400,
            detail="Phong ban dang co nguoi dung hoac tai lieu, vui long chuyen du lieu truoc khi xoa",
        )

    db.delete(department)
    db.commit()
    return {"status": "success"}


@router.get("/role-groups")
def list_role_groups(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    groups = db.query(models.RoleGroup).order_by(models.RoleGroup.name.asc()).all()
    return [{"id": group.id, "name": group.name, "description": group.description} for group in groups]


@router.post("/role-groups")
def create_role_group(payload: RoleGroupRequest, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Ten nhom quyen khong hop le")
    group = models.RoleGroup(name=name, description=(payload.description or "").strip() or None)
    db.add(group)
    db.commit()
    db.refresh(group)
    return {"status": "success", "id": group.id, "name": group.name, "description": group.description}


@router.put("/users/{user_id}/role-group")
def assign_role_group(
    user_id: int,
    payload: AssignRoleGroupRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Nguoi dung khong ton tai")
    if payload.role_group_id is not None:
        role_group = db.query(models.RoleGroup).filter(models.RoleGroup.id == payload.role_group_id).first()
        if not role_group:
            raise HTTPException(status_code=404, detail="Nhom quyen khong ton tai")
    user.role_group_id = payload.role_group_id
    db.commit()
    return {"status": "success", "user_id": user.id, "role_group_id": user.role_group_id}


@router.get("/configs")
def list_configs(type: str | None = None, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return config_service.list_configs(db, type)


@router.post("/configs")
def create_config(payload: ConfigRequest, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return config_service.create_config(db, payload.key or "", payload.value or "", payload.type or "metadata")


@router.put("/configs/{config_id}")
def update_config(config_id: int, payload: ConfigRequest, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return config_service.update_config(db, config_id, payload.key, payload.value, payload.type)


@router.delete("/configs/{config_id}")
def delete_config(config_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return config_service.delete_config(db, config_id)


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
    from config import CHROMA_PERSIST_DIR
    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    total = 0
    collections = client.list_collections()
    for collection_ref in collections:
        collection = (
            client.get_collection(collection_ref)
            if isinstance(collection_ref, str)
            else collection_ref
        )
        total += collection.count()

    return {"total_vectors": total, "persist_dir": CHROMA_PERSIST_DIR}


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
def clear_vector(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return maintenance_service.clear_collection_data(db)
