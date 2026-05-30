import os
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from services.admin.config_service import get_upload_dirs
from repositories.document_repository import DocumentRepository
from repositories.maintenance_repository import MaintenanceRepository


def _safe_upload_roots(db: Session) -> list[Path]:
    roots = []
    upload_dirs = get_upload_dirs(db)
    for configured in upload_dirs.values():
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


def _delete_known_files(db: Session, paths: list[str]) -> tuple[int, list[str]]:
    deleted = 0
    errors = []
    roots = _safe_upload_roots(db)

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

    manager = ChromaDBManager(db=db)
    manager.admin_clear_db()

    documents = DocumentRepository(db)
    document_paths = documents.list_file_paths()
    version_paths = documents.list_version_paths()
    deleted_files, file_errors = _delete_known_files(db, document_paths + version_paths)

    counts = MaintenanceRepository(db).clear_rag_data()

    deleted_upload_entries = 0
    for root in _safe_upload_roots(db):
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
