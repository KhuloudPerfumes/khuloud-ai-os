import json
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.models import Bot, Channel, ChatMessage, MemoryItem, Task


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def seed_system(db: Session, config_dir: Path) -> None:
    bots_data = _load_yaml(config_dir / "bots.yaml")["bots"]
    channels_data = _load_yaml(config_dir / "channels.yaml")["channels"]

    for item in bots_data:
        bot = db.query(Bot).filter(Bot.key == item["key"]).one_or_none()
        payload = {
            "key": item["key"],
            "name": item["name"],
            "department": item["department"],
            "active": bool(item["active"]),
            "authority_level": item["authority_level"],
            "role_description": item["role_description"],
            "communication_permissions": json.dumps(item["communication_permissions"]),
            "approval_requirements": item["approval_requirements"],
            "memory_scope": json.dumps(item["memory_scope"]),
            "personality_style": item["personality_style"],
            "output_structure": json.dumps(item["output_structure"]),
        }
        if bot:
            for key, value in payload.items():
                setattr(bot, key, value)
        else:
            db.add(Bot(**payload))

    for item in channels_data:
        channel = db.query(Channel).filter(Channel.key == item["key"]).one_or_none()
        payload = {
            "key": item["key"],
            "name": item["name"],
            "department": item["department"],
            "purpose": item["purpose"],
            "allowed_bots": json.dumps(item["allowed_bots"]),
        }
        if channel:
            for key, value in payload.items():
                setattr(channel, key, value)
        else:
            db.add(Channel(**payload))

    if db.query(MemoryItem).count() == 0:
        db.add_all(
            [
                MemoryItem(
                    scope="brand_guidelines",
                    title="Luxury restraint",
                    content="KHULOUD should feel refined, intimate, premium, and sensory. Avoid cheap urgency, exaggerated claims, and noisy visuals.",
                    source="seed",
                    created_by="founder_proxy",
                ),
                MemoryItem(
                    scope="approval_policy",
                    title="Founder approval gates",
                    content="Money spend, ad launches, customer messages, price edits, refunds, order cancellation, and live Shopify theme edits always need founder approval.",
                    source="seed",
                    created_by="ceo",
                ),
                MemoryItem(
                    scope="customer_objections",
                    title="Common early objections",
                    content="Customers may ask about longevity, authenticity, COD trust, delivery timing, gifting suitability, and whether a scent is too strong.",
                    source="seed",
                    created_by="whatsapp_sales",
                ),
            ]
        )

    if db.query(Task).count() == 0:
        db.add_all(
            [
                Task(
                    title="Create daily operating rhythm",
                    owner_key="ceo",
                    objective="Establish morning summary, approvals review, and end-of-day report cadence.",
                    status="assigned",
                    priority="high",
                    risk="low",
                    next_step="Confirm founder reporting preferences.",
                    approval_needed=False,
                    deadline="Today",
                    related_channel="ceo-orchestrator",
                ),
                Task(
                    title="Review Shopify conversion risks",
                    owner_key="shopify_cro",
                    objective="Identify product page and checkout improvements that require approval before live changes.",
                    status="needs_approval",
                    priority="high",
                    risk="medium",
                    next_step="Prepare first CRO experiment proposal.",
                    approval_needed=True,
                    deadline="This week",
                    related_channel="shopify-cro",
                ),
            ]
        )

    if db.query(ChatMessage).count() == 0:
        db.add(
            ChatMessage(
                channel_key="founder-command",
                sender_key="ceo",
                sender_name="CEO Orchestrator Bot",
                sender_type="bot",
                body="KHULOUD AI OS is online. V1 active employees: CEO, Creative Director, Performance Marketing, Shopify CRO, and WhatsApp Sales. I will route work, protect approval gates, and log every material action.",
            )
        )

    db.commit()
