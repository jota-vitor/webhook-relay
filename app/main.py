from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import Base, engine
from app.routers import admin, events, webhooks


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Recebe webhooks assinados, guarda cada evento e repassa para vários destinos "
        "com novas tentativas automáticas."
    ),
    lifespan=lifespan,
)

app.include_router(webhooks.router)
app.include_router(events.router)
app.include_router(admin.router)


@app.get("/health", tags=["infra"])
def health():
    return {"status": "ok"}
