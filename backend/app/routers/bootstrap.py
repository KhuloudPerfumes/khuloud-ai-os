import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ActionLog, Approval, Bot, Channel, ChatMessage, GeneratedAsset, MemoryItem, Task

router = APIRouter(prefix="/api/bootstrap", tags=["bootstrap"])


def _as_dict(obj) -> dict:
    data = {column.name: getattr(obj, column.name) for column in obj.__table__.columns}
    for key in ["communication_permissions", "memory_scope", "output_structure", "allowed_bots", "metadata_json"]:
        if key in data and isinstance(data[key], str):
            try:
                data[key] = json.loads(data[key])
            except Exception:
                pass
    if "metadata_json" in data:
        data["metadata"] = data["metadata_json"]
    for key, value in list(data.items()):
        if hasattr(value, "isoformat"):
            data[key] = value.isoformat()
    return data


@router.get("")
def bootstrap(db: Session = Depends(get_db)) -> dict:
    tasks = db.query(Task).order_by(Task.created_at.desc()).limit(30).all()
    approvals = db.query(Approval).order_by(Approval.created_at.desc()).limit(30).all()
    messages = db.query(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(60).all()
    logs = db.query(ActionLog).order_by(ActionLog.created_at.desc()).limit(20).all()
    memories = db.query(MemoryItem).order_by(MemoryItem.created_at.desc()).limit(20).all()
    assets = db.query(GeneratedAsset).order_by(GeneratedAsset.created_at.desc()).limit(20).all()
    bots = db.query(Bot).order_by(Bot.active.desc(), Bot.department, Bot.name).all()
    channels = db.query(Channel).order_by(Channel.department, Channel.name).all()
    return {
        "bots": [_as_dict(item) for item in bots],
        "channels": [_as_dict(item) for item in channels],
        "tasks": [_as_dict(item) for item in tasks],
        "approvals": [_as_dict(item) for item in approvals],
        "messages": [_as_dict(item) for item in reversed(messages)],
        "logs": [_as_dict(item) for item in logs],
        "memory": [_as_dict(item) for item in memories],
        "assets": [_as_dict(item) for item in assets],
        "dashboard": {
            "active_bots": sum(1 for bot in bots if bot.active),
            "configured_bots": len(bots),
            "pending_approvals": sum(1 for item in approvals if item.status == "pending"),
            "open_tasks": sum(1 for item in tasks if item.status not in ["completed", "failed", "rejected"]),
            "health": "local-first ready",
        },
    }
