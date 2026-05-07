from fastapi import APIRouter, Depends
import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.queues import QueueClient

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
def health(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    db_ok = True
    try:
        db.execute(text("select 1"))
    except Exception:
        db_ok = False
    redis_ok = QueueClient().ping()
    crewai = AgentOrchestrator().crewai_status()
    ai_ok = False
    try:
        with httpx.Client(timeout=2) as client:
            response = client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            ai_ok = response.status_code < 500
    except Exception:
        ai_ok = False
    shopify_configured = settings.shopify_webhook_secret not in ["", "change-me"]
    status = "ok" if db_ok else "degraded"
    return {
        "status": status,
        "mode": settings.environment,
        "database": db_ok,
        "redis": redis_ok,
        "ai_model": {
            "available": ai_ok,
            "provider": "ollama",
            "model": settings.ollama_model,
            "base_url": settings.ollama_base_url,
        },
        "shopify": {
            "configured": shopify_configured,
            "status": "configured" if shopify_configured else "not_configured",
        },
        "crewai": crewai,
    }
