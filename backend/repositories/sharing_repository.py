from __future__ import annotations

from sqlalchemy.orm import Session

from database import models


class SharingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_share(self, share_id: int) -> models.SharedDocument | None:
        return self.db.query(models.SharedDocument).filter(models.SharedDocument.id == share_id).first()

    def get_share_by_owner(self, share_id: int, shared_by: int) -> models.SharedDocument | None:
        return (
            self.db.query(models.SharedDocument)
            .filter(
                models.SharedDocument.id == share_id,
                models.SharedDocument.shared_by == shared_by,
            )
            .first()
        )

    def find_share_for_department(self, doc_id: int, dept_id: int) -> models.SharedDocument | None:
        return (
            self.db.query(models.SharedDocument)
            .filter(
                models.SharedDocument.document_id == doc_id,
                models.SharedDocument.shared_with_dept_id == dept_id,
            )
            .first()
        )

    def find_share_for_user(self, doc_id: int, user_id: int) -> models.SharedDocument | None:
        return (
            self.db.query(models.SharedDocument)
            .filter(
                models.SharedDocument.document_id == doc_id,
                models.SharedDocument.shared_with_user_id == user_id,
            )
            .first()
        )

    def find_access_share(self, user: models.User, doc: models.Document) -> models.SharedDocument | None:
        return (
            self.db.query(models.SharedDocument)
            .filter(
                models.SharedDocument.document_id == doc.id,
                (models.SharedDocument.shared_with_user_id == user.id)
                | (models.SharedDocument.shared_with_dept_id == user.department_id),
            )
            .first()
        )

    def list_all(self, search: str = "") -> list[models.SharedDocument]:
        query = self.db.query(models.SharedDocument).order_by(models.SharedDocument.created_at.desc())
        if search:
            query = query.join(models.Document, models.SharedDocument.document_id == models.Document.id).filter(
                models.Document.filename.contains(search)
            )
        return query.all()

    def list_by_owner(self, shared_by: int) -> list[models.SharedDocument]:
        return (
            self.db.query(models.SharedDocument)
            .filter(models.SharedDocument.shared_by == shared_by)
            .order_by(models.SharedDocument.created_at.desc())
            .all()
        )

    def list_contributors_by_department(self, department_id: int | None) -> list[models.Contributor]:
        return (
            self.db.query(models.Contributor)
            .filter(models.Contributor.department_id == department_id)
            .order_by(models.Contributor.created_at.desc())
            .all()
        )

    def get_contributor(self, contrib_id: int, department_id: int | None) -> models.Contributor | None:
        return (
            self.db.query(models.Contributor)
            .filter(
                models.Contributor.id == contrib_id,
                models.Contributor.department_id == department_id,
            )
            .first()
        )

    def find_contributor(self, user_id: int, department_id: int | None) -> models.Contributor | None:
        return (
            self.db.query(models.Contributor)
            .filter(
                models.Contributor.user_id == user_id,
                models.Contributor.department_id == department_id,
            )
            .first()
        )

    def add(self, item):
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, item) -> None:
        self.db.delete(item)
        self.db.commit()
