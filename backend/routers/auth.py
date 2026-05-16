from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.db_config import get_db
from schemas.auth_schema import LoginRequest, TokenResponse
from services.auth.auth_service import authenticate_user, create_access_token

router = APIRouter(prefix="/auth", tags=["Xác thực"])

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu")
    if user is False:
        raise HTTPException(status_code=403, detail="Tài khoản đã bị khóa. Liên hệ Admin.")

    role = user.role.value if hasattr(user.role, "value") else user.role
    token = create_access_token({"sub": user.username, "role": role, "id": user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role,
        "username": user.username,
    }
