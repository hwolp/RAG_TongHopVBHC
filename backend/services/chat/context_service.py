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
    exclude_message_ids: list[int] | None = None,
) -> str:
    excluded_ids = set(exclude_message_ids or [])
    if exclude_message_id is not None:
        excluded_ids.add(exclude_message_id)

    recent_messages = ChatRepository(db).list_recent_messages(session_id, limit * 8)
    turns = []
    pending_ai = None
    for message in recent_messages:
        if message.id in excluded_ids or _skip_history_message(message):
            continue
        content = (message.content or "").strip()
        if message.sender == "ai":
            pending_ai = content
            continue
        if message.sender == "user" and pending_ai:
            turns.append((content, pending_ai))
            pending_ai = None
        if len(turns) >= limit:
            break

    turns.reverse()
    lines = []
    for user_content, ai_content in turns:
        lines.append(f"Nguoi dung: {user_content}")
        lines.append(f"AI: {ai_content}")
    return "\n".join(lines) + ("\n" if lines else "")


def _skip_history_message(message: models.ChatMessage) -> bool:
    content = (message.content or "").strip()
    if not content:
        return True
    if message.sender != "ai":
        return False
    lowered = content.lower()
    ignored_phrases = [
        "tôi không tìm thấy thông tin này trong văn bản đã nạp",
        "xử lý ai thất bại",
        "không thể chờ trạng thái job",
        "đang xử lý câu trả lời",
        "ai đang tra cứu tài liệu",
        "tài liệu đính kèm chưa index xong",
    ]
    return any(phrase in lowered for phrase in ignored_phrases)


def accessible_attachment_ids(db: Session, user_model: models.User, session_id: int) -> list[int]:
    return [
        doc.id
        for doc in _accessible_attached_documents(db, user_model, session_id)
        if doc.is_indexed
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
        doc = documents_repo.get_active(attachment.doc_id)
        if can_access_document(db, user_model, doc):
            documents.append(doc)
    return documents
