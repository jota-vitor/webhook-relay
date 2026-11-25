from collections import deque
from functools import lru_cache
from typing import Protocol

from app.config import settings


class DeliveryQueue(Protocol):
    def push(self, delivery_id: int) -> None: ...
    def schedule(self, delivery_id: int, run_at: float) -> None: ...
    def pop(self, timeout: int = 1) -> int | None: ...
    def promote_due(self, now: float) -> int: ...


class RedisQueue:
    """Fila pronta (lista) + fila de espera (sorted set ordenado pelo horário de execução)."""

    READY = "relay:ready"
    DELAYED = "relay:delayed"

    def __init__(self, url: str):
        import redis

        self.redis = redis.Redis.from_url(url, decode_responses=True)

    def push(self, delivery_id: int) -> None:
        self.redis.lpush(self.READY, delivery_id)

    def schedule(self, delivery_id: int, run_at: float) -> None:
        self.redis.zadd(self.DELAYED, {str(delivery_id): run_at})

    def pop(self, timeout: int = 1) -> int | None:
        item = self.redis.brpop([self.READY], timeout=timeout)
        return int(item[1]) if item else None

    def promote_due(self, now: float) -> int:
        moved = 0
        for delivery_id in self.redis.zrangebyscore(self.DELAYED, 0, now):
            # zrem só devolve 1 para um worker: com vários workers, ninguém duplica a entrega
            if self.redis.zrem(self.DELAYED, delivery_id):
                self.redis.lpush(self.READY, delivery_id)
                moved += 1
        return moved


class MemoryQueue:
    """Mesma interface, sem Redis. Usada nos testes."""

    def __init__(self):
        self.ready: deque[int] = deque()
        self.delayed: list[tuple[float, int]] = []

    def push(self, delivery_id: int) -> None:
        self.ready.appendleft(delivery_id)

    def schedule(self, delivery_id: int, run_at: float) -> None:
        self.delayed.append((run_at, delivery_id))

    def pop(self, timeout: int = 1) -> int | None:
        return self.ready.pop() if self.ready else None

    def promote_due(self, now: float) -> int:
        due = [item for item in self.delayed if item[0] <= now]
        self.delayed = [item for item in self.delayed if item[0] > now]
        for _, delivery_id in sorted(due):
            self.push(delivery_id)
        return len(due)


@lru_cache
def get_queue() -> DeliveryQueue:
    return RedisQueue(settings.redis_url)
