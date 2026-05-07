from sqlalchemy.orm import Session

from app.models import ActionLog


def log_action(
    db: Session,
    actor_key: str,
    action: str,
    target_type: str,
    target_id: str,
    status: str = "ok",
    details: str = "",
) -> None:
    db.add(
        ActionLog(
            actor_key=actor_key,
            action=action,
            target_type=target_type,
            target_id=target_id,
            status=status,
            details=details,
        )
    )
    db.commit()
