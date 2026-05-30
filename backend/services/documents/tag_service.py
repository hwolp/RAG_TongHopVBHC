from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import models
from repositories.document_repository import DocumentRepository
from repositories.tag_repository import TagRepository
from repositories.user_repository import UserRepository
from services.policies.access_policy import can_access_document
from utils.enum_utils import enum_value
from utils.errors import forbidden, not_found


def list_tags(db: Session):
    return [{"id": tag.id, "name": tag.name} for tag in TagRepository(db).list()]


def _normalize_name(name: str) -> str:
    return " ".join((name or "").strip().split())


def _tag_to_dict(tag: models.Tag) -> dict:
    return {"id": tag.id, "name": tag.name}


def create_tag(db: Session, name: str):
    name = _normalize_name(name)
    if not name:
        raise HTTPException(status_code=400, detail="Tag name is required")

    tags = TagRepository(db)
    existing = tags.get_by_name(name)
    if existing:
        return {"status": "exists", "id": existing.id, "name": existing.name}

    tag = models.Tag(name=name)
    tags.add(tag)
    return {"status": "success", "id": tag.id, "name": tag.name}


def update_tag(db: Session, tag_id: int, name: str):
    name = _normalize_name(name)
    if not name:
        raise HTTPException(status_code=400, detail="Tag name is required")

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


def get_document_tags(db: Session, user_id: int, doc_id: int):
    user = UserRepository(db).get(user_id)
    if not user:
        raise not_found("Khong tim thay nguoi dung")
    doc = DocumentRepository(db).get_active(doc_id)
    if not doc:
        raise not_found("Tai lieu khong ton tai")
    if not can_access_document(db, user, doc):
        raise forbidden("Khong co quyen xem tai lieu nay")
    return [_tag_to_dict(tag) for tag in TagRepository(db).list_for_document(doc_id)]


def set_document_tags(db: Session, user_id: int, doc_id: int, tag_ids: list[int]):
    user = UserRepository(db).get(user_id)
    if not user:
        raise not_found("Khong tim thay nguoi dung")
    doc = DocumentRepository(db).get_active(doc_id)
    if not doc:
        raise not_found("Tai lieu khong ton tai")
    if not can_update_document_tags(user, doc):
        raise forbidden("Khong co quyen cap nhat tag cua tai lieu nay")

    unique_ids = list(dict.fromkeys(tag_ids or []))
    tags = TagRepository(db)
    found = tags.list_by_ids(unique_ids)
    found_ids = {tag.id for tag in found}
    missing = [tag_id for tag_id in unique_ids if tag_id not in found_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Tag not found: {missing[0]}")

    tags.replace_document_tags(doc_id, unique_ids)
    return {"status": "success", "doc_id": doc_id, "tags": [_tag_to_dict(tag) for tag in found]}


def apply_tags_to_document(db: Session, doc_id: int, tag_ids: list[int] | None):
    unique_ids = list(dict.fromkeys(tag_ids or []))
    if not unique_ids:
        return []
    tags = TagRepository(db)
    found = tags.list_by_ids(unique_ids)
    found_ids = {tag.id for tag in found}
    if len(found_ids) != len(unique_ids):
        missing = next(tag_id for tag_id in unique_ids if tag_id not in found_ids)
        raise HTTPException(status_code=404, detail=f"Tag not found: {missing}")
    tags.replace_document_tags(doc_id, unique_ids)
    return [_tag_to_dict(tag) for tag in found]


def can_update_document_tags(user: models.User, doc: models.Document) -> bool:
    scope = enum_value(doc.scope)
    if user.role == models.RoleEnum.admin:
        return True
    if scope == models.ScopeEnum.personal.value:
        return doc.owner_id == user.id
    if scope == models.ScopeEnum.department.value:
        return user.role == models.RoleEnum.manager and doc.department_id == user.department_id
    return False
