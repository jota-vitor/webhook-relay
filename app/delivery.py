import json
import time
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from app.backoff import is_retryable, next_delay
from app.models import Delivery, DeliveryStatus
from app.signatures import sign
from app.task_queue import DeliveryQueue

# Recebe (url, corpo, cabeçalhos) e devolve o status HTTP. Pode lançar exceção de rede.
Sender = Callable[[str, bytes, dict[str, str]], int]


def http_sender(url: str, body: bytes, headers: dict[str, str]) -> int:
    with httpx.Client(timeout=10) as client:
        return client.post(url, content=body, headers=headers).status_code


def build_body(delivery: Delivery) -> bytes:
    event = delivery.event
    return json.dumps(
        {
            "id": event.id,
            "type": event.event_type,
            "source": event.source.name,
            "payload": event.payload,
        },
        separators=(",", ":"),
    ).encode()


def process_delivery(
    db: Session,
    delivery_id: int,
    queue: DeliveryQueue,
    sender: Sender,
    max_attempts: int = 8,
    now: float | None = None,
) -> DeliveryStatus | None:
    delivery = db.get(Delivery, delivery_id)
    if delivery is None or delivery.status != DeliveryStatus.pending:
        return None  # já resolvida por outro worker ou removida

    now = time.time() if now is None else now
    body = build_body(delivery)
    delivery.attempts += 1
    headers = {
        "Content-Type": "application/json",
        "X-Relay-Signature": sign(delivery.destination.secret, body, int(now)),
        "X-Relay-Delivery": str(delivery.id),
        "X-Relay-Attempt": str(delivery.attempts),
    }

    try:
        status_code = sender(delivery.destination.url, body, headers)
        delivery.last_status_code = status_code
        delivery.last_error = None if 200 <= status_code < 300 else f"HTTP {status_code}"
    except Exception as exc:  # timeout, DNS, conexão recusada...
        status_code = None
        delivery.last_status_code = None
        delivery.last_error = f"{type(exc).__name__}: {exc}"[:500]

    run_at = None
    if status_code is not None and 200 <= status_code < 300:
        delivery.status = DeliveryStatus.succeeded
        delivery.next_attempt_at = None
    elif not is_retryable(status_code) or delivery.attempts >= max_attempts:
        delivery.status = DeliveryStatus.dead
        delivery.next_attempt_at = None
    else:
        run_at = now + next_delay(delivery.attempts)
        delivery.next_attempt_at = datetime.fromtimestamp(run_at, UTC)

    db.commit()

    # agenda só depois do commit, para o próximo worker já enxergar o estado salvo
    if run_at is not None:
        queue.schedule(delivery.id, run_at)
    return delivery.status
