from src.api.security import decode_token, hash_password, verify_password


def test_decode_invalid_token():
    assert decode_token("not-a-valid-jwt") is None


def test_verify_password_roundtrip():
    h = hash_password("secret123")
    assert verify_password("secret123", h)
    assert not verify_password("wrong", h)
