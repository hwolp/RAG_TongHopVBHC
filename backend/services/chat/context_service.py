from sqlalchemy.orm import Session

from database import models
from services.policies.access_policy import can_access_document


def build_recent_chat_history(
    db: Session,
    session_id: int,
    limit: int = 10,
    exclude_message_id: int | None = None,
) -> str:
    query = db.query(models.ChatMessage).filter(models.ChatMessage.session_id == session_id)
    if exclude_message_id is not None:
        query = query.filter(models.ChatMessage.id != exclude_message_id)

    recent_messages = query.order_by(models.ChatMessage.created_at.desc()).limit(limit).all()
    recent_messages.reverse()

    lines = []
    for message in recent_messages:
        role = "Nguoi dung" if message.sender == "user" else "AI"
        lines.append(f"{role}: {message.content}")
    return "\n".join(lines) + ("\n" if lines else "")


def accessible_attachment_ids(db: Session, user_model: models.User, session_id: int) -> list[int]:
    return [
        doc.id
        for doc in _accessible_attached_documents(db, user_model, session_id)
    ]


def split_accessible_attachments_by_index_status(
    db: Session,
    user_model: models.User,
    session_id: int,
) -> tuple[list[int], list[str]]:
    indexed_doc_ids = []
    waiting_filenames = []
    for doc in _accessible_attached_documents(db, user_model, session_id):
        if doc.is_indexed:
            indexed_doc_ids.append(doc.id)
        else:
            waiting_filenames.append(doc.filename)
    return indexed_doc_ids, waiting_filenames


def _accessible_attached_documents(db: Session, user_model: models.User, session_id: int) -> list[models.Document]:
    documents = []
    attachments = db.query(models.SessionDocAttachment).filter(
        models.SessionDocAttachment.session_id == session_id
    ).all()
    for attachment in attachments:
        doc = db.query(models.Document).filter(models.Document.id == attachment.doc_id).first()
        if can_access_document(db, user_model, doc):
            documents.append(doc)
    return documents
