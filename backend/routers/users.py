from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.db_config import get_db
from middleware.auth_middleware import require_admin
from schemas.user_schema import UserCreate, UserUpdate
from services import user_service

router = APIRouter(prefix="/admin/users", tags=["Quản lý người dùng"])


@router.get("")
def list_users(search: str = "", db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return user_service.list_users(db, search)


@router.post("")
def create_user(payload: UserCreate, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    try:
        user = user_service.create_user(
            db=db,
            username=payload.username,
            full_name=payload.full_name,
            role=payload.role,
            department_id=payload.department_id,
            password=payload.password,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Role không hợp lệ")

    if user is None:
        raise HTTPException(status_code=400, detail="Username đã tồn tại")

    return {"status": "success", "id": user.id}


@router.put("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    try:
        user = user_service.update_user(
            db=db,
            user_id=user_id,
            full_name=payload.full_name,
            role=payload.role,
            department_id=payload.department_id,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Role không hợp lệ")

    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    return {"status": "success"}


@router.post("/{user_id}/lock")
def toggle_lock_user(user_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    user = user_service.toggle_lock_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    return {"status": "success", "is_locked": user.is_locked}


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    ok = user_service.delete_user(db, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    return {"status": "success"}
