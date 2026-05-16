import os
import shutil
from uuid import uuid4

from fastapi import UploadFile

from utils.errors import bad_request


def safe_filename(filename: str) -> str:
    candidate = (filename or "").strip()
    if not candidate:
        raise bad_request("Ten file khong hop le")

    base_name = os.path.basename(candidate)
    if base_name != candidate or base_name in {".", ".."} or ".." in base_name:
        raise bad_request("Ten file khong hop le")
    return base_name


def stored_filename(original_filename: str) -> str:
    stem, extension = os.path.splitext(original_filename)
    return f"{stem}_{uuid4().hex}{extension}"


def save_upload_file(file: UploadFile, target_dir: str, stored_name: str | None = None) -> tuple[str, str]:
    clean_filename = safe_filename(file.filename)
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, stored_name or clean_filename)

    with open(file_path, "wb+") as handle:
        shutil.copyfileobj(file.file, handle)

    return clean_filename, file_path


def replace_file_path(current_path: str, new_filename: str) -> tuple[str, str]:
    clean_filename = safe_filename(new_filename)
    new_path = os.path.join(os.path.dirname(current_path), clean_filename)
    if os.path.exists(current_path) and current_path != new_path:
        os.replace(current_path, new_path)
    return clean_filename, new_path


def delete_file_if_exists(file_path: str) -> None:
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

