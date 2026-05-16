from sqlalchemy.orm import Session

from database import models
from services.jobs import job_service
from utils.enum_utils import enum_value
from utils.errors import bad_request, not_found


def _status_str(status_value) -> str:
    return enum_value(status_value)


def list_all_proposals(db: Session):
    proposals = db.query(models.SQPProposal).order_by(models.SQPProposal.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "document_id": p.document_id,
            "proposed_by": p.proposed_by,
            "status": _status_str(p.status),
            "created_at": str(p.created_at),
        }
        for p in proposals
    ]


def list_manager_proposals(db: Session, manager_user_id: int):
    proposals = db.query(models.SQPProposal).filter(
        models.SQPProposal.proposed_by == manager_user_id
    ).order_by(models.SQPProposal.created_at.desc()).all()

    return [
        {
            "id": p.id,
            "document_id": p.document_id,
            "status": _status_str(p.status),
            "created_at": str(p.created_at),
        }
        for p in proposals
    ]


def propose_document_to_sqp(db: Session, manager_user_id: int, document_id: int):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise not_found("Tai lieu khong ton tai")

    existing = db.query(models.SQPProposal).filter(
        models.SQPProposal.document_id == document_id,
        models.SQPProposal.status == models.ProposalStatus.pending,
    ).first()
    if existing:
        raise bad_request("Tai lieu da co de xuat dang cho duyet")

    proposal = models.SQPProposal(document_id=document_id, proposed_by=manager_user_id)
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return {"status": "success", "proposal_id": proposal.id}


def cancel_pending_proposal(db: Session, manager_user_id: int, proposal_id: int):
    proposal = db.query(models.SQPProposal).filter(
        models.SQPProposal.id == proposal_id,
        models.SQPProposal.proposed_by == manager_user_id,
        models.SQPProposal.status == models.ProposalStatus.pending,
    ).first()
    if not proposal:
        raise not_found("De xuat khong ton tai hoac da duoc xu ly")

    db.delete(proposal)
    db.commit()
    return {"status": "success"}


def approve_proposal(db: Session, proposal_id: int):
    proposal = db.query(models.SQPProposal).filter(models.SQPProposal.id == proposal_id).first()
    if not proposal:
        raise not_found("De xuat khong ton tai")

    proposal.status = models.ProposalStatus.approved
    doc = db.query(models.Document).filter(models.Document.id == proposal.document_id).first()
    job = None
    if doc:
        if doc.is_indexed:
            try:
                from rag_engine.chroma_manager import ChromaDBManager

                ChromaDBManager().delete_doc_from_index(doc.id)
            except Exception:
                pass
        doc.scope = models.ScopeEnum.sqp
        doc.is_indexed = False
        db.commit()
        job = job_service.create_index_job(db, doc, proposal.proposed_by, force_admin_chunking=True)
    else:
        db.commit()

    return {
        "status": "success",
        "message": "Da duyet thanh SQP",
        "job_id": job.id if job else None,
    }


def reject_proposal(db: Session, proposal_id: int):
    proposal = db.query(models.SQPProposal).filter(models.SQPProposal.id == proposal_id).first()
    if not proposal:
        raise not_found("De xuat khong ton tai")

    proposal.status = models.ProposalStatus.rejected
    db.commit()
    return {"status": "success"}
