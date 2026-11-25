"""Assinatura HMAC-SHA256 no formato `t=<timestamp>,v1=<hex>`.

O timestamp entra na mensagem assinada. Assim, alguém que capture uma
requisição válida não consegue reenviá-la depois da janela de tolerância
(proteção contra replay).
"""

import hashlib
import hmac
import time


class SignatureError(Exception):
    pass


def _digest(secret: str, body: bytes, timestamp: int) -> str:
    message = f"{timestamp}.".encode() + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def sign(secret: str, body: bytes, timestamp: int | None = None) -> str:
    timestamp = int(time.time()) if timestamp is None else timestamp
    return f"t={timestamp},v1={_digest(secret, body, timestamp)}"


def verify(
    secret: str,
    body: bytes,
    header: str | None,
    tolerance_seconds: int = 300,
    now: int | None = None,
) -> None:
    if not header:
        raise SignatureError("Assinatura ausente")

    parts = dict(item.split("=", 1) for item in header.split(",") if "=" in item)
    try:
        timestamp = int(parts["t"])
        received = parts["v1"]
    except (KeyError, ValueError):
        raise SignatureError("Formato de assinatura inválido") from None

    now = int(time.time()) if now is None else now
    if abs(now - timestamp) > tolerance_seconds:
        raise SignatureError("Assinatura fora da janela de tempo")

    # compare_digest leva o mesmo tempo acerte ou erre: não vaza informação por timing
    if not hmac.compare_digest(_digest(secret, body, timestamp), received):
        raise SignatureError("Assinatura inválida")
