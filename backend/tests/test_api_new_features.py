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
from services import document_service, job_worker, maintenance_service


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
    admin_dept = models.Department(id=0, name="Admin")
    dept = models.Department(id=1, name="IT")
    dept_b = models.Department(id=2, name="Kế Toán")
    admin_user = models.User(
        id=1,
        username="admin",
        hashed_password="x",
        full_name="Admin",
        role=models.RoleEnum.admin,
        department_id=0,
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
    )
    department_doc_a = models.Document(
        id=11,
        filename="dept-a.pdf",
        file_path="uploads/department/dept-a.pdf",
        scope=models.ScopeEnum.department,
        owner_id=2,
        department_id=1,
    )
    department_doc_b = models.Document(
        id=12,
        filename="dept-b.pdf",
        file_path="uploads/department/dept-b.pdf",
        scope=models.ScopeEnum.department,
        owner_id=2,
        department_id=2,
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
    db.add_all([admin_dept, dept, dept_b, admin_user, manager_user, employee_user, personal_doc, department_doc_a, department_doc_b, session, message, prompt])
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


def test_admin_clear_collection_removes_rag_data(tmp_path, monkeypatch):
    client, db, current_user = _client_and_db()
    current_user.update({"id": 1, "role": "admin", "sub": "admin"})

    personal_root = tmp_path / "uploads" / "personal"
    department_root = tmp_path / "uploads" / "department"
    sqp_root = tmp_path / "uploads" / "sqp"
    personal_root.mkdir(parents=True)
    department_root.mkdir(parents=True)
    sqp_root.mkdir(parents=True)
    uploaded_file = personal_root / "personal.pdf"
    uploaded_file.write_bytes(b"pdf")

    doc = db.query(models.Document).filter(models.Document.id == 10).first()
    doc.file_path = str(uploaded_file)
    doc.is_indexed = True
    db.add(models.DocumentVersion(document_id=10, filename="personal-v1.pdf", file_path=str(uploaded_file)))
    db.add(models.SessionDocAttachment(session_id=20, doc_id=10))
    db.add(models.BackgroundJob(type="chat_answer", status="success", created_by=3, document_id=10, session_id=20, message_id=30))
    db.commit()

    class DummyChromaDBManager:
        def admin_clear_db(self):
            return "Cleaned"

    import rag_engine.chroma_manager as chroma_manager_module

    monkeypatch.setattr(chroma_manager_module, "ChromaDBManager", DummyChromaDBManager)
    monkeypatch.setattr(maintenance_service, "UPLOAD_DIR_PERSONAL", str(personal_root))
    monkeypatch.setattr(maintenance_service, "UPLOAD_DIR_DEPARTMENT", str(department_root))
    monkeypatch.setattr(maintenance_service, "UPLOAD_DIR_SQP", str(sqp_root))

    response = client.post("/admin/vector/clear")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["deleted"]["documents"] >= 3
    assert payload["deleted"]["chat_sessions"] >= 1
    assert payload["deleted"]["chat_messages"] >= 1
    assert db.query(models.Document).count() == 0
    assert db.query(models.ChatSession).count() == 0
    assert db.query(models.ChatMessage).count() == 0
    assert db.query(models.BackgroundJob).count() == 0
    assert not uploaded_file.exists()


def test_admin_can_list_all_department_documents():
    client, db, _ = _client_and_db()

    response = client.get("/admin/documents/department")
    assert response.status_code == 200
    document_ids = {item["id"] for item in response.json()}
    assert {11, 12}.issubset(document_ids)

    tree_response = client.get("/documents/tree")
    assert tree_response.status_code == 200
    tree = tree_response.json()
    assert "IT" in tree["department"]
    assert "Kế Toán" in tree["department"]

    db.close()


def test_admin_approve_sqp_requeues_index_with_sqp_scope(monkeypatch):
    client, db, current_user = _client_and_db()
    current_user.update({"id": 1, "role": "admin", "sub": "admin"})

    doc = db.query(models.Document).filter(models.Document.id == 11).first()
    doc.is_indexed = True
    proposal = models.SQPProposal(
        document_id=11,
        proposed_by=2,
        status=models.ProposalStatus.pending,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    deleted_doc_ids = []

    class DummyChromaDBManager:
        def delete_doc_from_index(self, doc_id: int):
            deleted_doc_ids.append(doc_id)
            return 3

    import rag_engine.chroma_manager as chroma_manager_module

    monkeypatch.setattr(chroma_manager_module, "ChromaDBManager", DummyChromaDBManager)

    response = client.post(f"/admin/sqp/approve/{proposal.id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] is not None

    db.refresh(doc)
    assert doc.scope == models.ScopeEnum.sqp
    assert doc.is_indexed is False
    assert deleted_doc_ids == [11]
    job = db.query(models.BackgroundJob).filter(models.BackgroundJob.id == payload["job_id"]).first()
    assert job is not None
    assert job.type == "index_document"


def test_admin_library_tree_shows_all_departments_even_when_assigned_to_one_dept():
    client, db, current_user = _client_and_db()

    admin_user = db.query(models.User).filter(models.User.id == 1).first()
    admin_user.department_id = 1
    db.commit()

    current_user.update({"id": 1, "role": "admin", "sub": "admin"})

    tree_response = client.get("/documents/tree")
    assert tree_response.status_code == 200
    tree = tree_response.json()
    assert "IT" in tree["department"]
    assert "Kế Toán" in tree["department"]

    db.close()


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


def test_personal_upload_uses_user_scoped_unique_paths(tmp_path, monkeypatch):
    client, db, current_user = _client_and_db()
    monkeypatch.setattr(document_service, "UPLOAD_DIR_PERSONAL", str(tmp_path / "personal"))

    current_user.update({"id": 3, "role": "employee", "sub": "employee"})
    first_upload = client.post(
        "/documents/personal",
        files={"file": ("same.txt", io.BytesIO(b"employee file"), "text/plain")},
    )
    assert first_upload.status_code == 200
    first_doc_id = first_upload.json()["doc_id"]

    current_user.update({"id": 2, "role": "manager", "sub": "manager"})
    second_upload = client.post(
        "/documents/personal",
        files={"file": ("same.txt", io.BytesIO(b"manager file"), "text/plain")},
    )
    assert second_upload.status_code == 200
    second_doc_id = second_upload.json()["doc_id"]

    first_doc = db.query(models.Document).filter(models.Document.id == first_doc_id).first()
    second_doc = db.query(models.Document).filter(models.Document.id == second_doc_id).first()
    assert first_doc.filename == "same.txt"
    assert second_doc.filename == "same.txt"
    assert first_doc.file_path != second_doc.file_path
    assert os.path.basename(os.path.dirname(first_doc.file_path)) == "user_3"
    assert os.path.basename(os.path.dirname(second_doc.file_path)) == "user_2"
    assert open(first_doc.file_path, "rb").read() == b"employee file"
    assert open(second_doc.file_path, "rb").read() == b"manager file"

    current_user.update({"id": 3, "role": "employee", "sub": "employee"})
    listed = client.get("/documents/personal")
    assert listed.status_code == 200
    listed_ids = {item["id"] for item in listed.json()}
    assert first_doc_id in listed_ids
    assert second_doc_id not in listed_ids


def test_chat_citation_and_execute_prompt(monkeypatch):
    client, _, current_user = _client_and_db()
    current_user.update({"id": 3, "role": "employee", "sub": "employee"})

    citation = client.get("/chat/citations/30")
    assert citation.status_code == 200
    assert citation.json()["sources"] == ["10", "11"]

    executed = client.post("/chat/prompts/40/execute", json={"scope": "personal", "session_id": 20})
    assert executed.status_code == 200
    payload = executed.json()
    assert payload["status"] == "queued"
    assert payload["job_id"] is not None
    assert payload["session_id"] == 20
    assert payload["ai_message_id"] is not None


def test_chat_answer_worker_updates_placeholder(monkeypatch):
    client, db, current_user = _client_and_db()
    current_user.update({"id": 3, "role": "employee", "sub": "employee"})

    class DummyChromaDBManager:
        def search_context_with_filter(self, *args, **kwargs):
            return "context", ["10"]

    class DummyOllamaAI:
        def generate_answer(self, question: str, context: str, chat_history: str):
            return f"echo:{question}:{context}"

    import rag_engine.chroma_manager as chroma_manager_module
    import rag_engine.ollama_ai as ollama_ai_module

    monkeypatch.setattr(chroma_manager_module, "ChromaDBManager", DummyChromaDBManager)
    monkeypatch.setattr(ollama_ai_module, "OllamaAI", DummyOllamaAI)

    executed = client.post("/chat/prompts/40/execute", json={"scope": "personal", "session_id": 20})
    job_id = executed.json()["job_id"]
    ai_message_id = executed.json()["ai_message_id"]

    job_worker.run_job(job_id, db)

    ai_message = db.query(models.ChatMessage).filter(models.ChatMessage.id == ai_message_id).first()
    assert ai_message.content == "echo:saved question:context"
    assert ai_message.sources == '["10"]'


def test_chat_answer_waits_for_unindexed_attachment():
    client, db, current_user = _client_and_db()
    current_user.update({"id": 3, "role": "employee", "sub": "employee"})

    attached = client.post("/chat/sessions/20/attach", json={"doc_id": 10})
    assert attached.status_code == 200
    assert attached.json()["index_status"] == "queued"

    listed = client.get("/chat/sessions/20/attachments")
    assert listed.status_code == 200
    assert listed.json()[0]["index_status"] == "queued"

    executed = client.post("/chat/prompts/40/execute", json={"scope": "personal", "session_id": 20})
    job_id = executed.json()["job_id"]
    ai_message_id = executed.json()["ai_message_id"]

    job_worker.run_job(job_id, db)

    ai_message = db.query(models.ChatMessage).filter(models.ChatMessage.id == ai_message_id).first()
    assert "chưa index xong" in ai_message.content
    assert ai_message.sources == "[]"
