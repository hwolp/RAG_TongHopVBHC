from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DocumentOut(BaseModel):
    id: int
    filename: str
    scope: str
    is_indexed: bool
    uploaded_at: datetime
    owner_id: Optional[int] = None
    department_id: Optional[int] = None

    class Config:
        from_attributes = True

class SQPProposalOut(BaseModel):
    id: int
    document_id: int
    proposed_by: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
