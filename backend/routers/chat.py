from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db_config import get_db
from middleware.auth_middleware import get_current_user
from schemas.chat_schema import ChatRequest
from services import chat_service, document_service, folder_service

router = APIRouter(tags=["Chat AI"])


class RenameSessionRequest(BaseModel):
    title: str


class SavePromptRequest(BaseModel):
    content: str


class ExecutePromptRequest(BaseModel):
    scope: str = "personal"
    session_id: int | None = None


class AttachDocRequest(BaseModel):
    doc_id: int


class CreateSessionRequest(BaseModel):
    title: str | None = None


@router.post("/chat/ask")
def ask_ai(payload: ChatRequest, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return chat_service.queue_ai_answer(
        db=db,
        user_id=user["id"],
        question=payload.question,
        scope=payload.scope,
        session_id=payload.session_id,
    )


@router.post("/chat/sessions/{session_id}/documents")
async def upload_session_document(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return await document_service.upload_session_personal_document(db, user["id"], session_id, file)


# ── Folder Tree ────────────────────────────────────────────────────────────────

@router.get("/chat/documents/tree")
def get_document_folder_tree(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Trả về cây thư mục tài liệu (cá nhân / phòng ban / công ty) dành cho file picker trong Chat."""
    return folder_service.get_folder_tree(db, user["id"])


# ── Session Attachments ────────────────────────────────────────────────────────

@router.post("/chat/sessions/{session_id}/attach")
def attach_doc(
    session_id: int,
    payload: AttachDocRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Đính kèm tài liệu có sẵn từ thư viện vào session chat."""
    return folder_service.attach_doc_to_session(db, user["id"], session_id, payload.doc_id)


@router.delete("/chat/sessions/{session_id}/attach/{doc_id}")
def detach_doc(
    session_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Gỡ đính kèm tài liệu khỏi session chat."""
    return folder_service.detach_doc_from_session(db, user["id"], session_id, doc_id)


@router.get("/chat/sessions/{session_id}/attachments")
def list_attachments(
    session_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Liệt kê các tài liệu đính kèm của session."""
    return folder_service.list_session_attachments(db, user["id"], session_id)


@router.get("/chat/sessions/{session_id}/documents")
def list_session_documents(
    session_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Liệt kê các tài liệu được upload trực tiếp vào session."""
    return document_service.list_session_documents(db, user["id"], session_id)


@router.delete("/chat/sessions/{session_id}/documents/{doc_id}")
def delete_session_document(
    session_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Xóa tài liệu được upload vào session."""
    return document_service.delete_session_document(db, user["id"], session_id, doc_id)


@router.post("/chat/sessions")
def create_session(
    payload: CreateSessionRequest = CreateSessionRequest(),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return chat_service.create_session(db, user["id"], payload.title)


@router.get("/chat/sessions")
def list_sessions(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return chat_service.list_sessions(db, user["id"])


@router.get("/chat/sessions/{session_id}/messages")
def session_messages(
    session_id: int,
    limit: int = 5,
    before_id: int | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return chat_service.get_session_messages_paginated(
        db=db,
        user_id=user["id"],
        session_id=session_id,
        limit=limit,
        before_id=before_id,
    )


@router.put("/chat/sessions/{session_id}")
def rename_session(session_id: int, payload: RenameSessionRequest, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return chat_service.rename_session(db, user["id"], session_id, payload.title)


@router.delete("/chat/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return chat_service.delete_session(db, user["id"], session_id)


@router.get("/chat/prompts")
def list_prompts(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return chat_service.list_saved_prompts(db, user["id"])


@router.post("/chat/prompts")
def create_prompt(payload: SavePromptRequest, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return chat_service.create_saved_prompt(db, user["id"], payload.content)


@router.delete("/chat/prompts/{prompt_id}")
def delete_prompt(prompt_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return chat_service.delete_saved_prompt(db, user["id"], prompt_id)


@router.post("/chat/prompts/{prompt_id}/execute")
def execute_prompt(
    prompt_id: int,
    payload: ExecutePromptRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return chat_service.execute_saved_prompt(db, user["id"], prompt_id, payload.scope, payload.session_id)


@router.get("/chat/citations/{message_id}")
def message_citations(message_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return chat_service.get_message_citations(db, user["id"], message_id)


# Legacy compatibility endpoints
@router.post("/employee/chat")
def legacy_chat(payload: ChatRequest, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return ask_ai(payload, db, user)


@router.post("/employee/sessions/{session_id}/documents/upload")
async def legacy_upload_session_document(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return await upload_session_document(session_id, file, db, user)


@router.post("/employee/sessions")
def legacy_create_session(
    payload: CreateSessionRequest = CreateSessionRequest(),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return create_session(payload, db, user)


@router.get("/employee/sessions")
def legacy_list_sessions(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return list_sessions(db, user)


@router.get("/employee/sessions/{session_id}/messages")
def legacy_session_messages(
    session_id: int,
    limit: int = 5,
    before_id: int | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return session_messages(session_id, limit, before_id, db, user)


@router.put("/employee/sessions/{session_id}")
def legacy_rename_session(session_id: int, payload: RenameSessionRequest, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return rename_session(session_id, payload, db, user)


@router.delete("/employee/sessions/{session_id}")
def legacy_delete_session(session_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return delete_session(session_id, db, user)


@router.get("/employee/prompts")
def legacy_list_prompts(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return list_prompts(db, user)


@router.post("/employee/prompts")
def legacy_save_prompt(content: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    payload = SavePromptRequest(content=content)
    return create_prompt(payload, db, user)


@router.delete("/employee/prompts/{prompt_id}")
def legacy_delete_prompt(prompt_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return delete_prompt(prompt_id, db, user)
