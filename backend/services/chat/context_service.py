from sqlalchemy.orm import Session

from database import models
from repositories.chat_repository import ChatRepository
from repositories.document_repository import DocumentRepository
from services.policies.access_policy import can_access_document


def build_recent_chat_history(
    db: Session,
    session_id: int,
    limit: int = 3,
    exclude_message_id: int | None = None,
) -> str:
    recent_messages = ChatRepository(db).list_recent_messages(session_id, limit, exclude_message_id)
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
    chat = ChatRepository(db)
    documents_repo = DocumentRepository(db)
    documents = []
    attachments = chat.list_attachments(session_id)
    for attachment in attachments:
        doc = documents_repo.get(attachment.doc_id)
        if can_access_document(db, user_model, doc):
            documents.append(doc)
    return documents
