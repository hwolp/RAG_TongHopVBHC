from database import models


def can_access_document(user: models.User | None, doc: models.Document | None) -> bool:
    if not user or not doc:
        return False

    if user.role == models.RoleEnum.admin:
        return True

    if doc.owner_id == user.id:
        return True

    scope = doc.scope.value if hasattr(doc.scope, "value") else str(doc.scope)
    if scope == "department" and user.department_id and doc.department_id == user.department_id:
        return True
    if scope == "sqp":
        return True

    return False
