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

    def list_by_ids(self, tag_ids: list[int]) -> list[models.Tag]:
        if not tag_ids:
            return []
        return self.db.query(models.Tag).filter(models.Tag.id.in_(tag_ids)).all()

    def list_for_document(self, doc_id: int) -> list[models.Tag]:
        return (
            self.db.query(models.Tag)
            .join(models.DocumentTag, models.DocumentTag.tag_id == models.Tag.id)
            .filter(models.DocumentTag.document_id == doc_id)
            .order_by(models.Tag.name.asc())
            .all()
        )

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

    def add_links(self, links: list[models.DocumentTag]) -> None:
        if not links:
            return
        self.db.add_all(links)
        self.db.commit()

    def replace_document_links(self, doc_id: int, tag_ids: list[int]) -> None:
        self.db.query(models.DocumentTag).filter(models.DocumentTag.document_id == doc_id).delete()
        if tag_ids:
            self.db.add_all([
                models.DocumentTag(document_id=doc_id, tag_id=tag_id)
                for tag_id in tag_ids
            ])
        self.db.commit()

    def commit(self) -> None:
        self.db.commit()

    def delete(self, item) -> None:
        self.db.delete(item)
        self.db.commit()
