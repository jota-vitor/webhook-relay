import pytest

from app.backoff import is_retryable, next_delay


def test_ceiling_doubles_each_attempt():
    always_max = lambda: 1.0  # noqa: E731
    delays = [next_delay(n, rng=always_max) for n in range(1, 5)]
    assert delays == [4.0, 8.0, 16.0, 32.0]


def test_delay_never_passes_the_cap():
    assert next_delay(30, cap_seconds=3600, rng=lambda: 1.0) == 3600


def test_delay_has_a_minimum():
    assert next_delay(1, rng=lambda: 0.0) == 1.0


def test_jitter_spreads_values():
    values = {round(next_delay(6), 3) for _ in range(50)}
    assert len(values) > 40
    assert all(1.0 <= v <= 128.0 for v in values)


@pytest.mark.parametrize(
    ("status", "expected"),
    [(None, True), (500, True), (503, True), (429, True), (408, True), (400, False), (404, False)],
)
def test_retryable_status(status, expected):
    assert is_retryable(status) is expected
