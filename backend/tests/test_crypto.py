import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.core.crypto import SessionCipher


@pytest.fixture
def cipher() -> SessionCipher:
    return SessionCipher(Fernet.generate_key().decode())


def test_decrypts_what_it_encrypted(cipher) -> None:
    token = cipher.encrypt("session-value")

    assert token != "session-value"
    assert cipher.decrypt(token) == "session-value"


def test_other_key_cannot_decrypt(cipher) -> None:
    token = cipher.encrypt("session-value")
    other = SessionCipher(Fernet.generate_key().decode())

    with pytest.raises(InvalidToken):
        other.decrypt(token)


def test_rejects_invalid_key() -> None:
    with pytest.raises(ValueError):
        SessionCipher("not-a-fernet-key")
