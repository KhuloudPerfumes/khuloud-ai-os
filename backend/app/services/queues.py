import json

import redis

from app.core.config import get_settings


class QueueClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._redis: redis.Redis | None = None

    def client(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self.settings.redis_url, decode_responses=True)
        return self._redis

    def enqueue(self, queue: str, payload: dict) -> bool:
        try:
            self.client().lpush(queue, json.dumps(payload))
            return True
        except Exception:
            return False

    def ping(self) -> bool:
        try:
            return bool(self.client().ping())
        except Exception:
            return False
