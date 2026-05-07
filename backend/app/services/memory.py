from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import MemoryItem


def search_memory(db: Session, query: str, scopes: list[str] | None = None, limit: int = 6) -> list[MemoryItem]:
    q = db.query(MemoryItem)
    if scopes and "all" not in scopes:
        q = q.filter(MemoryItem.scope.in_(scopes))
    words = [word.strip() for word in query.split() if len(word.strip()) > 3][:6]
    if words:
        clauses = []
        for word in words:
            pattern = f"%{word}%"
            clauses.append(MemoryItem.title.ilike(pattern))
            clauses.append(MemoryItem.content.ilike(pattern))
            clauses.append(MemoryItem.scope.ilike(pattern))
        q = q.filter(or_(*clauses))
    return q.order_by(MemoryItem.created_at.desc()).limit(limit).all()


def add_memory(db: Session, scope: str, title: str, content: str, created_by: str, source: str = "agent") -> MemoryItem:
    item = MemoryItem(scope=scope, title=title[:240], content=content, created_by=created_by, source=source)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
