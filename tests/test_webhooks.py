import json
import time

from app.signatures import sign


def test_signed_webhook_is_stored_and_queued(client, setup, queue):
    response = setup["send"]({"type": "payment.paid", "amount": 1990})

    assert response.status_code == 202
    body = response.json()
    assert body["duplicate"] is False
    assert body["deliveries"] == 1
    assert len(queue.ready) == 1

    event = client.get(f"/events/{body['event_id']}").json()
    assert event["event_type"] == "payment.paid"
    assert event["payload"]["amount"] == 1990
    assert event["deliveries"][0]["status"] == "pending"


def test_wrong_signature_returns_401(setup, queue):
    response = setup["send"]({"type": "x"}, secret="segredo-falso")
    assert response.status_code == 401
    assert len(queue.ready) == 0


def test_expired_signature_returns_401(client, setup):
    body = b'{"type":"x"}'
    old = sign(setup["source"]["secret"], body, timestamp=int(time.time()) - 3600)
    response = client.post("/webhooks/pagamentos", content=body, headers={"X-Signature": old})
    assert response.status_code == 401


def test_unknown_source_returns_404(client):
    response = client.post("/webhooks/nao-existe", content=b"{}", headers={"X-Signature": "x"})
    assert response.status_code == 404


def test_invalid_json_returns_400(client, setup):
    body = b"isto nao e json"
    headers = {"X-Signature": sign(setup["source"]["secret"], body)}
    assert client.post("/webhooks/pagamentos", content=body, headers=headers).status_code == 400


def test_duplicate_event_id_is_ignored(setup, queue):
    first = setup["send"]({"type": "a"}, headers={"X-Event-Id": "evt_123"})
    second = setup["send"]({"type": "a"}, headers={"X-Event-Id": "evt_123"})

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["event_id"] == first.json()["event_id"]
    assert len(queue.ready) == 1


def test_inactive_destination_gets_nothing(client, setup, queue):
    client.patch(f"/destinations/{setup['destination']['id']}", json={"active": False})
    response = setup["send"]({"type": "a"})
    assert response.json()["deliveries"] == 0
    assert len(queue.ready) == 0


def test_secrets_are_not_listed(client, setup):
    assert "secret" not in client.get("/sources").json()[0]
    assert "secret" not in client.get("/destinations").json()[0]


def test_event_type_falls_back_to_payload(client, setup):
    response = setup["send"]({"type": "order.created"})
    event = client.get(f"/events/{response.json()['event_id']}").json()
    assert event["event_type"] == "order.created"
    assert json.dumps(event["payload"]) == '{"type": "order.created"}'
