import os
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from config import UPLOAD_DIR_DEPARTMENT, UPLOAD_DIR_PERSONAL, UPLOAD_DIR_SQP
from database import models


def _safe_upload_roots() -> list[Path]:
    roots = []
    for configured in (UPLOAD_DIR_PERSONAL, UPLOAD_DIR_DEPARTMENT, UPLOAD_DIR_SQP):
        root = Path(configured).resolve()
        if str(root) == root.anchor or len(root.parts) < 3:
            continue
        roots.append(root)
    return roots


def _clear_upload_root(root: Path) -> tuple[int, list[str]]:
    deleted = 0
    errors = []
    if not root.exists():
        return deleted, errors

    for child in root.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
            deleted += 1
        except OSError as exc:
            errors.append(f"{child}: {exc}")
    return deleted, errors


def _delete_known_files(paths: list[str]) -> tuple[int, list[str]]:
    deleted = 0
    errors = []
    roots = _safe_upload_roots()

    for raw_path in paths:
        if not raw_path:
            continue
        path = Path(raw_path).resolve()
        if not any(path == root or root in path.parents for root in roots):
            continue
        if not path.exists() or not path.is_file():
            continue
        try:
            path.unlink()
            deleted += 1
        except OSError as exc:
            errors.append(f"{path}: {exc}")
    return deleted, errors


def clear_collection_data(db: Session) -> dict:
    """Reset toàn bộ dữ liệu RAG: vector index, tài liệu upload, chat và job nền."""
    from rag_engine.chroma_manager import ChromaDBManager

    manager = ChromaDBManager()
    manager.admin_clear_db()

    document_paths = [row[0] for row in db.query(models.Document.file_path).all()]
    version_paths = [row[0] for row in db.query(models.DocumentVersion.file_path).all()]
    deleted_files, file_errors = _delete_known_files(document_paths + version_paths)

    counts = {
        "background_jobs": db.query(models.BackgroundJob).delete(synchronize_session=False),
        "chat_messages": db.query(models.ChatMessage).delete(synchronize_session=False),
        "session_doc_attachments": db.query(models.SessionDocAttachment).delete(synchronize_session=False),
        "shared_documents": db.query(models.SharedDocument).delete(synchronize_session=False),
        "sqp_proposals": db.query(models.SQPProposal).delete(synchronize_session=False),
        "document_tags": db.query(models.DocumentTag).delete(synchronize_session=False),
        "document_versions": db.query(models.DocumentVersion).delete(synchronize_session=False),
        "documents": db.query(models.Document).delete(synchronize_session=False),
        "chat_sessions": db.query(models.ChatSession).delete(synchronize_session=False),
    }
    db.commit()

    deleted_upload_entries = 0
    for root in _safe_upload_roots():
        root_deleted, root_errors = _clear_upload_root(root)
        deleted_upload_entries += root_deleted
        file_errors.extend(root_errors)
        os.makedirs(root, exist_ok=True)

    return {
        "status": "success",
        "message": "Da xoa collection, vector index, hoi thoai, tin nhan chat va file upload",
        "deleted": {
            **counts,
            "known_files": deleted_files,
            "upload_entries": deleted_upload_entries,
        },
        "file_errors": file_errors,
    }
