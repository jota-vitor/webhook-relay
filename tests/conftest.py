import json
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.signatures import sign  # noqa: E402
from app.task_queue import MemoryQueue, get_queue  # noqa: E402


@pytest.fixture
def queue():
    return MemoryQueue()


@pytest.fixture
def client(queue):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    app.dependency_overrides[get_queue] = lambda: queue
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def setup(client):
    """Cria uma origem e um destino e devolve uma função que envia webhooks assinados."""
    source = client.post("/sources", json={"name": "pagamentos"}).json()
    destination = client.post(
        "/destinations", json={"name": "loja", "url": "https://loja.example/hooks"}
    ).json()

    def send(payload: dict, headers: dict | None = None, secret: str | None = None):
        body = json.dumps(payload).encode()
        all_headers = {
            "Content-Type": "application/json",
            "X-Signature": sign(secret or source["secret"], body),
            **(headers or {}),
        }
        return client.post("/webhooks/pagamentos", content=body, headers=all_headers)

    return {"source": source, "destination": destination, "send": send}
