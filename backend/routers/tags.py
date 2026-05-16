from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.db_config import get_db
from middleware.auth_middleware import get_current_user, require_admin
from services.documents import tag_service

router = APIRouter(tags=["Tags"])


@router.get("/tags")
def list_tags(db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    return tag_service.list_tags(db)


@router.post("/tags")
def create_tag(name: str, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return tag_service.create_tag(db, name)


@router.put("/tags/{tag_id}")
def update_tag(tag_id: int, name: str, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return tag_service.update_tag(db, tag_id, name)


@router.delete("/tags/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return tag_service.delete_tag(db, tag_id)


@router.post("/documents/{doc_id}/tags/{tag_id}")
def attach_tag(doc_id: int, tag_id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    return tag_service.attach_tag_to_document(db, doc_id, tag_id)


# Legacy compatibility endpoints
@router.get("/employee/tags")
def legacy_employee_tags(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return list_tags(db, user)


@router.post("/employee/tags")
def legacy_employee_create_tag(name: str, db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    return tag_service.create_tag(db, name)


@router.post("/employee/documents/{doc_id}/tag/{tag_id}")
def legacy_attach_tag(doc_id: int, tag_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return attach_tag(doc_id, tag_id, db, user)


@router.get("/admin/tags")
def legacy_admin_tags(db: Session = Depends(get_db), admin_user: dict = Depends(require_admin)):
    return list_tags(db, admin_user)


@router.post("/admin/tags")
def legacy_admin_create_tag(name: str, db: Session = Depends(get_db), admin_user: dict = Depends(require_admin)):
    return create_tag(name, db, admin_user)


@router.put("/admin/tags/{tag_id}")
def legacy_admin_update_tag(tag_id: int, name: str, db: Session = Depends(get_db), admin_user: dict = Depends(require_admin)):
    return update_tag(tag_id, name, db, admin_user)


@router.delete("/admin/tags/{tag_id}")
def legacy_admin_delete_tag(tag_id: int, db: Session = Depends(get_db), admin_user: dict = Depends(require_admin)):
    return delete_tag(tag_id, db, admin_user)
