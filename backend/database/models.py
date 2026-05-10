from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from database.db_config import Base
import datetime
import enum


# ========== ENUMS ==========
class RoleEnum(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    employee = "employee"

class ScopeEnum(str, enum.Enum):
    personal = "personal"
    department = "department"
    sqp = "sqp"

class ProposalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


# ========== CORE TABLES ==========
class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True)
    users = relationship("User", back_populates="department")
    documents = relationship("Document", back_populates="department")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(100), nullable=True)
    role = Column(Enum(RoleEnum), default=RoleEnum.employee)
    is_locked = Column(Boolean, default=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    role_group_id = Column(Integer, ForeignKey("role_groups.id"), nullable=True)

    department = relationship("Department", back_populates="users")
    documents = relationship("Document", back_populates="owner")
    chat_sessions = relationship("ChatSession", back_populates="user")
    proposals = relationship("SQPProposal", back_populates="proposer")
    saved_prompts = relationship("SavedPrompt", back_populates="user")
    role_group = relationship("RoleGroup", back_populates="users")


class RoleGroup(Base):
    __tablename__ = "role_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    users = relationship("User", back_populates="role_group")


# ========== DOCUMENT TABLES ==========
class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True)

class DocumentTag(Base):
    __tablename__ = "document_tags"
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), index=True)
    file_path = Column(String(500))
    scope = Column(Enum(ScopeEnum), default=ScopeEnum.personal)
    summary = Column(Text, nullable=True)
    is_indexed = Column(Boolean, default=False)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="documents")
    department = relationship("Department", back_populates="documents")
    chat_session = relationship("ChatSession", back_populates="documents")
    proposals = relationship("SQPProposal", back_populates="document")
    shared_records = relationship("SharedDocument", back_populates="document")


# ========== SQP PROPOSAL ==========
class SQPProposal(Base):
    __tablename__ = "sqp_proposals"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    proposed_by = Column(Integer, ForeignKey("users.id"))
    status = Column(Enum(ProposalStatus), default=ProposalStatus.pending)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="proposals")
    proposer = relationship("User", back_populates="proposals")


# ========== CHAT TABLES ==========
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(255), default="Phiên hội thoại mới")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="chat_session")
    doc_attachments = relationship("SessionDocAttachment", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    sender = Column(String(50))  # "user" or "ai"
    content = Column(Text)
    sources = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


class SessionDocAttachment(Base):
    """Liên kết tài liệu đã có trong thư viện với một session chat (không re-upload)."""
    __tablename__ = "session_doc_attachments"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    doc_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    attached_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("ChatSession", back_populates="doc_attachments")


# ========== SAVED PROMPTS ==========
class SavedPrompt(Base):
    __tablename__ = "saved_prompts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="saved_prompts")


# ========== SHARING & CONTRIBUTOR ==========
class SharedDocument(Base):
    __tablename__ = "shared_documents"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    shared_with_dept_id = Column(Integer, ForeignKey("departments.id"))
    shared_with_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    shared_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="shared_records")

class Contributor(Base):
    __tablename__ = "contributors"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    granted_by = Column(Integer, ForeignKey("users.id"))
    department_id = Column(Integer, ForeignKey("departments.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
