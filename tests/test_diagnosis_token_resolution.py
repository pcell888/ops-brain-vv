from __future__ import annotations

from src.api.token_sync import normalize_token_header, resolve_biz_auth_token


def test_normalize_token_header_trims_and_ignores_blank() -> None:
    assert normalize_token_header("  abc  ") == "abc"
    assert normalize_token_header("   ") is None
    assert normalize_token_header(None) is None


def test_resolve_biz_auth_token_prefers_token_header() -> None:
    assert resolve_biz_auth_token("header-token", "body-token") == "header-token"
    assert resolve_biz_auth_token("  ", "body-token") == "body-token"
    assert resolve_biz_auth_token(None, " body-token ") == "body-token"
