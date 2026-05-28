from __future__ import annotations

from sqlalchemy.orm import Session

from database import models


class DepartmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, department_id: int) -> models.Department | None:
        return self.db.query(models.Department).filter(models.Department.id == department_id).first()

    def get_by_name(self, name: str) -> models.Department | None:
        return self.db.query(models.Department).filter(models.Department.name == name).first()

    def list(self) -> list[models.Department]:
        return self.db.query(models.Department).order_by(models.Department.name.asc()).all()

    def list_business_departments(self) -> list[models.Department]:
        return (
            self.db.query(models.Department)
            .filter(models.Department.id != 0)
            .order_by(models.Department.name.asc())
            .all()
        )

    def name_exists(self, name: str, exclude_id: int | None = None) -> bool:
        query = self.db.query(models.Department).filter(models.Department.name == name)
        if exclude_id is not None:
            query = query.filter(models.Department.id != exclude_id)
        return query.first() is not None

    def add(self, department: models.Department) -> models.Department:
        self.db.add(department)
        self.db.commit()
        self.db.refresh(department)
        return department

    def commit(self) -> None:
        self.db.commit()

    def delete(self, department: models.Department) -> None:
        self.db.delete(department)
        self.db.commit()
    