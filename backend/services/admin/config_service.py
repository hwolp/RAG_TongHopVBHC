from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import models
from repositories.config_repository import ConfigRepository


def list_configs(db: Session, item_type: str | None = None):
    rows = ConfigRepository(db).list(item_type)
    return [
        {
            "id": row.id,
            "key": row.key,
            "value": row.value,
            "type": row.type,
            "created_at": str(row.created_at),
        }
        for row in rows
    ]


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
