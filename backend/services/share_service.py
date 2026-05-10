from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import models


def _ensure_manager_can_share_doc(db: Session, manager_user_id: int, doc_id: int):
    manager = db.query(models.User).filter(models.User.id == manager_user_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.scope == models.ScopeEnum.department,
        models.Document.department_id == manager.department_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Tai lieu khong ton tai hoac khong thuoc phong ban cua ban")
    return manager, doc


def share_document_to_department(db: Session, manager_user_id: int, doc_id: int, dept_id: int):
    _, doc = _ensure_manager_can_share_doc(db, manager_user_id, doc_id)

    existing = db.query(models.SharedDocument).filter(
        models.SharedDocument.document_id == doc.id,
        models.SharedDocument.shared_with_dept_id == dept_id,
    ).first()
    if existing:
        return {"status": "exists", "share_id": existing.id}

    share = models.SharedDocument(document_id=doc_id, shared_with_dept_id=dept_id, shared_by=manager_user_id)
    db.add(share)
    db.commit()
    db.refresh(share)

    return {"status": "success", "share_id": share.id}


def share_document_to_user(db: Session, manager_user_id: int, doc_id: int, username: str):
    _, doc = _ensure_manager_can_share_doc(db, manager_user_id, doc_id)
    target_user = db.query(models.User).filter(models.User.username == username).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Khong tim thay tai khoan duoc chia se")

    existing = db.query(models.SharedDocument).filter(
        models.SharedDocument.document_id == doc.id,
        models.SharedDocument.shared_with_user_id == target_user.id,
    ).first()
    if existing:
        return {"status": "exists", "share_id": existing.id}

    share = models.SharedDocument(
        document_id=doc.id,
        shared_with_dept_id=None,
        shared_with_user_id=target_user.id,
        shared_by=manager_user_id,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return {
        "status": "success",
        "share_id": share.id,
        "shared_with_username": target_user.username,
    }


def revoke_share(db: Session, manager_user_id: int, share_id: int):
    share = db.query(models.SharedDocument).filter(
        models.SharedDocument.id == share_id,
        models.SharedDocument.shared_by == manager_user_id,
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="Chia se khong ton tai")

    db.delete(share)
    db.commit()
    return {"status": "success"}


def _ensure_admin(db: Session, admin_user_id: int):
    admin_user = db.query(models.User).filter(models.User.id == admin_user_id).first()
    if not admin_user:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")
    if admin_user.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Chi admin duoc thao tac")
    return admin_user


def list_all_shares(db: Session, search: str = ""):
    query = db.query(models.SharedDocument).order_by(models.SharedDocument.created_at.desc())
    if search:
        query = query.join(models.Document, models.SharedDocument.document_id == models.Document.id).filter(
            models.Document.filename.contains(search)
        )

    shares = query.all()
    results = []
    for share in shares:
        document = db.query(models.Document).filter(models.Document.id == share.document_id).first()
        source_department = None
        if document and document.department_id is not None:
            source_department = db.query(models.Department).filter(models.Department.id == document.department_id).first()

        target_department = None
        if share.shared_with_dept_id is not None:
            target_department = db.query(models.Department).filter(models.Department.id == share.shared_with_dept_id).first()

        target_user = None
        if share.shared_with_user_id is not None:
            target_user = db.query(models.User).filter(models.User.id == share.shared_with_user_id).first()

        shared_by_user = db.query(models.User).filter(models.User.id == share.shared_by).first()
        results.append(
            {
                "id": share.id,
                "document_id": share.document_id,
                "document_filename": document.filename if document else "N/A",
                "document_department_id": document.department_id if document else None,
                "document_department_name": source_department.name if source_department else None,
                "shared_with_dept_id": share.shared_with_dept_id,
                "shared_with_department_name": target_department.name if target_department else None,
                "shared_with_user_id": share.shared_with_user_id,
                "shared_with_username": target_user.username if target_user else None,
                "shared_by": share.shared_by,
                "shared_by_username": shared_by_user.username if shared_by_user else None,
                "created_at": str(share.created_at),
            }
        )
    return results


def list_manager_shares(db: Session, manager_user_id: int):
    query = db.query(models.SharedDocument).filter(
        models.SharedDocument.shared_by == manager_user_id,
    ).order_by(models.SharedDocument.created_at.desc())

    shares = query.all()
    results = []
    for share in shares:
        document = db.query(models.Document).filter(models.Document.id == share.document_id).first()
        source_department = None
        if document and document.department_id is not None:
            source_department = db.query(models.Department).filter(models.Department.id == document.department_id).first()

        target_department = None
        if share.shared_with_dept_id is not None:
            target_department = db.query(models.Department).filter(models.Department.id == share.shared_with_dept_id).first()

        target_user = None
        if share.shared_with_user_id is not None:
            target_user = db.query(models.User).filter(models.User.id == share.shared_with_user_id).first()

        results.append(
            {
                "id": share.id,
                "document_id": share.document_id,
                "document_filename": document.filename if document else "N/A",
                "document_department_id": document.department_id if document else None,
                "document_department_name": source_department.name if source_department else None,
                "shared_with_dept_id": share.shared_with_dept_id,
                "shared_with_department_name": target_department.name if target_department else None,
                "shared_with_user_id": share.shared_with_user_id,
                "shared_with_username": target_user.username if target_user else None,
                "shared_by": share.shared_by,
                "created_at": str(share.created_at),
            }
        )
    return results


def share_document_to_department_as_admin(db: Session, admin_user_id: int, doc_id: int, dept_id: int):
    _ensure_admin(db, admin_user_id)
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.scope == models.ScopeEnum.department,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Tai lieu phong ban khong ton tai")

    dept = db.query(models.Department).filter(models.Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Phong ban khong ton tai")

    existing = db.query(models.SharedDocument).filter(
        models.SharedDocument.document_id == doc.id,
        models.SharedDocument.shared_with_dept_id == dept_id,
    ).first()
    if existing:
        return {"status": "exists", "share_id": existing.id}

    share = models.SharedDocument(document_id=doc.id, shared_with_dept_id=dept_id, shared_by=admin_user_id)
    db.add(share)
    db.commit()
    db.refresh(share)
    return {"status": "success", "share_id": share.id}


def share_document_to_user_as_admin(db: Session, admin_user_id: int, doc_id: int, username: str):
    _ensure_admin(db, admin_user_id)
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.scope == models.ScopeEnum.department,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Tai lieu phong ban khong ton tai")

    target_user = db.query(models.User).filter(models.User.username == username).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Khong tim thay tai khoan duoc chia se")

    existing = db.query(models.SharedDocument).filter(
        models.SharedDocument.document_id == doc.id,
        models.SharedDocument.shared_with_user_id == target_user.id,
    ).first()
    if existing:
        return {"status": "exists", "share_id": existing.id}

    share = models.SharedDocument(
        document_id=doc.id,
        shared_with_dept_id=None,
        shared_with_user_id=target_user.id,
        shared_by=admin_user_id,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return {
        "status": "success",
        "share_id": share.id,
        "shared_with_username": target_user.username,
    }


def revoke_share_as_admin(db: Session, admin_user_id: int, share_id: int):
    _ensure_admin(db, admin_user_id)
    share = db.query(models.SharedDocument).filter(models.SharedDocument.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="Chia se khong ton tai")

    db.delete(share)
    db.commit()
    return {"status": "success"}


def list_contributors(db: Session, manager_user_id: int):
    manager = db.query(models.User).filter(models.User.id == manager_user_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    contributors = db.query(models.Contributor).filter(
        models.Contributor.department_id == manager.department_id
    ).order_by(models.Contributor.created_at.desc()).all()

    results = []
    for contributor in contributors:
        user = db.query(models.User).filter(models.User.id == contributor.user_id).first()
        results.append(
            {
                "id": contributor.id,
                "user_id": contributor.user_id,
                "username": user.username if user else "N/A",
                "created_at": str(contributor.created_at),
            }
        )
    return results


def add_contributor(db: Session, manager_user_id: int, target_user_id: int):
    manager = db.query(models.User).filter(models.User.id == manager_user_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    existing = db.query(models.Contributor).filter(
        models.Contributor.user_id == target_user_id,
        models.Contributor.department_id == manager.department_id,
    ).first()
    if existing:
        return {"status": "exists", "id": existing.id}

    contributor = models.Contributor(
        user_id=target_user_id,
        granted_by=manager_user_id,
        department_id=manager.department_id,
    )
    db.add(contributor)
    db.commit()
    db.refresh(contributor)

    return {"status": "success", "id": contributor.id}


def remove_contributor(db: Session, manager_user_id: int, contrib_id: int):
    manager = db.query(models.User).filter(models.User.id == manager_user_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")

    contributor = db.query(models.Contributor).filter(
        models.Contributor.id == contrib_id,
        models.Contributor.department_id == manager.department_id,
    ).first()
    if not contributor:
        raise HTTPException(status_code=404, detail="Contributor not found")

    db.delete(contributor)
    db.commit()
    return {"status": "success"}
