import pytest

from app.signatures import SignatureError, sign, verify

SECRET = "segredo-de-teste"
BODY = b'{"type":"payment.paid","amount":1990}'


def test_valid_signature():
    header = sign(SECRET, BODY, timestamp=1_700_000_000)
    verify(SECRET, BODY, header, now=1_700_000_010)


def test_tampered_body_is_rejected():
    header = sign(SECRET, BODY, timestamp=1_700_000_000)
    with pytest.raises(SignatureError, match="inválida"):
        verify(SECRET, BODY.replace(b"1990", b"9990"), header, now=1_700_000_000)


def test_wrong_secret_is_rejected():
    header = sign("outro-segredo", BODY, timestamp=1_700_000_000)
    with pytest.raises(SignatureError):
        verify(SECRET, BODY, header, now=1_700_000_000)


def test_old_signature_is_rejected_to_prevent_replay():
    header = sign(SECRET, BODY, timestamp=1_700_000_000)
    with pytest.raises(SignatureError, match="janela"):
        verify(SECRET, BODY, header, tolerance_seconds=300, now=1_700_000_301)


def test_changing_timestamp_breaks_signature():
    header = sign(SECRET, BODY, timestamp=1_700_000_000)
    forged = header.replace("t=1700000000", "t=1700000100")
    with pytest.raises(SignatureError):
        verify(SECRET, BODY, forged, now=1_700_000_100)


@pytest.mark.parametrize("header", [None, "", "lixo", "t=abc,v1=123", "v1=abc"])
def test_malformed_headers(header):
    with pytest.raises(SignatureError):
        verify(SECRET, BODY, header)
