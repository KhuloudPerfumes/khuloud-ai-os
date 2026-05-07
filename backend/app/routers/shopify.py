import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.models import IntegrationEvent
from app.services.queues import QueueClient

router = APIRouter(prefix="/api/shopify", tags=["shopify"])


@router.post("/webhooks/{event_type}")
async def shopify_webhook(
    event_type: str,
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_webhook_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    body = await request.body()
    if not _verify(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="Invalid Shopify webhook signature")
    payload = json.loads(body.decode("utf-8") or "{}")
    event = IntegrationEvent(
        source="shopify",
        external_id=x_shopify_webhook_id or payload.get("id", "unknown"),
        event_type=event_type,
        payload_json=json.dumps(payload),
    )
    db.add(event)
    db.commit()
    QueueClient().enqueue("shopify_events", {"event_id": event.id, "event_type": event_type})
    return {"ok": True, "event_id": event.id, "dangerous_actions_executed": False}


def _verify(body: bytes, received: str | None) -> bool:
    settings = get_settings()
    if settings.shopify_webhook_secret == "change-me":
        return True
    if not received:
        return False
    digest = hmac.new(settings.shopify_webhook_secret.encode(), body, hashlib.sha256).digest()
    import base64

    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, received)
