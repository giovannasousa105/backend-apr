from invite_utils import (
    build_invite_link,
    generate_invite_token,
    hash_invite_token,
    mask_email,
)


def test_hash_invite_token_is_deterministic():
    token = "token-123"
    assert hash_invite_token(token) == hash_invite_token(token)


def test_generate_invite_token_not_empty():
    token = generate_invite_token()
    assert isinstance(token, str)
    assert len(token) >= 20


def test_mask_email():
    assert mask_email("abc@example.com").startswith("ab")
    assert mask_email("x@example.com").startswith("x")


def test_build_invite_link_contains_token():
    token = "abc123"
    link = build_invite_link(token)
    assert "token=abc123" in link
