import secrets

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import DbSession
from app.models import Destination, Source
from app.schemas import (
    DestinationCreate,
    DestinationCreated,
    DestinationOut,
    DestinationUpdate,
    SourceCreate,
    SourceCreated,
    SourceOut,
)

router = APIRouter(tags=["admin"])


@router.post("/sources", response_model=SourceCreated, status_code=status.HTTP_201_CREATED)
def create_source(data: SourceCreate, db: DbSession):
    source = Source(name=data.name, secret=secrets.token_urlsafe(32))
    db.add(source)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Já existe uma origem com esse nome"
        ) from None
    db.refresh(source)
    return source


@router.get("/sources", response_model=list[SourceOut])
def list_sources(db: DbSession):
    return db.scalars(select(Source).order_by(Source.id)).all()


@router.post(
    "/destinations", response_model=DestinationCreated, status_code=status.HTTP_201_CREATED
)
def create_destination(data: DestinationCreate, db: DbSession):
    destination = Destination(name=data.name, url=str(data.url), secret=secrets.token_urlsafe(32))
    db.add(destination)
    db.commit()
    db.refresh(destination)
    return destination


@router.get("/destinations", response_model=list[DestinationOut])
def list_destinations(db: DbSession):
    return db.scalars(select(Destination).order_by(Destination.id)).all()


@router.patch("/destinations/{destination_id}", response_model=DestinationOut)
def update_destination(destination_id: int, data: DestinationUpdate, db: DbSession):
    destination = db.get(Destination, destination_id)
    if destination is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Destino não encontrado")
    destination.active = data.active
    db.commit()
    db.refresh(destination)
    return destination
