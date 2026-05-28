import os
from typing import Optional

from fastapi import UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from config import UPLOAD_DIR_DEPARTMENT, UPLOAD_DIR_PERSONAL, UPLOAD_DIR_SQP
from database import models
from repositories.chat_repository import ChatRepository
from repositories.department_repository import DepartmentRepository
from repositories.document_repository import DocumentRepository
from repositories.job_repository import BackgroundJobRepository
from repositories.user_repository import UserRepository
from services.jobs import job_service
from services.policies.access_policy import can_access_document
from utils.enum_utils import enum_value
from utils.errors import bad_request, forbidden, not_found
from utils.file_storage import (
    delete_file_if_exists,
    replace_file_path,
    safe_filename,
    save_upload_file,
    stored_filename,
)
from utils.time_utils import utc_now, utc_timestamp


def _scope_str(scope_value) -> str:
    return enum_value(scope_value)


def _safe_filename(filename: str) -> str:
    return safe_filename(filename)


def _stored_filename(original_filename: str) -> str:
    return stored_filename(original_filename)


def _save_upload_file(file: UploadFile, target_dir: str, stored_name: str | None = None) -> tuple[str, str]:
    return save_upload_file(file, target_dir, stored_name)


class DocumentIndexCoordinator:
    def __init__(self, db: Session):
        self.db = db
        self.jobs = BackgroundJobRepository(db)

    def upload_response(self, doc: models.Document, created_by: int | None, force_admin_chunking: bool = False) -> dict:
        job = job_service.create_index_job(self.db, doc, created_by, force_admin_chunking)
        if not job:
            return {"status": "success", "doc_id": doc.id, "job_id": None}
        return {"status": "queued", "doc_id": doc.id, "job_id": job.id}

    def index_status(self, doc: models.Document) -> str:
        if doc.is_indexed:
            return "indexed"
        job = self.jobs.latest_for_document(doc.id, job_service.JOB_TYPE_INDEX_DOCUMENT)
        if job and job.status in {"queued", "running", "failed"}:
            return job.status
        return "not_    indexed"

    def queue_department_index(self, manager_user_id: int, doc_id: int) -> dict:
        manager = UserRepository(self.db).get(manager_user_id)
        if not manager:
            raise not_found("Khong tim thay nguoi dung")

        doc = DocumentRepository(self.db).get_department_active(doc_id, manager.department_id)
        if not doc:
            raise not_found("Tài liệu không tồn tại hoặc không thuộc phòng ban")

        if doc.is_indexed:
            return {"status": "already_indexed", "doc_id": doc_id}

        running_job = self.jobs.latest_active_for_document(
            doc.id,
            job_service.JOB_TYPE_INDEX_DOCUMENT,
            [job_service.STATUS_QUEUED, job_service.STATUS_RUNNING],
        )
        if running_job:
            return {"status": running_job.status, "doc_id": doc_id, "job_id": running_job.id}

        job = job_service.create_index_job(self.db, doc, manager_user_id)
        if not job:
            raise bad_request("Định dạng file chưa hỗ trợ index")
        return {"status": "queued", "doc_id": doc_id, "job_id": job.id}


def _upload_response_with_index_job(
    db: Session,
    doc: models.Document,
    created_by: int | None,
    force_admin_chunking: bool = False,
) -> dict:
    return DocumentIndexCoordinator(db).upload_response(doc, created_by, force_admin_chunking)


def _index_status(db: Session, doc: models.Document) -> str:
    return DocumentIndexCoordinator(db).index_status(doc)


class DocumentPresenter:
    def __init__(self, indexer: DocumentIndexCoordinator):
        self.indexer = indexer

    def personal_item(self, doc: models.Document) -> dict:
        return {
            "id": doc.id,
            "filename": doc.filename,
            "scope": enum_value(doc.scope),
            "is_indexed": doc.is_indexed,
            "index_status": self.indexer.index_status(doc),
            "uploaded_at": str(doc.uploaded_at),
        }

    def department_item(self, doc: models.Document) -> dict:
        return {
            "id": doc.id,
            "filename": doc.filename,
            "uploaded_at": str(doc.uploaded_at),
            "owner_id": doc.owner_id,
            "department_id": doc.department_id,
            "is_indexed": doc.is_indexed,
            "index_status": self.indexer.index_status(doc),
        }

    def detail(self, doc: models.Document) -> dict:
        return {
            "id": doc.id,
            "filename": doc.filename,
            "file_path": doc.file_path,
            "scope": enum_value(doc.scope),
            "summary": doc.summary,
            "is_indexed": doc.is_indexed,
            "version_number": doc.version_number or 1,
            "uploaded_at": str(doc.uploaded_at),
            "owner_id": doc.owner_id,
            "department_id": doc.department_id,
        }

    def deleted_item(self, doc: models.Document) -> dict:
        return {
            "id": doc.id,
            "filename": doc.filename,
            "scope": enum_value(doc.scope),
            "deleted_at": str(doc.deleted_at),
            "version_number": doc.version_number or 1,
        }

    def session_item(self, doc: models.Document) -> dict:
        return {
            "id": doc.id,
            "filename": doc.filename,
            "is_indexed": doc.is_indexed,
            "index_status": self.indexer.index_status(doc),
            "uploaded_at": str(doc.uploaded_at),
        }


