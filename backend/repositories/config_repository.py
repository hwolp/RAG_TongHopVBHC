from __future__ import annotations

from sqlalchemy.orm import Session

from database import models


class ConfigRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, config_id: int) -> models.ConfigItem | None:
        return self.db.query(models.ConfigItem).filter(models.ConfigItem.id == config_id).first()

    def get_by_key(self, key: str) -> models.ConfigItem | None:
        return self.db.query(models.ConfigItem).filter(models.ConfigItem.key == key).first()

    def key_exists(self, key: str, exclude_id: int | None = None) -> bool:
        query = self.db.query(models.ConfigItem).filter(models.ConfigItem.key == key)
        if exclude_id is not None:
            query = query.filter(models.ConfigItem.id != exclude_id)
        return query.first() is not None

    def list(self, item_type: str | None = None) -> list[models.ConfigItem]:
        query = self.db.query(models.ConfigItem)
        if item_type:
            query = query.filter(models.ConfigItem.type == item_type)
        return query.order_by(models.ConfigItem.id.asc()).all()

    def add(self, item: models.ConfigItem) -> models.ConfigItem:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def commit(self) -> None:
        self.db.commit()

    def delete(self, item: models.ConfigItem) -> None:
        self.db.delete(item)
        self.db.commit()
