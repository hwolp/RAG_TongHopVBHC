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
from middleware.auth_middleware import get_current_user, require_admin, require_manager, require_manager_only
from routers import documents, manager
from services import document_service, job_worker


def _build_test_app(db_session: Session, current_user: dict) -> FastAPI:
    app = FastAPI()
    app.include_router(documents.router)
    app.include_router(manager.router)

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
    dept_a = models.Department(id=1, name="Phong A")
    dept_b = models.Department(id=2, name="Phong B")
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
    db.add_all([dept_a, dept_b, admin_user, manager_user])
    db.commit()


def _client_and_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = testing_session_local()
    _seed(db)
    current_user = {"id": 1, "role": "admin", "sub": "admin"}
    app = _build_test_app(db, current_user)
    client = TestClient(app)
    return client, db


def test_admin_can_crud_sqp_documents(tmp_path, monkeypatch):
    client, db = _client_and_db()
    document_service.UPLOAD_DIR_SQP = str(tmp_path / "sqp")

    class DummyChromaDBManager:
        def process_and_store_pdf(self, *args, **kwargs):
            return 7

    import rag_engine.chroma_manager as chroma_manager_module

    monkeypatch.setattr(chroma_manager_module, "ChromaDBManager", DummyChromaDBManager)

    upload_response = client.post(
        "/documents/sqp",
        files={"file": ("sqp-policy.pdf", io.BytesIO(b"pdf"), "application/pdf")},
    )
    assert upload_response.status_code == 200
    doc_id = upload_response.json()["doc_id"]

    upload_payload = upload_response.json()
    assert upload_payload["status"] == "queued"
    assert upload_payload["job_id"] is not None

    stored_doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    assert stored_doc is not None
    assert stored_doc.is_indexed is False

    job_worker.run_job(upload_payload["job_id"], db)
    db.refresh(stored_doc)
    assert stored_doc.is_indexed is True

    listed = client.get("/documents/sqp")
    assert listed.status_code == 200
    assert any(item["id"] == doc_id for item in listed.json())
    assert any(item["id"] == doc_id and item["is_indexed"] is True for item in listed.json())

    updated = client.put(f"/documents/sqp/{doc_id}", json={"filename": "sqp-policy-updated.pdf"})
    assert updated.status_code == 200
    assert updated.json()["filename"] == "sqp-policy-updated.pdf"

    deleted = client.delete(f"/documents/sqp/{doc_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "success"

    listed_after = client.get("/documents/sqp")
    assert listed_after.status_code == 200
    assert all(item["id"] != doc_id for item in listed_after.json())

    db.close()


def test_admin_cannot_use_manager_share_route():
    client, db = _client_and_db()

    denied = client.post("/manager/share/document/1/to-dept/2")
    assert denied.status_code == 403

    db.close()
