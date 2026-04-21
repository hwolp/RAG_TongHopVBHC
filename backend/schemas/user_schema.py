from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    username: str
    full_name: str = ""
    role: str = "employee"
    department_id: Optional[int] = None
    password: str = "123456"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[int] = None

class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role: str
    is_locked: bool
    department_id: Optional[int]

    class Config:
        from_attributes = True
