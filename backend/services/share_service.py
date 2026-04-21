from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import models


def share_document_to_department(db: Session, manager_user_id: int, doc_id: int, dept_id: int):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Tai lieu khong ton tai")

    share = models.SharedDocument(document_id=doc_id, shared_with_dept_id=dept_id, shared_by=manager_user_id)
    db.add(share)
    db.commit()
    db.refresh(share)

    return {"status": "success", "share_id": share.id}


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


def remove_contributor(db: Session, contrib_id: int):
    contributor = db.query(models.Contributor).filter(models.Contributor.id == contrib_id).first()
    if not contributor:
        raise HTTPException(status_code=404, detail="Contributor not found")

    db.delete(contributor)
    db.commit()
    return {"status": "success"}
