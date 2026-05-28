from sqlalchemy.orm import Session

from database import models
from repositories.department_repository import DepartmentRepository
from repositories.document_repository import DocumentRepository
from repositories.role_group_repository import RoleGroupRepository
from repositories.user_repository import UserRepository
from utils.errors import bad_request, not_found


class AdminDirectoryService:
    def __init__(self, db: Session):
        self.departments = DepartmentRepository(db)
        self.documents = DocumentRepository(db)
        self.role_groups = RoleGroupRepository(db)
        self.users = UserRepository(db)

    def list_departments(self):
        departments = self.departments.list()
        return [{"id": department.id, "name": department.name} for department in departments]

    def create_department(self, name: str):
        clean_name = name.strip()
        if not clean_name:
            raise bad_request("Ten phong ban khong hop le")
        if self.departments.get_by_name(clean_name):
            raise bad_request("Phong ban da ton tai")

        department = models.Department(name=clean_name)
        self.departments.add(department)
        return {"status": "success", "id": department.id, "name": department.name}

    def update_department(self, department_id: int, name: str):
        department = self._require_department(department_id)
        if department.id == 0:
            raise bad_request("Khong the doi ten phong ban he thong")

        clean_name = name.strip()
        if not clean_name:
            raise bad_request("Ten phong ban khong hop le")
        if self.departments.name_exists(clean_name, exclude_id=department_id):
            raise bad_request("Phong ban da ton tai")

        department.name = clean_name
        self.departments.commit()
        return {"status": "success", "id": department.id, "name": department.name}

    def delete_department(self, department_id: int):
        department = self._require_department(department_id)
        if department.id == 0:
            raise bad_request("Khong the xoa phong ban he thong")

        users_count = self.users.count_by_department(department_id)
        docs_count = self.documents.count_by_department(department_id)
        if users_count or docs_count:
            raise bad_request("Phong ban dang co nguoi dung hoac tai lieu, vui long chuyen du lieu truoc khi xoa")

        self.departments.delete(department)
        return {"status": "success"}

    def list_role_groups(self):
        groups = self.role_groups.list()
        return [{"id": group.id, "name": group.name, "description": group.description} for group in groups]

    def create_role_group(self, name: str, description: str | None = None):
        clean_name = name.strip()
        if not clean_name:
            raise bad_request("Ten nhom quyen khong hop le")
        group = models.RoleGroup(name=clean_name, description=(description or "").strip() or None)
        self.role_groups.add(group)
        return {"status": "success", "id": group.id, "name": group.name, "description": group.description}

    def assign_role_group(self, user_id: int, role_group_id: int | None = None):
        user = self.users.get(user_id)
        if not user:
            raise not_found("Nguoi dung khong ton tai")
        if role_group_id is not None:
            role_group = self.role_groups.get(role_group_id)
            if not role_group:
                raise not_found("Nhom quyen khong ton tai")
        user.role_group_id = role_group_id
        self.users.commit()
        return {"status": "success", "user_id": user.id, "role_group_id": user.role_group_id}

    def _require_department(self, department_id: int) -> models.Department:
        department = self.departments.get(department_id)
        if not department:
            raise not_found("Phong ban khong ton tai")
        return department
