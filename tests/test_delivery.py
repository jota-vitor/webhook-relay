import httpx

from app.delivery import process_delivery
from app.models import Delivery, DeliveryStatus
from app.signatures import verify


class FakeSender:
    """Simula o destino: devolve os status da lista, em ordem, e guarda o que recebeu."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, body, headers):
        self.calls.append({"url": url, "body": body, "headers": headers})
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def queued_delivery(setup, queue) -> int:
    setup["send"]({"type": "payment.paid"})
    return queue.pop()


def test_successful_delivery(setup, queue, db):
    delivery_id = queued_delivery(setup, queue)
    sender = FakeSender(200)

    status = process_delivery(db, delivery_id, queue, sender)

    assert status == DeliveryStatus.succeeded
    assert db.get(Delivery, delivery_id).attempts == 1
    assert sender.calls[0]["url"] == "https://loja.example/hooks"


def test_destination_can_verify_the_signature(setup, queue, db):
    delivery_id = queued_delivery(setup, queue)
    sender = FakeSender(200)
    process_delivery(db, delivery_id, queue, sender)

    call = sender.calls[0]
    verify(setup["destination"]["secret"], call["body"], call["headers"]["X-Relay-Signature"])


def test_server_error_schedules_a_retry(setup, queue, db):
    delivery_id = queued_delivery(setup, queue)

    status = process_delivery(db, delivery_id, queue, FakeSender(503), now=1_000)

    assert status == DeliveryStatus.pending
    run_at, scheduled_id = queue.delayed[0]
    assert scheduled_id == delivery_id
    assert run_at > 1_000
    assert db.get(Delivery, delivery_id).last_error == "HTTP 503"


def test_network_error_is_retried(setup, queue, db):
    delivery_id = queued_delivery(setup, queue)
    sender = FakeSender(httpx.ConnectError("conexão recusada"))

    status = process_delivery(db, delivery_id, queue, sender)

    assert status == DeliveryStatus.pending
    assert "ConnectError" in db.get(Delivery, delivery_id).last_error


def test_client_error_is_not_retried(setup, queue, db):
    delivery_id = queued_delivery(setup, queue)
    status = process_delivery(db, delivery_id, queue, FakeSender(400))
    assert status == DeliveryStatus.dead
    assert queue.delayed == []


def test_gives_up_after_max_attempts(setup, queue, db):
    delivery_id = queued_delivery(setup, queue)
    sender = FakeSender(500, 500, 500)

    statuses = [process_delivery(db, delivery_id, queue, sender, max_attempts=3) for _ in range(3)]

    assert statuses == [DeliveryStatus.pending, DeliveryStatus.pending, DeliveryStatus.dead]


def test_retry_after_success_does_nothing(setup, queue, db):
    delivery_id = queued_delivery(setup, queue)
    process_delivery(db, delivery_id, queue, FakeSender(200))
    assert process_delivery(db, delivery_id, queue, FakeSender(200)) is None


def test_dead_delivery_can_be_retried_manually(client, setup, queue, db):
    delivery_id = queued_delivery(setup, queue)
    process_delivery(db, delivery_id, queue, FakeSender(400))

    assert [d["id"] for d in client.get("/deliveries").json()] == [delivery_id]

    response = client.post(f"/deliveries/{delivery_id}/retry")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert queue.pop() == delivery_id


def test_promote_due_moves_scheduled_items(queue):
    queue.schedule(7, run_at=100)
    queue.schedule(8, run_at=200)

    assert queue.promote_due(now=150) == 1
    assert queue.pop() == 7
    assert queue.pop() is None
