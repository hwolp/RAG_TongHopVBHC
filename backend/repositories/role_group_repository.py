from __future__ import annotations

from sqlalchemy.orm import Session

from database import models


class RoleGroupRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, role_group_id: int) -> models.RoleGroup | None:
        return self.db.query(models.RoleGroup).filter(models.RoleGroup.id == role_group_id).first()

    def list(self) -> list[models.RoleGroup]:
        return self.db.query(models.RoleGroup).order_by(models.RoleGroup.name.asc()).all()

    def add(self, group: models.RoleGroup) -> models.RoleGroup:
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return group
