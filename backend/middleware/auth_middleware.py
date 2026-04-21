from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from config import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Giải mã JWT token, trả về payload chứa id, username, role."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("id") is None:
            raise HTTPException(status_code=401, detail="Token không hợp lệ")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Phiên đăng nhập hết hạn hoặc không hợp lệ")

def require_role(*allowed_roles: str):
    """Factory tạo dependency kiểm tra quyền."""
    def checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Yêu cầu quyền: {', '.join(allowed_roles)}")
        return user
    return checker

require_admin = require_role("admin")
require_manager = require_role("admin", "manager")
require_any = get_current_user  # Bất kì user đã đăng nhập
