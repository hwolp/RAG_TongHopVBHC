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
from middleware.auth_middleware import get_current_user, require_admin
from routers import admin


def _build_test_app(db_session: Session, current_user: dict) -> FastAPI:
    app = FastAPI()
    app.include_router(admin.router)

    def _get_db_override() -> Generator[Session, None, None]:
        yield db_session

    def _current_user_override() -> dict:
        return current_user

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _current_user_override
    app.dependency_overrides[require_admin] = _current_user_override
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
    target_user = models.User(
        id=2,
        username="employee_b",
        hashed_password="x",
        full_name="Employee B",
        role=models.RoleEnum.employee,
        department_id=2,
    )
    department_doc = models.Document(
        id=10,
        filename="ke_hoach.pdf",
        file_path="uploads/department/ke_hoach.pdf",
        scope=models.ScopeEnum.department,
        owner_id=1,
        department_id=1,
    )
    db.add_all([dept_a, dept_b, admin_user, target_user, department_doc])
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


def test_admin_can_share_and_revoke_department_document():
    client, db = _client_and_db()

    share_response = client.post("/admin/documents/10/share/department/2")
    assert share_response.status_code == 200
    assert share_response.json()["status"] == "success"

    shares_response = client.get("/admin/shares")
    assert shares_response.status_code == 200
    shares = shares_response.json()
    assert len(shares) == 1
    assert shares[0]["document_filename"] == "ke_hoach.pdf"
    assert shares[0]["shared_with_department_name"] == "Phong B"

    revoke_response = client.delete(f"/admin/shares/{shares[0]['id']}")
    assert revoke_response.status_code == 200
    assert revoke_response.json()["status"] == "success"

    shares_after = client.get("/admin/shares")
    assert shares_after.status_code == 200
    assert shares_after.json() == []

    db.close()
