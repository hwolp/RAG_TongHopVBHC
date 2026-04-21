from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import models


def list_tags(db: Session):
    return [{"id": tag.id, "name": tag.name} for tag in db.query(models.Tag).all()]


def create_tag(db: Session, name: str):
    existing = db.query(models.Tag).filter(models.Tag.name == name).first()
    if existing:
        return {"status": "exists", "id": existing.id}

    tag = models.Tag(name=name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return {"status": "success", "id": tag.id}


def update_tag(db: Session, tag_id: int, name: str):
    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    tag.name = name
    db.commit()
    return {"status": "success"}


def delete_tag(db: Session, tag_id: int):
    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    db.delete(tag)
    db.commit()
    return {"status": "success"}


def attach_tag_to_document(db: Session, doc_id: int, tag_id: int):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    existing = db.query(models.DocumentTag).filter(
        models.DocumentTag.document_id == doc_id,
        models.DocumentTag.tag_id == tag_id,
    ).first()
    if existing:
        return {"status": "exists"}

    link = models.DocumentTag(document_id=doc_id, tag_id=tag_id)
    db.add(link)
    db.commit()
    return {"status": "success"}
