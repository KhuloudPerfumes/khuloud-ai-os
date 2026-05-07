import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Bot

router = APIRouter(prefix="/api/bots", tags=["bots"])


@router.get("")
def list_bots(db: Session = Depends(get_db)) -> dict:
    bots = db.query(Bot).order_by(Bot.active.desc(), Bot.department, Bot.name).all()
    return {
        "bots": [
            {
                "key": bot.key,
                "name": bot.name,
                "department": bot.department,
                "active": bot.active,
                "authority_level": bot.authority_level,
                "communication_permissions": json.loads(bot.communication_permissions),
                "memory_scope": json.loads(bot.memory_scope),
            }
            for bot in bots
        ]
    }