class DocumentQueryService:
    def __init__(self, db: Session):
        self.db = db
        self.documents = DocumentRepository(db)
        self.chat = ChatRepository(db)
        self.users = UserRepository(db)
        self.presenter = DocumentPresenter(DocumentIndexCoordinator(db))

    def list_personal_documents(self, user_id: int, search: str = ""):
        return [self.presenter.personal_item(doc) for doc in self.documents.list_personal_library(user_id, search)]

    def list_department_documents(self, user_id: int, search: str = ""):
        user = self._require_user(user_id)
        if user.role == models.RoleEnum.admin:
            docs = self.documents.list_department(search=search)
        elif user.role == models.RoleEnum.manager:
            docs = self.documents.list_department(user.department_id, search)
        else:
            raise forbidden("Chi manager/admin duoc xem danh sach tai lieu phong ban")
        return [self.presenter.department_item(doc) for doc in docs]

    def list_sqp_documents(self, search: str = ""):
        return [self.presenter.department_item(doc) for doc in self.documents.list_sqp(search)]

    def list_company_documents(self, search: str = ""):
        return self.list_sqp_documents(search)

    def list_shared_documents(self, user_id: int, search: str = ""):
        user = self._require_user(user_id)
        docs = self.documents.list_shared_with_user(user, search)
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

    def download_document(self, user_id: int, doc_id: int):
        user = self._require_user(user_id)
        doc = self._require_active_document(doc_id)
        if not can_access_document(self.db, user, doc):
            raise forbidden("Khong co quyen tai tai lieu nay")
        return FileResponse(doc.file_path, filename=doc.filename)

    def get_document_detail(self, user_id: int, doc_id: int):
        user = self._require_user(user_id)
        doc = self._require_active_document(doc_id)
        if not can_access_document(self.db, user, doc):
            raise forbidden("Khong co quyen xem tai lieu nay")
        return self.presenter.detail(doc)

    def get_sqp_document_detail(self, doc_id: int):
        doc = self.documents.get_by_scope(doc_id, models.ScopeEnum.sqp)
        if not doc:
            raise not_found("Quy dinh khong ton tai")
        return {
            "id": doc.id,
            "filename": doc.filename,
            "file_path": doc.file_path,
            "summary": doc.summary,
            "uploaded_at": str(doc.uploaded_at),
        }

    def list_document_versions(self, user_id: int, doc_id: int):
        self.get_document_detail(user_id, doc_id)
        doc = self.documents.get(doc_id)
        versions = self.documents.list_versions(doc_id)
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

    def list_deleted_documents(self, user_id: int):
        user = self._require_user(user_id)
        return [self.presenter.deleted_item(doc) for doc in self.documents.list_deleted_for_user(user)]

    def list_session_documents(self, user_id: int, session_id: int) -> list[dict]:
        session = self.chat.get_session(session_id, user_id)
        if not session:
            raise not_found("Session không tồn tại")
        docs = self.documents.list_session_documents(user_id, session_id)
        return [self.presenter.session_item(doc) for doc in docs]

    def _require_user(self, user_id: int) -> models.User:
        user = self.users.get(user_id)
        if not user:
            raise not_found("Khong tim thay nguoi dung")
        return user

    def _require_active_document(self, doc_id: int) -> models.Document:
        doc = self.documents.get_active(doc_id)
        if not doc:
            raise not_found("Tai lieu khong ton tai")
        return doc


