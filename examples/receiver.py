"""Destino de exemplo: um serviço que recebe os eventos repassados pelo relay.

Falha de propósito em parte das requisições para dar para ver as novas
tentativas acontecendo nos logs do worker.

    RELAY_SECRET=<segredo-do-destino> uvicorn examples.receiver:app --port 9000
"""

import os
import random
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.signatures import SignatureError, verify  # noqa: E402

app = FastAPI(title="Receptor de exemplo")
FAILURE_RATE = float(os.getenv("FAILURE_RATE", "0.3"))


@app.post("/hook")
async def hook(request: Request):
    body = await request.body()
    secret = os.getenv("RELAY_SECRET")
    if secret:
        try:
            verify(secret, body, request.headers.get("X-Relay-Signature"))
        except SignatureError as exc:
            raise HTTPException(401, str(exc)) from None

    if random.random() < FAILURE_RATE:
        raise HTTPException(503, "Instabilidade simulada")

    attempt = request.headers.get("X-Relay-Attempt")
    print(f"recebido na tentativa {attempt}: {body.decode()}")
    return {"ok": True}
