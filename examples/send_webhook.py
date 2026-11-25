"""Envia um webhook assinado para o relay, como um provedor externo faria.

Uso:
    python examples/send_webhook.py --source pagamentos --secret <segredo-da-origem>
"""

import argparse
import json
import sys
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.signatures import sign  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--source", required=True)
    parser.add_argument("--secret", required=True)
    args = parser.parse_args()

    body = json.dumps({"type": "payment.paid", "order_id": 42, "amount_cents": 1990}).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Signature": sign(args.secret, body),
        "X-Event-Id": f"evt_{uuid.uuid4().hex[:12]}",
    }
    response = httpx.post(f"{args.url}/webhooks/{args.source}", content=body, headers=headers)
    print(response.status_code, response.json())


if __name__ == "__main__":
    main()
