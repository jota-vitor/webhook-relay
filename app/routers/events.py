from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.deps import DbSession, PageParams, Queue
from app.models import Delivery, DeliveryStatus, Event, Source
from app.schemas import DeliveryOut, EventDetail, EventOut, Page

router = APIRouter(tags=["events"])


@router.get("/events", response_model=Page[EventOut])
def list_events(db: DbSession, pagination: PageParams, source: str | None = None):
    query = select(Event)
    if source:
        query = query.join(Source).where(Source.name == source)

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(
        query.order_by(Event.received_at.desc(), Event.id)
        .offset(pagination.offset)
        .limit(pagination.size)
    ).all()
    return Page[EventOut](items=items, total=total, page=pagination.page, size=pagination.size)


@router.get("/events/{event_id}", response_model=EventDetail)
def get_event(event_id: str, db: DbSession):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento não encontrado")
    return event


@router.get("/deliveries", response_model=list[DeliveryOut])
def list_deliveries(
    db: DbSession,
    status_filter: Annotated[DeliveryStatus, Query(alias="status")] = DeliveryStatus.dead,
):
    """Por padrão lista a "fila morta": entregas que esgotaram as tentativas."""
    return db.scalars(
        select(Delivery).where(Delivery.status == status_filter).order_by(Delivery.id).limit(100)
    ).all()


@router.post("/deliveries/{delivery_id}/retry", response_model=DeliveryOut)
def retry_delivery(delivery_id: int, db: DbSession, queue: Queue):
    delivery = db.get(Delivery, delivery_id)
    if delivery is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entrega não encontrada")
    if delivery.status != DeliveryStatus.dead:
        raise HTTPException(status.HTTP_409_CONFLICT, "Só entregas mortas podem ser reenviadas")

    delivery.status = DeliveryStatus.pending
    delivery.attempts = 0
    delivery.next_attempt_at = None
    db.commit()
    db.refresh(delivery)
    queue.push(delivery.id)
    return delivery
