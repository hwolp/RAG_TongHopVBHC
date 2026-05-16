from sqlalchemy.orm import Session

from database import models


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, doc_id: int) -> models.Document | None:
        return self.db.query(models.Document).filter(models.Document.id == doc_id).first()

    def get_active(self, doc_id: int) -> models.Document | None:
        return (
            self.db.query(models.Document)
            .filter(models.Document.id == doc_id, models.Document.is_deleted == False)
            .first()
        )

    def list_personal_library(self, user_id: int, search: str = "") -> list[models.Document]:
        query = self.db.query(models.Document).filter(
            models.Document.owner_id == user_id,
            models.Document.scope == models.ScopeEnum.personal,
            models.Document.is_deleted == False,
            models.Document.chat_session_id == None,
        )
        return self._apply_search(query, search).order_by(models.Document.uploaded_at.desc()).all()

    def list_department(self, department_id: int | None = None, search: str = "") -> list[models.Document]:
        query = self.db.query(models.Document).filter(
            models.Document.scope == models.ScopeEnum.department,
            models.Document.is_deleted == False,
        )
        if department_id is not None:
            query = query.filter(models.Document.department_id == department_id)
        return self._apply_search(query, search).order_by(models.Document.uploaded_at.desc()).all()

    def list_sqp(self, search: str = "") -> list[models.Document]:
        query = self.db.query(models.Document).filter(
            models.Document.scope == models.ScopeEnum.sqp,
            models.Document.is_deleted == False,
        )
        return self._apply_search(query, search).order_by(models.Document.uploaded_at.desc()).all()

    def list_deleted_for_user(self, user: models.User) -> list[models.Document]:
        query = self.db.query(models.Document).filter(models.Document.is_deleted == True)
        if user.role != models.RoleEnum.admin:
            query = query.filter(models.Document.owner_id == user.id)
        return query.order_by(models.Document.deleted_at.desc()).all()

    def list_shared_with_user(self, user: models.User, search: str = "") -> list[models.Document]:
        shared_doc_ids = self.db.query(models.SharedDocument.document_id).filter(
            (models.SharedDocument.shared_with_user_id == user.id)
            | (models.SharedDocument.shared_with_dept_id == user.department_id)
        )
        query = self.db.query(models.Document).filter(
            models.Document.id.in_(shared_doc_ids),
            models.Document.scope == models.ScopeEnum.department,
            models.Document.is_deleted == False,
        )
        return self._apply_search(query, search).order_by(models.Document.uploaded_at.desc()).all()

    def list_session_documents(self, user_id: int, session_id: int) -> list[models.Document]:
        return (
            self.db.query(models.Document)
            .filter(
                models.Document.chat_session_id == session_id,
                models.Document.owner_id == user_id,
            )
            .order_by(models.Document.uploaded_at.desc())
            .all()
        )

    def list_versions(self, doc_id: int) -> list[models.DocumentVersion]:
        return (
            self.db.query(models.DocumentVersion)
            .filter(models.DocumentVersion.document_id == doc_id)
            .order_by(models.DocumentVersion.version_number.asc())
            .all()
        )

    def has_versions(self, doc_id: int) -> bool:
        return (
            self.db.query(models.DocumentVersion)
            .filter(models.DocumentVersion.document_id == doc_id)
            .first()
            is not None
        )

    def add(self, doc: models.Document) -> models.Document:
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def commit(self) -> None:
        self.db.commit()

    def delete(self, doc: models.Document) -> None:
        self.db.delete(doc)
        self.db.commit()

    @staticmethod
    def _apply_search(query, search: str):
        if search:
            return query.filter(models.Document.filename.contains(search))
        return query

