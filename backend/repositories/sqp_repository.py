from __future__ import annotations

from sqlalchemy.orm import Session

from database import models


class SQPProposalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, proposal_id: int) -> models.SQPProposal | None:
        return self.db.query(models.SQPProposal).filter(models.SQPProposal.id == proposal_id).first()

    def get_pending_by_manager(self, manager_user_id: int, proposal_id: int) -> models.SQPProposal | None:
        return (
            self.db.query(models.SQPProposal)
            .filter(
                models.SQPProposal.id == proposal_id,
                models.SQPProposal.proposed_by == manager_user_id,
                models.SQPProposal.status == models.ProposalStatus.pending,
            )
            .first()
        )

    def pending_for_document(self, document_id: int) -> models.SQPProposal | None:
        return (
            self.db.query(models.SQPProposal)
            .filter(
                models.SQPProposal.document_id == document_id,
                models.SQPProposal.status == models.ProposalStatus.pending,
            )
            .first()
        )

    def list_all(self) -> list[models.SQPProposal]:
        return self.db.query(models.SQPProposal).order_by(models.SQPProposal.created_at.desc()).all()

    def list_by_manager(self, manager_user_id: int) -> list[models.SQPProposal]:
        return (
            self.db.query(models.SQPProposal)
            .filter(models.SQPProposal.proposed_by == manager_user_id)
            .order_by(models.SQPProposal.created_at.desc())
            .all()
        )

    def add(self, proposal: models.SQPProposal) -> models.SQPProposal:
        self.db.add(proposal)
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def commit(self) -> None:
        self.db.commit()

    def delete(self, proposal: models.SQPProposal) -> None:
        self.db.delete(proposal)
        self.db.commit()
