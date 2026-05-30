from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import models
from repositories.config_repository import ConfigRepository
from config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    RAG_CHUNK_SIZE,
    RAG_TOP_K,
    UPLOAD_DIR_DEPARTMENT,
    UPLOAD_DIR_PERSONAL,
    UPLOAD_DIR_SQP,
)


SYSTEM_CONFIG_DEFINITIONS = [
    {
        "key": "ollama.base_url",
        "value": OLLAMA_BASE_URL,
        "type": "system",
        "label": "Ollama URL",
        "description": "Dia chi server Ollama, vi du http://localhost:11434",
        "input_type": "text",
    },
    {
        "key": "ollama.model",
        "value": OLLAMA_MODEL,
        "type": "system",
        "label": "Ten model",
        "description": "Model LLM dung de sinh cau tra loi RAG",
        "input_type": "text",
    },
    {
        "key": "rag.top_k",
        "value": str(RAG_TOP_K),
        "type": "system",
        "label": "Top K",
        "description": "So luong chunk uu tien lay tu vector DB moi cau hoi",
        "input_type": "number",
    },
    {
        "key": "rag.chunk_size",
        "value": str(RAG_CHUNK_SIZE),
        "type": "system",
        "label": "Chunk size",
        "description": "Kich thuoc moi chunk khi index tai lieu moi hoac re-index",
        "input_type": "number",
    },
    {
        "key": "upload.personal_dir",
        "value": UPLOAD_DIR_PERSONAL,
        "type": "system",
        "label": "Thu muc upload ca nhan",
        "description": "Thu muc goc luu tai lieu ca nhan va tai lieu trong phien chat",
        "input_type": "text",
    },
    {
        "key": "upload.department_dir",
        "value": UPLOAD_DIR_DEPARTMENT,
        "type": "system",
        "label": "Thu muc upload phong ban",
        "description": "Thu muc goc luu tai lieu phong ban",
        "input_type": "text",
    },
    {
        "key": "upload.sqp_dir",
        "value": UPLOAD_DIR_SQP,
        "type": "system",
        "label": "Thu muc upload SQP",
        "description": "Thu muc goc luu tai lieu quy dinh/SQP",
        "input_type": "text",
    },
]

SYSTEM_CONFIG_DEFAULTS = {item["key"]: item for item in SYSTEM_CONFIG_DEFINITIONS}


def _serialize(row: models.ConfigItem, definition: dict | None = None):
    return {
        "id": row.id,
        "key": row.key,
        "value": row.value,
        "type": row.type,
        "created_at": str(row.created_at),
        "label": (definition or {}).get("label", row.key),
        "description": (definition or {}).get("description", ""),
        "input_type": (definition or {}).get("input_type", "text"),
    }


def _ensure_system_configs(db: Session) -> None:
    configs = ConfigRepository(db)
    changed = False
    for definition in SYSTEM_CONFIG_DEFINITIONS:
        item = configs.get_by_key(definition["key"])
        if item:
            continue
        db.add(
            models.ConfigItem(
                key=definition["key"],
                value=str(definition["value"]),
                type=definition["type"],
            )
        )
        changed = True
    if changed:
        db.commit()


def reset_system_configs(db: Session):
    _ensure_system_configs(db)
    configs = ConfigRepository(db)
    reset_count = 0
    for definition in SYSTEM_CONFIG_DEFINITIONS:
        item = configs.get_by_key(definition["key"])
        if not item:
            continue
        item.value = str(definition["value"])
        item.type = definition["type"]
        reset_count += 1
    configs.commit()
    return {"status": "success", "reset_count": reset_count}


def list_configs(db: Session, item_type: str | None = None):
    if item_type in (None, "system"):
        _ensure_system_configs(db)
    rows = ConfigRepository(db).list(item_type)
    return [_serialize(row, SYSTEM_CONFIG_DEFAULTS.get(row.key)) for row in rows]


def get_config_value(db: Session, key: str, default: str) -> str:
    item = ConfigRepository(db).get_by_key(key)
    if not item or item.value is None:
        return default
    return str(item.value)


def get_int_config_value(db: Session, key: str, default: int, min_value: int = 1, max_value: int | None = None) -> int:
    raw_value = get_config_value(db, key, str(default))
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    if value < min_value:
        return default
    if max_value is not None and value > max_value:
        return max_value
    return value


def get_ollama_settings(db: Session) -> dict:
    return {
        "base_url": get_config_value(db, "ollama.base_url", OLLAMA_BASE_URL).strip(),
        "model": get_config_value(db, "ollama.model", OLLAMA_MODEL).strip(),
    }


def get_rag_settings(db: Session) -> dict:
    return {
        "top_k": get_int_config_value(db, "rag.top_k", RAG_TOP_K, min_value=1, max_value=50),
        "chunk_size": get_int_config_value(db, "rag.chunk_size", RAG_CHUNK_SIZE, min_value=300, max_value=8000),
    }


def get_upload_dirs(db: Session) -> dict:
    return {
        "personal": get_config_value(db, "upload.personal_dir", UPLOAD_DIR_PERSONAL).strip(),
        "department": get_config_value(db, "upload.department_dir", UPLOAD_DIR_DEPARTMENT).strip(),
        "sqp": get_config_value(db, "upload.sqp_dir", UPLOAD_DIR_SQP).strip(),
    }


def create_config(db: Session, key: str, value: str, item_type: str):
    clean_key = (key or "").strip()
    clean_value = (value or "").strip()
    clean_type = (item_type or "metadata").strip()
    if not clean_key or not clean_value:
        raise HTTPException(status_code=400, detail="key va value khong duoc de trong")
    configs = ConfigRepository(db)
    if configs.get_by_key(clean_key):
        raise HTTPException(status_code=400, detail="key da ton tai")
    item = models.ConfigItem(key=clean_key, value=clean_value, type=clean_type)
    configs.add(item)
    return {"status": "success", "id": item.id}


def update_config(db: Session, config_id: int, key: str | None, value: str | None, item_type: str | None):
    configs = ConfigRepository(db)
    item = configs.get(config_id)
    if not item:
        raise HTTPException(status_code=404, detail="Config khong ton tai")

    if key is not None:
        clean_key = key.strip()
        if not clean_key:
            raise HTTPException(status_code=400, detail="key khong hop le")
        if configs.key_exists(clean_key, exclude_id=config_id):
            raise HTTPException(status_code=400, detail="key da ton tai")
        item.key = clean_key
    if value is not None:
        clean_value = value.strip()
        if not clean_value:
            raise HTTPException(status_code=400, detail="value khong hop le")
        item.value = clean_value
    if item_type is not None:
        clean_type = item_type.strip()
        if not clean_type:
            raise HTTPException(status_code=400, detail="type khong hop le")
        item.type = clean_type

    configs.commit()
    return {"status": "success"}


def delete_config(db: Session, config_id: int):
    configs = ConfigRepository(db)
    item = configs.get(config_id)
    if not item:
        raise HTTPException(status_code=404, detail="Config khong ton tai")
    configs.delete(item)
    return {"status": "success"}
