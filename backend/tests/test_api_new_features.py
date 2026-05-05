import io
import os
import sys
from collections.abc import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import models
from database.db_config import Base, get_db
from middleware.auth_middleware import get_current_user, require_admin, require_manager
from routers import admin, chat, documents
from services import chat_service, document_service


def _build_test_app(db_session: Session, current_user: dict) -> FastAPI:
    app = FastAPI()
    app.include_router(admin.router)
    app.include_router(documents.router)
    app.include_router(chat.router)

    def _get_db_override() -> Generator[Session, None, None]:
        yield db_session

    def _current_user_override() -> dict:
        return current_user

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _current_user_override
    app.dependency_overrides[require_admin] = _current_user_override
    app.dependency_overrides[require_manager] = _current_user_override
    return app


def _seed(db: Session) -> None:
    dept = models.Department(id=1, name="IT")
    admin_user = models.User(
        id=1,
        username="admin",
        hashed_password="x",
        full_name="Admin",
        role=models.RoleEnum.admin,
        department_id=1,
    )
    manager_user = models.User(
        id=2,
        username="manager",
        hashed_password="x",
        full_name="Manager",
        role=models.RoleEnum.manager,
        department_id=1,
    )
    employee_user = models.User(
        id=3,
        username="employee",
        hashed_password="x",
        full_name="Employee",
        role=models.RoleEnum.employee,
        department_id=1,
    )
    personal_doc = models.Document(
        id=10,
        filename="personal.pdf",
        file_path="uploads/personal/personal.pdf",
        scope=models.ScopeEnum.personal,
        owner_id=3,
        version_number=1,
    )
    session = models.ChatSession(id=20, user_id=3, title="s1")
    message = models.ChatMessage(
        id=30,
        session_id=20,
        sender="ai",
        content="answer",
        sources='["10","11"]',
    )
    prompt = models.SavedPrompt(id=40, user_id=3, content="saved question")
    db.add_all([dept, admin_user, manager_user, employee_user, personal_doc, session, message, prompt])
    db.commit()


def _client_and_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    _seed(db)
    current_user = {"id": 1, "role": "admin", "sub": "admin"}
    app = _build_test_app(db, current_user)
    client = TestClient(app)
    return client, db, current_user


def test_admin_role_groups_and_assign_user():
    client, db, _ = _client_and_db()

    created = client.post("/admin/role-groups", json={"name": "ops", "description": "Ops team"})
    assert created.status_code == 200
    role_group_id = created.json()["id"]

    listed = client.get("/admin/role-groups")
    assert listed.status_code == 200
    assert any(item["name"] == "ops" for item in listed.json())

    assigned = client.put(f"/admin/users/3/role-group", json={"role_group_id": role_group_id})
    assert assigned.status_code == 200
    db.refresh(db.query(models.User).filter(models.User.id == 3).first())
    assert db.query(models.User).filter(models.User.id == 3).first().role_group_id == role_group_id


def test_admin_config_crud():
    client, _, _ = _client_and_db()

    created = client.post("/admin/configs", json={"key": "security_level", "value": "internal", "type": "metadata"})
    assert created.status_code == 200
    config_id = created.json()["id"]

    listed = client.get("/admin/configs")
    assert listed.status_code == 200
    assert any(item["key"] == "security_level" for item in listed.json())

    updated = client.put(f"/admin/configs/{config_id}", json={"value": "restricted"})
    assert updated.status_code == 200

    deleted = client.delete(f"/admin/configs/{config_id}")
    assert deleted.status_code == 200


def test_document_trash_restore_and_version_flow(tmp_path):
    client, db, current_user = _client_and_db()
    current_user.update({"id": 3, "role": "employee", "sub": "employee"})

    document_service.UPLOAD_DIR_PERSONAL = str(tmp_path / "personal")
    document_service.UPLOAD_DIR_DEPARTMENT = str(tmp_path / "department")

    detail = client.get("/documents/10")
    assert detail.status_code == 200
    assert detail.json()["version_number"] == 1

    version_upload = client.post(
        "/documents/10/versions",
        files={"file": ("new.pdf", io.BytesIO(b"pdf"), "application/pdf")},
    )
    assert version_upload.status_code == 200
    assert version_upload.json()["version_number"] == 2

    versions = client.get("/documents/10/versions")
    assert versions.status_code == 200
    assert len(versions.json()) >= 2

    deleted = client.delete("/documents/personal/10")
    assert deleted.status_code == 200
    trash = client.get("/documents/trash")
    assert trash.status_code == 200
    assert any(item["id"] == 10 for item in trash.json())

    restored = client.post("/documents/10/restore")
    assert restored.status_code == 200
    trash_after = client.get("/documents/trash")
    assert all(item["id"] != 10 for item in trash_after.json())


def test_chat_citation_and_execute_prompt(monkeypatch):
    client, _, current_user = _client_and_db()
    current_user.update({"id": 3, "role": "employee", "sub": "employee"})

    citation = client.get("/chat/citations/30")
    assert citation.status_code == 200
    assert citation.json()["sources"] == ["10", "11"]

    def _fake_ask_ai(db: Session, user_id: int, question: str, scope: str = "personal", session_id: int | None = None):
        return {"answer": f"echo:{question}", "sources": [], "session_id": 20, "session_title": "s1", "attached_docs": 0}

    monkeypatch.setattr(chat_service, "ask_ai", _fake_ask_ai)
    executed = client.post("/chat/prompts/40/execute", json={"scope": "personal", "session_id": 20})
    assert executed.status_code == 200
    assert executed.json()["answer"] == "echo:saved question"
