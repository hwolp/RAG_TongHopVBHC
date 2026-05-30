from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db_config import get_db
from middleware.auth_middleware import require_admin
from services.admin import config_service, maintenance_service
from services.admin.directory_service import AdminDirectoryService
from services.admin.vector_service import VectorAdminService
from services.documents import document_service
from services.sharing import share_service, sqp_service

router = APIRouter(prefix="/admin", tags=["Quản trị hệ thống"])


def parse_tag_ids(tag_ids: str | None) -> list[int]:
    if not tag_ids:
        return []
    result: list[int] = []
    for raw in tag_ids.split(","):
        value = raw.strip()
        if value:
            result.append(int(value))
    return result


class UpdateDepartmentDocumentRequest(BaseModel):
    filename: str | None = None
    department_id: int | None = None
    tag_ids: list[int] | None = None


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
    return AdminDirectoryService(db).list_departments()


@router.post("/departments")
def create_department(payload: DepartmentRequest, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return AdminDirectoryService(db).create_department(payload.name)


@router.put("/departments/{department_id}")
def update_department(
    department_id: int,
    payload: DepartmentRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    return AdminDirectoryService(db).update_department(department_id, payload.name)


@router.delete("/departments/{department_id}")
def delete_department(department_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return AdminDirectoryService(db).delete_department(department_id)


@router.get("/role-groups")
def list_role_groups(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return AdminDirectoryService(db).list_role_groups()


@router.post("/role-groups")
def create_role_group(payload: RoleGroupRequest, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return AdminDirectoryService(db).create_role_group(payload.name, payload.description)


@router.put("/users/{user_id}/role-group")
def assign_role_group(
    user_id: int,
    payload: AssignRoleGroupRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    return AdminDirectoryService(db).assign_role_group(user_id, payload.role_group_id)


@router.get("/configs")
def list_configs(type: str | None = None, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return config_service.list_configs(db, type)


@router.post("/configs")
def create_config(payload: ConfigRequest, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return config_service.create_config(db, payload.key or "", payload.value or "", payload.type or "metadata")


@router.post("/configs/system/reset")
def reset_system_configs(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return config_service.reset_system_configs(db)


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
    tag_ids: str = Form(""),
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    return await document_service.upload_department_document_for_admin(
        db, admin_user["id"], department_id, file, parse_tag_ids(tag_ids)
    )


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
        tag_ids=payload.tag_ids,
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
    return VectorAdminService().status()


@router.post("/vector/reindex")
def reindex_vector(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return VectorAdminService().reindex(db)


@router.post("/vector/clear")
def clear_vector(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return maintenance_service.clear_collection_data(db)
