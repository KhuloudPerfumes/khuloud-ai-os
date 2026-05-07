from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def new_id() -> str:
    return str(uuid4())


class TaskStatus(str, Enum):
    pending = "pending"
    assigned = "assigned"
    in_progress = "in_progress"
    needs_approval = "needs_approval"
    approved = "approved"
    rejected = "rejected"
    completed = "completed"
    failed = "failed"


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Bot(Base):
    __tablename__ = "bots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    department: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    authority_level: Mapped[str] = mapped_column(String(100))
    role_description: Mapped[str] = mapped_column(Text)
    communication_permissions: Mapped[str] = mapped_column(Text)
    approval_requirements: Mapped[str] = mapped_column(Text)
    memory_scope: Mapped[str] = mapped_column(Text)
    personality_style: Mapped[str] = mapped_column(Text)
    output_structure: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(100))
    purpose: Mapped[str] = mapped_column(Text)
    allowed_bots: Mapped[str] = mapped_column(Text)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    channel_key: Mapped[str] = mapped_column(String(100), index=True)
    sender_key: Mapped[str] = mapped_column(String(100), index=True)
    sender_name: Mapped[str] = mapped_column(String(160))
    sender_type: Mapped[str] = mapped_column(String(40), default="bot")
    body: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(240))
    owner_key: Mapped[str] = mapped_column(String(100), index=True)
    objective: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default=TaskStatus.pending.value, index=True)
    priority: Mapped[str] = mapped_column(String(40), default="medium")
    risk: Mapped[str] = mapped_column(String(40), default="low")
    next_step: Mapped[str] = mapped_column(Text, default="")
    approval_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    deadline: Mapped[str] = mapped_column(String(100), default="not set")
    related_channel: Mapped[str] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    approvals: Mapped[list["Approval"]] = relationship(back_populates="task")


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    requested_by: Mapped[str] = mapped_column(String(100))
    action_type: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)
    risk: Mapped[str] = mapped_column(String(40), default="medium")
    status: Mapped[str] = mapped_column(String(40), default=ApprovalStatus.pending.value, index=True)
    founder_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    task: Mapped[Task | None] = relationship(back_populates="approvals")


class MemoryItem(Base):
    __tablename__ = "memory_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    scope: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(240))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(120), default="system")
    created_by: Mapped[str] = mapped_column(String(100), default="ceo")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ActionLog(Base):
    __tablename__ = "action_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    actor_key: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(160))
    target_type: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(60), default="ok")
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GeneratedAsset(Base):
    __tablename__ = "generated_assets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(240))
    prompt: Mapped[str] = mapped_column(Text)
    asset_type: Mapped[str] = mapped_column(String(80), default="campaign_board_svg")
    created_by: Mapped[str] = mapped_column(String(100), default="creative_director")
    svg: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IntegrationEvent(Base):
    __tablename__ = "integration_events"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_integration_event"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    source: Mapped[str] = mapped_column(String(80), index=True)
    external_id: Mapped[str] = mapped_column(String(160), index=True)
    event_type: Mapped[str] = mapped_column(String(120))
    payload_json: Mapped[str] = mapped_column(Text)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
