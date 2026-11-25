import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeliveryStatus(enum.StrEnum):
    pending = "pending"
    succeeded = "succeeded"
    dead = "dead"


class Source(Base):
    """Quem envia webhooks para o relay (ex.: gateway de pagamento, GitHub)."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    secret: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Destination(Base):
    """Para onde o relay repassa os eventos."""

    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    url: Mapped[str] = mapped_column(String(500))
    secret: Mapped[str] = mapped_column(String(128))
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_event_external"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(100))
    event_type: Mapped[str | None] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source: Mapped[Source] = relationship()
    deliveries: Mapped[list["Delivery"]] = relationship(back_populates="event")


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (UniqueConstraint("event_id", "destination_id", name="uq_delivery"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id"))
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, native_enum=False), default=DeliveryStatus.pending, index=True
    )
    attempts: Mapped[int] = mapped_column(default=0)
    last_status_code: Mapped[int | None]
    last_error: Mapped[str | None] = mapped_column(Text)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    event: Mapped[Event] = relationship(back_populates="deliveries")
    destination: Mapped[Destination] = relationship()
