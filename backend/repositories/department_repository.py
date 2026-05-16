from sqlalchemy.orm import Session

from database import models


class DepartmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, department_id: int) -> models.Department | None:
        return self.db.query(models.Department).filter(models.Department.id == department_id).first()

    def list_business_departments(self) -> list[models.Department]:
        return (
            self.db.query(models.Department)
            .filter(models.Department.id != 0)
            .order_by(models.Department.name.asc())
            .all()
        )

