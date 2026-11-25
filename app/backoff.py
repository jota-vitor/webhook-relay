import random
from collections.abc import Callable


def next_delay(
    attempt: int,
    base_seconds: float = 2.0,
    cap_seconds: float = 3600.0,
    min_seconds: float = 1.0,
    rng: Callable[[], float] = random.random,
) -> float:
    """Backoff exponencial com "full jitter".

    O teto dobra a cada tentativa (2s, 4s, 8s, ... até 1h) e a espera real é
    sorteada entre 0 e esse teto. O sorteio espalha os reenvios: se um destino
    cair e voltar, ele não recebe todas as entregas atrasadas no mesmo segundo.
    """
    ceiling = min(cap_seconds, base_seconds * (2**attempt))
    return max(min_seconds, rng() * ceiling)


def is_retryable(status_code: int | None) -> bool:
    """Erro de rede (None), 5xx, 408 e 429 valem nova tentativa. Outros 4xx não."""
    if status_code is None:
        return True
    return status_code >= 500 or status_code in (408, 429)
