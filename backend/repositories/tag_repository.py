from __future__ import annotations

from sqlalchemy.orm import Session

from database import models


class TagRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, tag_id: int) -> models.Tag | None:
        return self.db.query(models.Tag).filter(models.Tag.id == tag_id).first()

    def get_by_name(self, name: str) -> models.Tag | None:
        return self.db.query(models.Tag).filter(models.Tag.name == name).first()

    def list(self) -> list[models.Tag]:
        return self.db.query(models.Tag).all()

    def get_document_tag(self, doc_id: int, tag_id: int) -> models.DocumentTag | None:
        return (
            self.db.query(models.DocumentTag)
            .filter(
                models.DocumentTag.document_id == doc_id,
                models.DocumentTag.tag_id == tag_id,
            )
            .first()
        )

    def add(self, item):
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_link(self, link: models.DocumentTag) -> models.DocumentTag:
        self.db.add(link)
        self.db.commit()
        return link

    def commit(self) -> None:
        self.db.commit()

    def delete(self, item) -> None:
        self.db.delete(item)
        self.db.commit()
