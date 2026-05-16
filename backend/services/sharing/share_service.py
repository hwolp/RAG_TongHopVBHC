from sqlalchemy.orm import Session

from database import models
from repositories.department_repository import DepartmentRepository
from repositories.document_repository import DocumentRepository
from repositories.user_repository import UserRepository
from utils.errors import forbidden, not_found


class ShareService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.documents = DocumentRepository(db)
        self.departments = DepartmentRepository(db)

    def share_document_to_department(self, manager_user_id: int, doc_id: int, dept_id: int):
        _, doc = self._ensure_manager_can_share_doc(manager_user_id, doc_id)
        return self._share_to_department(doc, manager_user_id, dept_id, validate_target=False)

    def share_document_to_user(self, manager_user_id: int, doc_id: int, username: str):
        _, doc = self._ensure_manager_can_share_doc(manager_user_id, doc_id)
        return self._share_to_user(doc, manager_user_id, username)

    def revoke_share(self, manager_user_id: int, share_id: int):
        share = self.db.query(models.SharedDocument).filter(
            models.SharedDocument.id == share_id,
            models.SharedDocument.shared_by == manager_user_id,
        ).first()
        if not share:
            raise not_found("Chia se khong ton tai")
        self.db.delete(share)
        self.db.commit()
        return {"status": "success"}

    def share_document_to_department_as_admin(self, admin_user_id: int, doc_id: int, dept_id: int):
        self._ensure_admin(admin_user_id)
        doc = self._require_department_doc(doc_id)
        return self._share_to_department(doc, admin_user_id, dept_id, validate_target=True)

    def share_document_to_user_as_admin(self, admin_user_id: int, doc_id: int, username: str):
        self._ensure_admin(admin_user_id)
        doc = self._require_department_doc(doc_id)
        return self._share_to_user(doc, admin_user_id, username)

    def revoke_share_as_admin(self, admin_user_id: int, share_id: int):
        self._ensure_admin(admin_user_id)
        share = self.db.query(models.SharedDocument).filter(models.SharedDocument.id == share_id).first()
        if not share:
            raise not_found("Chia se khong ton tai")
        self.db.delete(share)
        self.db.commit()
        return {"status": "success"}

    def list_all_shares(self, search: str = ""):
        query = self.db.query(models.SharedDocument).order_by(models.SharedDocument.created_at.desc())
        if search:
            query = query.join(models.Document, models.SharedDocument.document_id == models.Document.id).filter(
                models.Document.filename.contains(search)
            )
        return [self._share_to_dict(share, include_shared_by_username=True) for share in query.all()]

    def list_manager_shares(self, manager_user_id: int):
        shares = self.db.query(models.SharedDocument).filter(
            models.SharedDocument.shared_by == manager_user_id,
        ).order_by(models.SharedDocument.created_at.desc()).all()
        return [self._share_to_dict(share, include_shared_by_username=False) for share in shares]

    def list_contributors(self, manager_user_id: int):
        manager = self._require_user(manager_user_id)
        contributors = self.db.query(models.Contributor).filter(
            models.Contributor.department_id == manager.department_id
        ).order_by(models.Contributor.created_at.desc()).all()
        return [
            {
                "id": contributor.id,
                "user_id": contributor.user_id,
                "username": self._username_or_na(contributor.user_id),
                "created_at": str(contributor.created_at),
            }
            for contributor in contributors
        ]

    def add_contributor(self, manager_user_id: int, target_user_id: int):
        manager = self._require_user(manager_user_id)
        existing = self.db.query(models.Contributor).filter(
            models.Contributor.user_id == target_user_id,
            models.Contributor.department_id == manager.department_id,
        ).first()
        if existing:
            return {"status": "exists", "id": existing.id}

        contributor = models.Contributor(
            user_id=target_user_id,
            granted_by=manager_user_id,
            department_id=manager.department_id,
        )
        self.db.add(contributor)
        self.db.commit()
        self.db.refresh(contributor)
        return {"status": "success", "id": contributor.id}

    def remove_contributor(self, manager_user_id: int, contrib_id: int):
        manager = self._require_user(manager_user_id)
        contributor = self.db.query(models.Contributor).filter(
            models.Contributor.id == contrib_id,
            models.Contributor.department_id == manager.department_id,
        ).first()
        if not contributor:
            raise not_found("Contributor not found")
        self.db.delete(contributor)
        self.db.commit()
        return {"status": "success"}

    def _share_to_department(
        self,
        doc: models.Document,
        shared_by: int,
        dept_id: int,
        validate_target: bool,
    ):
        if validate_target and not self.departments.get(dept_id):
            raise not_found("Phong ban khong ton tai")
        existing = self.db.query(models.SharedDocument).filter(
            models.SharedDocument.document_id == doc.id,
            models.SharedDocument.shared_with_dept_id == dept_id,
        ).first()
        if existing:
            return {"status": "exists", "share_id": existing.id}
        share = models.SharedDocument(document_id=doc.id, shared_with_dept_id=dept_id, shared_by=shared_by)
        self.db.add(share)
        self.db.commit()
        self.db.refresh(share)
        return {"status": "success", "share_id": share.id}

    def _share_to_user(self, doc: models.Document, shared_by: int, username: str):
        target_user = self.users.get_by_username(username)
        if not target_user:
            raise not_found("Khong tim thay tai khoan duoc chia se")
        existing = self.db.query(models.SharedDocument).filter(
            models.SharedDocument.document_id == doc.id,
            models.SharedDocument.shared_with_user_id == target_user.id,
        ).first()
        if existing:
            return {"status": "exists", "share_id": existing.id}
        share = models.SharedDocument(
            document_id=doc.id,
            shared_with_dept_id=None,
            shared_with_user_id=target_user.id,
            shared_by=shared_by,
        )
        self.db.add(share)
        self.db.commit()
        self.db.refresh(share)
        return {
            "status": "success",
            "share_id": share.id,
            "shared_with_username": target_user.username,
        }

    def _share_to_dict(self, share: models.SharedDocument, include_shared_by_username: bool) -> dict:
        document = self.documents.get(share.document_id)
        source_department = self.departments.get(document.department_id) if document and document.department_id is not None else None
        target_department = self.departments.get(share.shared_with_dept_id) if share.shared_with_dept_id is not None else None
        target_user = self.users.get(share.shared_with_user_id) if share.shared_with_user_id is not None else None
        result = {
            "id": share.id,
            "document_id": share.document_id,
            "document_filename": document.filename if document else "N/A",
            "document_department_id": document.department_id if document else None,
            "document_department_name": source_department.name if source_department else None,
            "shared_with_dept_id": share.shared_with_dept_id,
            "shared_with_department_name": target_department.name if target_department else None,
            "shared_with_user_id": share.shared_with_user_id,
            "shared_with_username": target_user.username if target_user else None,
            "shared_by": share.shared_by,
            "created_at": str(share.created_at),
        }
        if include_shared_by_username:
            shared_by_user = self.users.get(share.shared_by)
            result["shared_by_username"] = shared_by_user.username if shared_by_user else None
        return result

    def _ensure_manager_can_share_doc(self, manager_user_id: int, doc_id: int):
        manager = self._require_user(manager_user_id)
        doc = self.db.query(models.Document).filter(
            models.Document.id == doc_id,
            models.Document.scope == models.ScopeEnum.department,
            models.Document.department_id == manager.department_id,
        ).first()
        if not doc:
            raise not_found("Tai lieu khong ton tai hoac khong thuoc phong ban cua ban")
        return manager, doc

    def _ensure_admin(self, admin_user_id: int):
        admin_user = self._require_user(admin_user_id)
        if admin_user.role != models.RoleEnum.admin:
            raise forbidden("Chi admin duoc thao tac")
        return admin_user

    def _require_department_doc(self, doc_id: int) -> models.Document:
        doc = self.db.query(models.Document).filter(
            models.Document.id == doc_id,
            models.Document.scope == models.ScopeEnum.department,
        ).first()
        if not doc:
            raise not_found("Tai lieu phong ban khong ton tai")
        return doc

    def _require_user(self, user_id: int):
        user = self.users.get(user_id)
        if not user:
            raise not_found("Khong tim thay nguoi dung")
        return user

    def _username_or_na(self, user_id: int) -> str:
        user = self.users.get(user_id)
        return user.username if user else "N/A"


