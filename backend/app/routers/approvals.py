from datetime import datetime

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Approval, Task
from app.services.logging import log_action
from app.services.notifications import NotificationService

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


class ApprovalDecision(BaseModel):
    founder_note: str = ""


@router.post("/{approval_id}/approve")
async def approve(approval_id: str, payload: ApprovalDecision, db: Session = Depends(get_db)) -> dict:
    return await _decide(db, approval_id, "approved", payload.founder_note)


@router.post("/{approval_id}/reject")
async def reject(approval_id: str, payload: ApprovalDecision, db: Session = Depends(get_db)) -> dict:
    return await _decide(db, approval_id, "rejected", payload.founder_note)


async def _decide(db: Session, approval_id: str, status: str, note: str) -> dict:
    approval = db.query(Approval).filter(Approval.id == approval_id).one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    approval.status = status
    approval.founder_note = note
    approval.resolved_at = datetime.utcnow()
    if approval.task_id:
        task = db.query(Task).filter(Task.id == approval.task_id).one_or_none()
        if task:
            task.status = "approved" if status == "approved" else "rejected"
            task.next_step = f"Founder {status}. {note}".strip()
    db.commit()
    log_action(db, "founder", f"{status}_approval", "approval", approval.id, details=note)
    await NotificationService().notify_founder(f"Approval {status}: KHULOUD AI OS", approval.summary)
    return {"approval_id": approval.id, "status": approval.status}
