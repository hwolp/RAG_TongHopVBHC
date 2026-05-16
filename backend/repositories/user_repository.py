from sqlalchemy.orm import Session

from database import models


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: int) -> models.User | None:
        return self.db.query(models.User).filter(models.User.id == user_id).first()

    def get_by_username(self, username: str) -> models.User | None:
        return self.db.query(models.User).filter(models.User.username == username).first()

