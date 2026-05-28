from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import models
from repositories.document_repository import DocumentRepository
from repositories.tag_repository import TagRepository


def list_tags(db: Session):
    return [{"id": tag.id, "name": tag.name} for tag in TagRepository(db).list()]


def create_tag(db: Session, name: str):
    tags = TagRepository(db)
    existing = tags.get_by_name(name)
    if existing:
        return {"status": "exists", "id": existing.id}

    tag = models.Tag(name=name)
    tags.add(tag)
    return {"status": "success", "id": tag.id}


def update_tag(db: Session, tag_id: int, name: str):
    tags = TagRepository(db)
    tag = tags.get(tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    tag.name = name
    tags.commit()
    return {"status": "success"}


def delete_tag(db: Session, tag_id: int):
    tags = TagRepository(db)
    tag = tags.get(tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    tags.delete(tag)
    return {"status": "success"}


def attach_tag_to_document(db: Session, doc_id: int, tag_id: int):
    doc = DocumentRepository(db).get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    tags = TagRepository(db)
    tag = tags.get(tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    existing = tags.get_document_tag(doc_id, tag_id)
    if existing:
        return {"status": "exists"}

    link = models.DocumentTag(document_id=doc_id, tag_id=tag_id)
    tags.add_link(link)
    return {"status": "success"}
