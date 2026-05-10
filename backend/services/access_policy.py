from sqlalchemy.orm import Session

from database import models


def _scope_str(scope_value) -> str:
    return scope_value.value if hasattr(scope_value, "value") else str(scope_value)


def is_document_shared_with_user(db: Session, user: models.User, doc: models.Document) -> bool:
    if user.role == models.RoleEnum.admin and user.department_id == 0:
        return True

    share = db.query(models.SharedDocument).filter(
        models.SharedDocument.document_id == doc.id,
        (models.SharedDocument.shared_with_user_id == user.id)
        | (models.SharedDocument.shared_with_dept_id == user.department_id),
    ).first()
    return share is not None


def can_access_document(db: Session, user: models.User | None, doc: models.Document | None) -> bool:
    if not user or not doc:
        return False

    if user.role == models.RoleEnum.admin:
        return True

    if doc.owner_id == user.id:
        return True

    scope = _scope_str(doc.scope)
    if scope == "sqp":
        return True

    if scope == "department":
        # Only manager can read own department by default.
        if user.role == models.RoleEnum.manager and user.department_id == doc.department_id:
            return True
        # Employee/manager from other departments can read only when explicitly shared.
        return is_document_shared_with_user(db, user, doc)

    return False
