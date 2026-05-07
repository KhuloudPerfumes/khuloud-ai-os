from datetime import datetime
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ActionLog, ChatMessage, Task
from app.services.queues import QueueClient
from app.services.realtime import manager

router = APIRouter(prefix="/api/operations", tags=["operations"])


class ImageQueueRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=2000)
    title: str = "Queued visual request"


@router.post("/daily-check")
async def run_daily_check(db: Session = Depends(get_db)) -> dict:
    db_ok = _database_ok(db)
    redis_ok = QueueClient().ping()
    open_tasks = db.query(Task).filter(Task.status.notin_(["completed", "failed", "rejected"])).count()
    message = await _create_message(
        db,
        body=(
            "Daily check completed.\n\n"
            f"Database: {'online' if db_ok else 'unavailable'}\n"
            f"Queue: {'online' if redis_ok else 'unavailable'}\n"
            f"Open tasks: {open_tasks}\n\n"
            "Free cloud mode note: sleeping services may need a wake request before deeper checks run."
        ),
    )
    _log(db, "run_daily_check", "operation", message.id, "Daily check completed from founder dashboard.")
    return {"ok": True, "message_id": message.id, "database": db_ok, "redis": redis_ok, "open_tasks": open_tasks}


@router.post("/ceo-report")
async def generate_ceo_report(db: Session = Depends(get_db)) -> dict:
    tasks = db.query(Task).order_by(Task.created_at.desc()).limit(12).all()
    pending = [task for task in tasks if task.status not in ["completed", "failed", "rejected"]]
    approvals_needed = [task for task in pending if task.approval_needed]
    report_lines = [
        "Daily CEO report generated.",
        "",
        f"Open task count: {len(pending)}",
        f"Tasks needing founder approval: {len(approvals_needed)}",
        "",
        "Current CEO recommendation:",
        "Focus on one revenue-driving task, one operations risk, and one customer insight before creating new work.",
    ]
    if pending:
        report_lines.extend(["", "Highest attention tasks:"])
        report_lines.extend([f"- {task.title}: {task.next_step}" for task in pending[:5]])
    message = await _create_message(db, body="\n".join(report_lines))
    _log(db, "generate_daily_ceo_report", "operation", message.id, "Founder requested CEO report.")
    return {"ok": True, "message_id": message.id, "open_tasks": len(pending), "approvals_needed": len(approvals_needed)}


@router.post("/queue-image")
async def queue_image(payload: ImageQueueRequest, db: Session = Depends(get_db)) -> dict:
    task = Task(
        title=f"Queued image generation: {payload.title[:180]}",
        owner_key="creative_director",
        objective=payload.prompt,
        status="pending",
        priority="medium",
        risk="low",
        next_step="Generate locally when local AI/image service is available, or configure a free cloud model provider.",
        approval_needed=False,
        deadline="on demand",
        related_channel="content-studio",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    message = await _create_message(
        db,
        sender_key="creative_director",
        sender_name="Creative Director Bot",
        body=(
            "Image generation has been queued instead of forced in cloud mode.\n\n"
            f"Title: {payload.title}\n"
            f"Prompt: {payload.prompt}\n\n"
            "This avoids cloud failures when no free image model is configured. Run local generation when the laptop stack is on."
        ),
    )
    _log(db, "queue_image_generation", "task", task.id, payload.prompt)
    return {"ok": True, "task_id": task.id, "message_id": message.id}


def _database_ok(db: Session) -> bool:
    try:
        db.execute(text("select 1"))
        return True
    except Exception:
        return False


async def _create_message(
    db: Session,
    *,
    body: str,
    sender_key: str = "ceo",
    sender_name: str = "CEO Orchestrator Bot",
    channel_key: str = "founder-command",
) -> ChatMessage:
    message = ChatMessage(
        channel_key=channel_key,
        sender_key=sender_key,
        sender_name=sender_name,
        sender_type="bot",
        body=body,
        metadata_json=json.dumps({"operation": True, "created_at": datetime.utcnow().isoformat()}),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    await manager.broadcast(
        {
            "type": "message",
            "message": {
                "id": message.id,
                "channel_key": message.channel_key,
                "sender_key": message.sender_key,
                "sender_name": message.sender_name,
                "sender_type": message.sender_type,
                "body": message.body,
                "metadata": {"operation": True},
                "created_at": message.created_at.isoformat(),
            },
        }
    )
    return message


def _log(db: Session, action: str, target_type: str, target_id: str, details: str) -> None:
    db.add(ActionLog(actor_key="founder", action=action, target_type=target_type, target_id=target_id, status="ok", details=details))
    db.commit()
