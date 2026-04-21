from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ChatRequest(BaseModel):
    question: str
    scope: str = "personal"
    session_id: Optional[int] = None

class ChatResponse(BaseModel):
    answer: str
    sources: Optional[List[str]] = None
    session_id: int
    session_title: str

class ChatSessionOut(BaseModel):
    id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatMessageOut(BaseModel):
    id: int
    sender: str
    content: str
    sources: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
