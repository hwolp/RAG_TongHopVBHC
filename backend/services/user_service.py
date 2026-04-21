from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import models
from services.auth_service import get_password_hash


def _role_to_str(role_value) -> str:
    return role_value.value if hasattr(role_value, "value") else str(role_value)


def list_users(db: Session, search: str = ""):
    query = db.query(models.User)
    if search:
        query = query.filter(
            or_(
                models.User.username.contains(search),
                models.User.full_name.contains(search),
            )
        )
    users = query.all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": _role_to_str(user.role),
            "is_locked": user.is_locked,
            "department_id": user.department_id,
        }
        for user in users
    ]


def create_user(
    db: Session,
    username: str,
    full_name: str,
    role: str,
    department_id: Optional[int],
    password: str,
):
    if db.query(models.User).filter(models.User.username == username).first():
        return None

    role_enum = models.RoleEnum(role)
    user = models.User(
        username=username,
        full_name=full_name,
        role=role_enum,
        department_id=department_id,
        hashed_password=get_password_hash(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, full_name: Optional[str], role: Optional[str], department_id: Optional[int]):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None

    if full_name is not None:
        user.full_name = full_name
    if role is not None:
        user.role = models.RoleEnum(role)
    if department_id is not None:
        user.department_id = department_id

    db.commit()
    db.refresh(user)
    return user


def toggle_lock_user(db: Session, user_id: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None

    user.is_locked = not user.is_locked
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return False

    db.delete(user)
    db.commit()
    return True
