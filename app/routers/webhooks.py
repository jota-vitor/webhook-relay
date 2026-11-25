import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from app.config import settings
from app.deps import DbSession, Queue
from app.models import Delivery, Destination, Event, Source
from app.schemas import WebhookAccepted
from app.signatures import SignatureError, verify

router = APIRouter(tags=["webhooks"])


async def raw_body(request: Request) -> bytes:
    # A assinatura é calculada sobre os bytes exatos recebidos, antes de qualquer parse.
    # Ler o corpo aqui (async) deixa a rota síncrona, rodando no threadpool junto com o banco.
    return await request.body()


@router.post(
    "/webhooks/{source_name}",
    response_model=WebhookAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def receive_webhook(
    source_name: str,
    request: Request,
    response: Response,
    body: Annotated[bytes, Depends(raw_body)],
    db: DbSession,
    queue: Queue,
):
    source = db.scalar(select(Source).where(Source.name == source_name))
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Origem desconhecida")

    try:
        verify(
            source.secret,
            body,
            request.headers.get("X-Signature"),
            settings.signature_tolerance_seconds,
        )
    except SignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from None

    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "O corpo precisa ser JSON") from None
    if not isinstance(payload, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "O corpo precisa ser um objeto JSON")

    # provedores reenviam o mesmo evento quando não recebem resposta a tempo
    external_id = request.headers.get("X-Event-Id")
    if external_id:
        existing = db.scalar(
            select(Event).where(Event.source_id == source.id, Event.external_id == external_id)
        )
        if existing:
            response.status_code = status.HTTP_200_OK
            return WebhookAccepted(
                event_id=existing.id, duplicate=True, deliveries=len(existing.deliveries)
            )

    event = Event(
        source_id=source.id,
        external_id=external_id,
        event_type=request.headers.get("X-Event-Type") or payload.get("type"),
        payload=payload,
    )
    db.add(event)

    destinations = db.scalars(select(Destination).where(Destination.active.is_(True))).all()
    deliveries = [Delivery(event=event, destination_id=d.id) for d in destinations]
    db.add_all(deliveries)
    db.commit()

    # responde rápido: a entrega de verdade acontece no worker
    for delivery in deliveries:
        queue.push(delivery.id)

    return WebhookAccepted(event_id=event.id, duplicate=False, deliveries=len(deliveries))
