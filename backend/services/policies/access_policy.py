from sqlalchemy.orm import Session

from database import models
from repositories.sharing_repository import SharingRepository
from utils.enum_utils import enum_value


def _scope_str(scope_value) -> str:
    return enum_value(scope_value)


def is_document_shared_with_user(db: Session, user: models.User, doc: models.Document) -> bool:
    if user.role == models.RoleEnum.admin and user.department_id == 0:
        return True

    return SharingRepository(db).find_access_share(user, doc) is not None


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
        if user.department_id == doc.department_id:
            return True
        return is_document_shared_with_user(db, user, doc)

    return False