class DocumentUploadService:
    def __init__(self, db: Session):
        self.db = db
        self.documents = DocumentRepository(db)
        self.users = UserRepository(db)
        self.departments = DepartmentRepository(db)
        self.chat = ChatRepository(db)
        self.indexer = DocumentIndexCoordinator(db)

    async def upload_personal_document(self, user_id: int, file: UploadFile):
        clean_name = safe_filename(file.filename)
        target_dir = os.path.join(UPLOAD_DIR_PERSONAL, f"user_{user_id}")
        clean_name, file_path = save_upload_file(file, target_dir, stored_filename(clean_name))
        doc = self.documents.add(models.Document(
            filename=clean_name,
            file_path=file_path,
            owner_id=user_id,
            scope=models.ScopeEnum.personal,
        ))
        return self.indexer.upload_response(doc, user_id)

    async def upload_session_personal_document(self, user_id: int, session_id: int, file: UploadFile):
        session = self.chat.get_session(session_id, user_id)
        if not session:
            raise not_found("Phien khong ton tai")

        clean_name = safe_filename(file.filename)
        target_dir = os.path.join(UPLOAD_DIR_PERSONAL, f"user_{user_id}", "sessions", f"session_{session_id}")
        clean_name, file_path = save_upload_file(file, target_dir, stored_filename(clean_name))
        doc = self.documents.add(models.Document(
            filename=clean_name,
            file_path=file_path,
            owner_id=user_id,
            scope=models.ScopeEnum.personal,
            chat_session_id=session_id,
        ))
        return self.indexer.upload_response(doc, user_id)

    async def upload_department_document(self, manager_user_id: int, file: UploadFile):
        manager = self._require_user(manager_user_id)
        clean_name, file_path = save_upload_file(file, UPLOAD_DIR_DEPARTMENT)
        doc = self.documents.add(models.Document(
            filename=clean_name,
            file_path=file_path,
            owner_id=manager_user_id,
            department_id=manager.department_id,
            scope=models.ScopeEnum.department,
        ))
        return self.indexer.upload_response(doc, manager_user_id)

    async def upload_department_document_for_admin(self, admin_user_id: int, department_id: int, file: UploadFile):
        self._require_admin(admin_user_id)
        if not self.departments.get(department_id):
            raise not_found("Phong ban khong ton tai")

        clean_name, file_path = save_upload_file(file, UPLOAD_DIR_DEPARTMENT)
        doc = self.documents.add(models.Document(
            filename=clean_name,
            file_path=file_path,
            owner_id=admin_user_id,
            department_id=department_id,
            scope=models.ScopeEnum.department,
        ))
        return self.indexer.upload_response(doc, admin_user_id)

    async def upload_document_version(self, user_id: int, doc_id: int, file: UploadFile):
        user = self._require_user(user_id)
        doc = self.documents.get_active(doc_id)
        if not doc:
            raise not_found("Tai lieu khong ton tai")
        if not self._can_update_document(user, doc):
            raise forbidden("Khong co quyen cap nhat tai lieu nay")

        clean_name = safe_filename(file.filename)
        base_dir = os.path.dirname(doc.file_path) or UPLOAD_DIR_PERSONAL
        if not self.documents.has_versions(doc_id):
            self.documents.add_version(models.DocumentVersion(
                document_id=doc.id,
                filename=doc.filename,
                file_path=doc.file_path,
                version_number=doc.version_number or 1,
                uploaded_by=doc.owner_id,
                created_at=doc.uploaded_at,
            ))

        next_version = (doc.version_number or 1) + 1
        stored_name = f"v{next_version}_{utc_timestamp()}_{clean_name}"
        clean_name, file_path = save_upload_file(file, base_dir, stored_name)
        version = models.DocumentVersion(
            document_id=doc.id,
            filename=clean_name,
            file_path=file_path,
            version_number=next_version,
            uploaded_by=user_id,
        )
        self.documents.add_version(version)
        doc.filename = clean_name
        doc.file_path = file_path
        doc.version_number = next_version
        doc.is_indexed = False
        self.documents.commit()
        self.documents.refresh(version)
        job = job_service.create_index_job(self.db, doc, user_id)
        return {
            "status": "queued" if job else "success",
            "doc_id": doc.id,
            "version_id": version.id,
            "version_number": version.version_number,
            "job_id": job.id if job else None,
        }

    async def upload_sqp_document_for_admin(self, admin_user_id: int, file: UploadFile):
        self._require_admin(admin_user_id)
        clean_name, file_path = save_upload_file(file, UPLOAD_DIR_SQP)
        doc = self.documents.add(models.Document(
            filename=clean_name,
            file_path=file_path,
            owner_id=admin_user_id,
            scope=models.ScopeEnum.sqp,
        ))
        return self.indexer.upload_response(doc, admin_user_id, force_admin_chunking=True)

    def _require_user(self, user_id: int) -> models.User:
        user = self.users.get(user_id)
        if not user:
            raise not_found("Khong tim thay nguoi dung")
        return user

    def _require_admin(self, user_id: int) -> models.User:
        user = self._require_user(user_id)
        if user.role != models.RoleEnum.admin:
            raise forbidden("Chi admin duoc thao tac")
        return user

    @staticmethod
    def _can_update_document(user: models.User, doc: models.Document) -> bool:
        scope = doc.scope.value if hasattr(doc.scope, "value") else str(doc.scope)
        if user.role == models.RoleEnum.admin:
            return True
        if scope == models.ScopeEnum.personal.value:
            return doc.owner_id == user.id
        if scope == models.ScopeEnum.department.value:
            return user.role == models.RoleEnum.manager and doc.department_id == user.department_id
        if scope == models.ScopeEnum.sqp.value:
            return False
        return False


