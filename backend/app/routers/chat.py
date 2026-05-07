from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChatMessage
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.logging import log_action
from app.services.realtime import manager

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    channel_key: str = "founder-command"
    body: str = Field(min_length=1, max_length=6000)


class DirectBotRequest(BaseModel):
    channel_key: str = "founder-command"
    bot_key: str
    body: str = Field(min_length=1, max_length=6000)


@router.post("")
async def send_message(payload: ChatRequest, db: Session = Depends(get_db)) -> dict:
    founder_message = ChatMessage(
        channel_key=payload.channel_key,
        sender_key="founder",
        sender_name="Founder",
        sender_type="founder",
        body=payload.body,
    )
    db.add(founder_message)
    db.commit()
    db.refresh(founder_message)
    await manager.broadcast({"type": "message", "message": _message_dict(founder_message)})

    result = await AgentOrchestrator().handle_founder_message(db, payload.channel_key, payload.body)
    log_action(db, "ceo", "route_founder_message", "task", result.task.id if result.task else "none")
    for message in result.messages:
        await manager.broadcast({"type": "message", "message": _message_dict(message)})
    if result.approval:
        await manager.broadcast({"type": "approval_created", "approval_id": result.approval.id})
    return {
        "founder_message": _message_dict(founder_message),
        "bot_messages": [_message_dict(message) for message in result.messages],
        "task_id": result.task.id if result.task else None,
        "approval_id": result.approval.id if result.approval else None,
    }


@router.post("/direct")
async def direct_bot_message(payload: DirectBotRequest, db: Session = Depends(get_db)) -> dict:
    founder_message = ChatMessage(
        channel_key=payload.channel_key,
        sender_key="founder",
        sender_name=f"Founder -> {payload.bot_key}",
        sender_type="founder",
        body=payload.body,
    )
    db.add(founder_message)
    db.commit()
    db.refresh(founder_message)
    await manager.broadcast({"type": "message", "message": _message_dict(founder_message)})

    result = await AgentOrchestrator().handle_direct_bot_message(db, payload.channel_key, payload.bot_key, payload.body)
    log_action(db, payload.bot_key, "direct_bot_response", "task", result.task.id if result.task else "none")
    for message in result.messages:
        await manager.broadcast({"type": "message", "message": _message_dict(message)})
    if result.approval:
        await manager.broadcast({"type": "approval_created", "approval_id": result.approval.id})
    return {
        "founder_message": _message_dict(founder_message),
        "bot_messages": [_message_dict(message) for message in result.messages],
        "task_id": result.task.id if result.task else None,
        "approval_id": result.approval.id if result.approval else None,
    }


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def _message_dict(message: ChatMessage) -> dict:
    import json

    try:
        metadata = json.loads(message.metadata_json or "{}")
    except Exception:
        metadata = {}
    return {
        "id": message.id,
        "channel_key": message.channel_key,
        "sender_key": message.sender_key,
        "sender_name": message.sender_name,
        "sender_type": message.sender_type,
        "body": message.body,
        "metadata": metadata,
        "created_at": message.created_at.isoformat(),
    }
