from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models import DeliveryStatus

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


class SourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9-]+$")


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class SourceCreated(SourceOut):
    secret: str = Field(description="Mostrado só agora. Use para assinar os webhooks enviados.")


class DestinationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    url: HttpUrl


class DestinationUpdate(BaseModel):
    active: bool


class DestinationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    active: bool
    created_at: datetime


class DestinationCreated(DestinationOut):
    secret: str = Field(description="Mostrado só agora. Use para verificar X-Relay-Signature.")


class WebhookAccepted(BaseModel):
    event_id: str
    duplicate: bool
    deliveries: int


class DeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    destination_id: int
    status: DeliveryStatus
    attempts: int
    last_status_code: int | None
    last_error: str | None
    next_attempt_at: datetime | None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: int
    external_id: str | None
    event_type: str | None
    received_at: datetime


class EventDetail(EventOut):
    payload: dict[str, Any]
    deliveries: list[DeliveryOut]