class DocumentLifecycleService:
    def __init__(self, db: Session):
        self.db = db
        self.documents = DocumentRepository(db)
        self.users = UserRepository(db)
        self.departments = DepartmentRepository(db)
        self.chat = ChatRepository(db)

    def delete_personal_document(self, user_id: int, doc_id: int):
        doc = self.documents.get_owned_personal_active(doc_id, user_id)
        if not doc:
            raise not_found("Tai lieu khong ton tai")
        doc.is_deleted = True
        doc.deleted_at = utc_now()
        self.documents.commit()
        return {"status": "success"}

    def delete_department_document(self, manager_user_id: int, doc_id: int):
        manager = self._require_user(manager_user_id)
        department_id = None if manager.role == models.RoleEnum.admin else manager.department_id
        doc = self.documents.get_department_active(doc_id, department_id)
        if not doc:
            raise not_found("Tai lieu khong ton tai trong phong ban")
        delete_file_if_exists(doc.file_path)
        self.documents.delete(doc)
        return {"status": "success"}

    def update_department_document_for_admin(
        self,
        admin_user_id: int,
        doc_id: int,
        filename: Optional[str] = None,
        department_id: Optional[int] = None,
    ):
        self._require_admin(admin_user_id)
        doc = self.documents.get_by_scope(doc_id, models.ScopeEnum.department, include_deleted=True)
        if not doc:
            raise not_found("Tai lieu phong ban khong ton tai")

        if filename is not None and filename.strip():
            doc.filename, doc.file_path = replace_file_path(doc.file_path, filename)

        if department_id is not None:
            if not self.departments.get(department_id):
                raise not_found("Phong ban khong ton tai")
            doc.department_id = department_id

        self.documents.commit()
        self.documents.refresh(doc)
        return {
            "status": "success",
            "id": doc.id,
            "filename": doc.filename,
            "department_id": doc.department_id,
        }

    def update_sqp_document_for_admin(
        self,
        admin_user_id: int,
        doc_id: int,
        filename: Optional[str] = None,
    ):
        self._require_admin(admin_user_id)
        doc = self.documents.get_by_scope(doc_id, models.ScopeEnum.sqp, include_deleted=True)
        if not doc:
            raise not_found("Tai lieu SQP khong ton tai")

        if filename is not None and filename.strip():
            doc.filename, doc.file_path = replace_file_path(doc.file_path, filename)

        self.documents.commit()
        self.documents.refresh(doc)
        return {"status": "success", "id": doc.id, "filename": doc.filename}

    def delete_sqp_document_for_admin(self, admin_user_id: int, doc_id: int):
        self._require_admin(admin_user_id)
        doc = self.documents.get_by_scope(doc_id, models.ScopeEnum.sqp, include_deleted=True)
        if not doc:
            raise not_found("Tai lieu SQP khong ton tai")
        delete_file_if_exists(doc.file_path)
        self.documents.delete(doc)
        return {"status": "success"}

    def restore_document(self, user_id: int, doc_id: int):
        user = self._require_user(user_id)
        doc = self.documents.get(doc_id)
        if not doc or not doc.is_deleted:
            raise not_found("Tai lieu trong thung rac khong ton tai")
        if user.role != models.RoleEnum.admin and doc.owner_id != user_id:
            raise forbidden("Khong co quyen khoi phuc tai lieu nay")
        doc.is_deleted = False
        doc.deleted_at = None
        self.documents.commit()
        return {"status": "success", "doc_id": doc.id}

    def delete_session_document(self, user_id: int, session_id: int, doc_id: int) -> dict:
        session = self.chat.get_session(session_id, user_id)
        if not session:
            raise not_found("Session không tồn tại")

        doc = self.documents.get_session_document(doc_id, user_id, session_id)
        if not doc:
            raise not_found("Tài liệu không tồn tại trong session")

        delete_file_if_exists(doc.file_path)
        self.documents.delete(doc)
        return {"status": "success", "message": "Đã xóa tài liệu khỏi session"}

    def _require_user(self, user_id: int) -> models.User:
        user = self.users.get(user_id)
        if not user:
            raise not_found("Khong tim thay nguoi dung")
        return user

    def _require_admin(self, user_id: int) -> models.User:
        user = self._require_user(user_id)
        if user.role != models.RoleEnum.admin:
            raise forbidden("Chi admin duoc thao tac")
        return user


