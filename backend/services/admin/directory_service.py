from sqlalchemy.orm import Session

from database import models
from utils.errors import bad_request, not_found


class AdminDirectoryService:
    def __init__(self, db: Session):
        self.db = db

    def list_departments(self):
        departments = self.db.query(models.Department).order_by(models.Department.name.asc()).all()
        return [{"id": department.id, "name": department.name} for department in departments]

    def create_department(self, name: str):
        clean_name = name.strip()
        if not clean_name:
            raise bad_request("Ten phong ban khong hop le")
        if self.db.query(models.Department).filter(models.Department.name == clean_name).first():
            raise bad_request("Phong ban da ton tai")

        department = models.Department(name=clean_name)
        self.db.add(department)
        self.db.commit()
        self.db.refresh(department)
        return {"status": "success", "id": department.id, "name": department.name}

    def update_department(self, department_id: int, name: str):
        department = self._require_department(department_id)
        if department.id == 0:
            raise bad_request("Khong the doi ten phong ban he thong")

        clean_name = name.strip()
        if not clean_name:
            raise bad_request("Ten phong ban khong hop le")
        existed = self.db.query(models.Department).filter(
            models.Department.name == clean_name,
            models.Department.id != department_id,
        ).first()
        if existed:
            raise bad_request("Phong ban da ton tai")

        department.name = clean_name
        self.db.commit()
        return {"status": "success", "id": department.id, "name": department.name}

    def delete_department(self, department_id: int):
        department = self._require_department(department_id)
        if department.id == 0:
            raise bad_request("Khong the xoa phong ban he thong")

        users_count = self.db.query(models.User).filter(models.User.department_id == department_id).count()
        docs_count = self.db.query(models.Document).filter(models.Document.department_id == department_id).count()
        if users_count or docs_count:
            raise bad_request("Phong ban dang co nguoi dung hoac tai lieu, vui long chuyen du lieu truoc khi xoa")

        self.db.delete(department)
        self.db.commit()
        return {"status": "success"}

    def list_role_groups(self):
        groups = self.db.query(models.RoleGroup).order_by(models.RoleGroup.name.asc()).all()
        return [{"id": group.id, "name": group.name, "description": group.description} for group in groups]

    def create_role_group(self, name: str, description: str | None = None):
        clean_name = name.strip()
        if not clean_name:
            raise bad_request("Ten nhom quyen khong hop le")
        group = models.RoleGroup(name=clean_name, description=(description or "").strip() or None)
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return {"status": "success", "id": group.id, "name": group.name, "description": group.description}

    def assign_role_group(self, user_id: int, role_group_id: int | None = None):
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise not_found("Nguoi dung khong ton tai")
        if role_group_id is not None:
            role_group = self.db.query(models.RoleGroup).filter(models.RoleGroup.id == role_group_id).first()
            if not role_group:
                raise not_found("Nhom quyen khong ton tai")
        user.role_group_id = role_group_id
        self.db.commit()
        return {"status": "success", "user_id": user.id, "role_group_id": user.role_group_id}

    def _require_department(self, department_id: int) -> models.Department:
        department = self.db.query(models.Department).filter(models.Department.id == department_id).first()
        if not department:
            raise not_found("Phong ban khong ton tai")
        return department

