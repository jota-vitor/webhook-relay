"""Worker que entrega os eventos aos destinos.

Rode com:  python -m app.worker
Pode subir várias cópias em paralelo: cada entrega é retirada da fila por um só worker.
"""

import logging
import signal
import threading
import time

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.delivery import Sender, http_sender, process_delivery
from app.task_queue import DeliveryQueue, RedisQueue

logger = logging.getLogger("relay.worker")


def run(queue: DeliveryQueue, sender: Sender, stop: threading.Event) -> None:
    logger.info("Worker iniciado")
    while not stop.is_set():
        queue.promote_due(time.time())
        delivery_id = queue.pop(timeout=1)
        if delivery_id is None:
            continue

        with SessionLocal() as db:
            status = process_delivery(db, delivery_id, queue, sender, settings.max_attempts)
        if status is not None:
            logger.info("entrega %s -> %s", delivery_id, status.value)
    logger.info("Worker encerrado")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    Base.metadata.create_all(bind=engine)

    stop = threading.Event()
    # docker stop manda SIGTERM: termina a entrega atual e sai sem perder nada
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    run(RedisQueue(settings.redis_url), http_sender, stop)


if __name__ == "__main__":
    main()