def list_personal_documents(db: Session, user_id: int, search: str = ""):
    return DocumentQueryService(db).list_personal_documents(user_id, search)


async def upload_personal_document(db: Session, user_id: int, file: UploadFile):
    return await DocumentUploadService(db).upload_personal_document(user_id, file)


async def upload_session_personal_document(db: Session, user_id: int, session_id: int, file: UploadFile):
    return await DocumentUploadService(db).upload_session_personal_document(user_id, session_id, file)


def list_department_documents(db: Session, user_id: int, search: str = ""):
    return DocumentQueryService(db).list_department_documents(user_id, search)


async def upload_department_document(db: Session, manager_user_id: int, file: UploadFile):
    return await DocumentUploadService(db).upload_department_document(manager_user_id, file)


async def upload_department_document_for_admin(db: Session, admin_user_id: int, department_id: int, file: UploadFile):
    return await DocumentUploadService(db).upload_department_document_for_admin(admin_user_id, department_id, file)


def delete_personal_document(db: Session, user_id: int, doc_id: int):
    return DocumentLifecycleService(db).delete_personal_document(user_id, doc_id)


def delete_department_document(db: Session, manager_user_id: int, doc_id: int):
    return DocumentLifecycleService(db).delete_department_document(manager_user_id, doc_id)


def update_department_document_for_admin(
    db: Session,
    admin_user_id: int,
    doc_id: int,
    filename: Optional[str] = None,
    department_id: Optional[int] = None,
):
    return DocumentLifecycleService(db).update_department_document_for_admin(
        admin_user_id, doc_id, filename, department_id
    )


def download_document(db: Session, user_id: int, doc_id: int):
    return DocumentQueryService(db).download_document(user_id, doc_id)


def get_document_detail(db: Session, user_id: int, doc_id: int):
    return DocumentQueryService(db).get_document_detail(user_id, doc_id)


def list_document_versions(db: Session, user_id: int, doc_id: int):
    return DocumentQueryService(db).list_document_versions(user_id, doc_id)


async def upload_document_version(db: Session, user_id: int, doc_id: int, file: UploadFile):
    return await DocumentUploadService(db).upload_document_version(user_id, doc_id, file)


def list_deleted_documents(db: Session, user_id: int):
    return DocumentQueryService(db).list_deleted_documents(user_id)


def restore_document(db: Session, user_id: int, doc_id: int):
    return DocumentLifecycleService(db).restore_document(user_id, doc_id)


def list_sqp_documents(db: Session, search: str = ""):
    return DocumentQueryService(db).list_sqp_documents(search)


def list_company_documents(db: Session, search: str = ""):
    return DocumentQueryService(db).list_company_documents(search)


async def upload_sqp_document_for_admin(db: Session, admin_user_id: int, file: UploadFile):
    return await DocumentUploadService(db).upload_sqp_document_for_admin(admin_user_id, file)


def update_sqp_document_for_admin(
    db: Session,
    admin_user_id: int,
    doc_id: int,
    filename: Optional[str] = None,
):
    return DocumentLifecycleService(db).update_sqp_document_for_admin(admin_user_id, doc_id, filename)


def delete_sqp_document_for_admin(db: Session, admin_user_id: int, doc_id: int):
    return DocumentLifecycleService(db).delete_sqp_document_for_admin(admin_user_id, doc_id)


def get_sqp_document_detail(db: Session, doc_id: int):
    return DocumentQueryService(db).get_sqp_document_detail(doc_id)


def list_shared_documents(db: Session, user_id: int, search: str = ""):
    return DocumentQueryService(db).list_shared_documents(user_id, search)


def list_session_documents(db: Session, user_id: int, session_id: int) -> list[dict]:
    return DocumentQueryService(db).list_session_documents(user_id, session_id)


def delete_session_document(db: Session, user_id: int, session_id: int, doc_id: int) -> dict:
    return DocumentLifecycleService(db).delete_session_document(user_id, session_id, doc_id)


def queue_department_document_index(db: Session, manager_user_id: int, doc_id: int) -> dict:
    return DocumentIndexCoordinator(db).queue_department_index(manager_user_id, doc_id)