def _ensure_manager_can_share_doc(db: Session, manager_user_id: int, doc_id: int):
    return ShareService(db)._ensure_manager_can_share_doc(manager_user_id, doc_id)


def share_document_to_department(db: Session, manager_user_id: int, doc_id: int, dept_id: int):
    return ShareService(db).share_document_to_department(manager_user_id, doc_id, dept_id)


def share_document_to_user(db: Session, manager_user_id: int, doc_id: int, username: str):
    return ShareService(db).share_document_to_user(manager_user_id, doc_id, username)


def revoke_share(db: Session, manager_user_id: int, share_id: int):
    return ShareService(db).revoke_share(manager_user_id, share_id)


def _ensure_admin(db: Session, admin_user_id: int):
    return ShareService(db)._ensure_admin(admin_user_id)


def list_all_shares(db: Session, search: str = ""):
    return ShareService(db).list_all_shares(search)


def list_manager_shares(db: Session, manager_user_id: int):
    return ShareService(db).list_manager_shares(manager_user_id)


def share_document_to_department_as_admin(db: Session, admin_user_id: int, doc_id: int, dept_id: int):
    return ShareService(db).share_document_to_department_as_admin(admin_user_id, doc_id, dept_id)


def share_document_to_user_as_admin(db: Session, admin_user_id: int, doc_id: int, username: str):
    return ShareService(db).share_document_to_user_as_admin(admin_user_id, doc_id, username)


def revoke_share_as_admin(db: Session, admin_user_id: int, share_id: int):
    return ShareService(db).revoke_share_as_admin(admin_user_id, share_id)


def list_contributors(db: Session, manager_user_id: int):
    return ShareService(db).list_contributors(manager_user_id)


def add_contributor(db: Session, manager_user_id: int, target_user_id: int):
    return ShareService(db).add_contributor(manager_user_id, target_user_id)


def remove_contributor(db: Session, manager_user_id: int, contrib_id: int):
    return ShareService(db).remove_contributor(manager_user_id, contrib_id)
