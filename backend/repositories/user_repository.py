from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import models


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: int) -> models.User | None:
        return self.db.query(models.User).filter(models.User.id == user_id).first()

    def get_by_username(self, username: str) -> models.User | None:
        return self.db.query(models.User).filter(models.User.username == username).first()

    def list(self, search: str = "") -> list[models.User]:
        query = self.db.query(models.User)
        if search:
            query = query.filter(
                or_(
                    models.User.username.contains(search),
                    models.User.full_name.contains(search),
                )
            )
        return query.all()

    def count_by_department(self, department_id: int) -> int:
        return self.db.query(models.User).filter(models.User.department_id == department_id).count()

    def add(self, user: models.User) -> models.User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, user: models.User) -> None:
        self.db.refresh(user)

    def delete(self, user: models.User) -> None:
        self.db.delete(user)
        self.db.commit()
