from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db_config import get_db
from middleware.auth_middleware import get_current_user, require_admin, require_manager
from services.documents import document_service, folder_service


class UpdateSQPDocumentRequest(BaseModel):
    filename: str | None = None
    tag_ids: list[int] | None = None


class UpdateDocumentRequest(BaseModel):
    filename: str | None = None
    tag_ids: list[int] | None = None

router = APIRouter(tags=["Tài liệu"])


@router.get("/documents/tree")
def get_document_tree(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Cây thư mục tài liệu (cá nhân / phòng ban / công ty) — dùng cho file picker."""
    return folder_service.get_folder_tree(db, user["id"])


# Canonical endpoints
@router.get("/documents/personal")
def list_personal_documents(search: str = "", db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.list_personal_documents(db, user["id"], search)


@router.post("/documents/personal")
async def upload_personal_document(
    file: UploadFile = File(...),
    tag_ids: list[int] | None = Form(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return await document_service.upload_personal_document(db, user["id"], file, tag_ids)


@router.delete("/documents/personal/{doc_id}")
def delete_personal_document(doc_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.delete_personal_document(db, user["id"], doc_id)


@router.put("/documents/personal/{doc_id}")
def update_personal_document(
    doc_id: int,
    payload: UpdateDocumentRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return document_service.update_personal_document(db, user["id"], doc_id, payload.filename, payload.tag_ids)


@router.get("/documents/department")
def list_department_documents(search: str = "", db: Session = Depends(get_db), user: dict = Depends(require_manager)):
    return document_service.list_department_documents(db, user["id"], search)


@router.post("/documents/department")
async def upload_department_document(
    file: UploadFile = File(...),
    tag_ids: list[int] | None = Form(None),
    db: Session = Depends(get_db),
    user: dict = Depends(require_manager),
):
    return await document_service.upload_department_document(db, user["id"], file, tag_ids)


@router.delete("/documents/department/{doc_id}")
def delete_department_document(doc_id: int, db: Session = Depends(get_db), user: dict = Depends(require_manager)):
    return document_service.delete_department_document(db, user["id"], doc_id)


@router.put("/documents/department/{doc_id}")
def update_department_document(
    doc_id: int,
    payload: UpdateDocumentRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_manager),
):
    return document_service.update_department_document(db, user["id"], doc_id, payload.filename, payload.tag_ids)


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.download_document(db, user["id"], doc_id)


@router.get("/documents/sqp")
def browse_sqp_documents(search: str = "", db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    return document_service.list_sqp_documents(db, search)


@router.post("/documents/sqp")
async def upload_sqp_document(
    file: UploadFile = File(...),
    tag_ids: list[int] | None = Form(None),
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    return await document_service.upload_sqp_document_for_admin(db, admin_user["id"], file, tag_ids)


@router.put("/documents/sqp/{doc_id}")
def update_sqp_document(
    doc_id: int,
    payload: UpdateSQPDocumentRequest,
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    return document_service.update_sqp_document_for_admin(db, admin_user["id"], doc_id, payload.filename, payload.tag_ids)


@router.delete("/documents/sqp/{doc_id}")
def delete_sqp_document(
    doc_id: int,
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    return document_service.delete_sqp_document_for_admin(db, admin_user["id"], doc_id)


@router.get("/documents/company")
def browse_company_documents(search: str = "", db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    return document_service.list_company_documents(db, search)


@router.get("/documents/shared")
def list_shared_documents(search: str = "", db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.list_shared_documents(db, user["id"], search)


@router.get("/documents/sqp/{doc_id}")
def sqp_document_detail(doc_id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    return document_service.get_sqp_document_detail(db, doc_id)


@router.get("/documents/trash")
def list_trash(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.list_deleted_documents(db, user["id"])


@router.get("/documents/{doc_id}")
def document_detail(doc_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.get_document_detail(db, user["id"], doc_id)


@router.post("/documents/{doc_id}/versions")
async def upload_document_version(
    doc_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return await document_service.upload_document_version(db, user["id"], doc_id, file)


@router.get("/documents/{doc_id}/versions")
def list_document_versions(doc_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.list_document_versions(db, user["id"], doc_id)


@router.post("/documents/{doc_id}/restore")
def restore_document(doc_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.restore_document(db, user["id"], doc_id)


# Legacy compatibility endpoints
@router.get("/employee/documents")
def legacy_list_my_documents(search: str = "", db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.list_personal_documents(db, user["id"], search)


@router.post("/employee/documents/upload")
async def legacy_upload_my_document(
    file: UploadFile = File(...),
    tag_ids: list[int] | None = Form(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return await document_service.upload_personal_document(db, user["id"], file, tag_ids)


@router.delete("/employee/documents/{doc_id}")
def legacy_delete_my_document(doc_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.delete_personal_document(db, user["id"], doc_id)


@router.put("/employee/documents/{doc_id}")
def legacy_update_my_document(
    doc_id: int,
    payload: UpdateDocumentRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return document_service.update_personal_document(db, user["id"], doc_id, payload.filename, payload.tag_ids)


@router.get("/employee/documents/{doc_id}/download")
def legacy_download_document(doc_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.download_document(db, user["id"], doc_id)


@router.get("/manager/department/documents")
def legacy_list_department_docs(search: str = "", db: Session = Depends(get_db), user: dict = Depends(require_manager)):
    return document_service.list_department_documents(db, user["id"], search)


@router.get("/employee/department/documents")
def legacy_employee_department_docs(search: str = "", db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    if user.get("role") == "employee":
        return document_service.list_shared_documents(db, user["id"], search)
    return document_service.list_department_documents(db, user["id"], search)


@router.post("/manager/department/documents/upload")
async def legacy_upload_department_doc(
    file: UploadFile = File(...),
    tag_ids: list[int] | None = Form(None),
    db: Session = Depends(get_db),
    user: dict = Depends(require_manager),
):
    return await document_service.upload_department_document(db, user["id"], file, tag_ids)


@router.delete("/manager/department/documents/{doc_id}")
def legacy_delete_department_doc(doc_id: int, db: Session = Depends(get_db), user: dict = Depends(require_manager)):
    return document_service.delete_department_document(db, user["id"], doc_id)


@router.put("/manager/department/documents/{doc_id}")
def legacy_update_department_doc(
    doc_id: int,
    payload: UpdateDocumentRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_manager),
):
    return document_service.update_department_document(db, user["id"], doc_id, payload.filename, payload.tag_ids)


@router.get("/employee/sqp")
def legacy_browse_sqp(search: str = "", db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.list_sqp_documents(db, search)


@router.get("/employee/company")
def legacy_browse_company(search: str = "", db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.list_company_documents(db, search)


@router.get("/employee/shared")
def legacy_shared_docs(search: str = "", db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.list_shared_documents(db, user["id"], search)


@router.get("/employee/sqp/{doc_id}")
def legacy_sqp_detail(doc_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return document_service.get_sqp_document_detail(db, doc_id)
