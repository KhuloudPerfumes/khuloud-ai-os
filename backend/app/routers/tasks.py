from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Task, TaskStatus
from app.services.logging import log_action

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    owner_key: str
    objective: str
    priority: str = "medium"
    risk: str = "low"
    next_step: str = ""
    approval_needed: bool = False
    deadline: str = "not set"
    related_channel: str = "ceo-orchestrator"


class TaskUpdate(BaseModel):
    status: TaskStatus | None = None
    next_step: str | None = None
    priority: str | None = None
    risk: str | None = None


@router.post("")
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> dict:
    task = Task(**payload.model_dump(), status="needs_approval" if payload.approval_needed else "assigned")
    db.add(task)
    db.commit()
    db.refresh(task)
    log_action(db, "founder", "create_task", "task", task.id)
    return {"task": _task_dict(task)}


@router.patch("/{task_id}")
def update_task(task_id: str, payload: TaskUpdate, db: Session = Depends(get_db)) -> dict:
    task = db.query(Task).filter(Task.id == task_id).one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(task, key, value.value if isinstance(value, TaskStatus) else value)
    db.commit()
    db.refresh(task)
    log_action(db, "founder", "update_task", "task", task.id)
    return {"task": _task_dict(task)}


def _task_dict(task: Task) -> dict:
    return {column.name: getattr(task, column.name).isoformat() if hasattr(getattr(task, column.name), "isoformat") else getattr(task, column.name) for column in task.__table__.columns}
