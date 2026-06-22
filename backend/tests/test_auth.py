import pytest
from fastapi import HTTPException
from supabase_auth.errors import AuthApiError

import auth
import config


class FakeUser:
    def __init__(self, id, email):
        self.id = id
        self.email = email


class FakeUserResponse:
    def __init__(self, user):
        self.user = user


class FakeAuth:
    def __init__(self, user_response, raise_error=False):
        self._user_response = user_response
        self._raise_error = raise_error

    def get_user(self, token):
        if self._raise_error:
            raise AuthApiError("invalid token", status=401, code="invalid_token")
        return self._user_response


class FakeSupabaseClient:
    def __init__(self, user_response, raise_error=False):
        self.auth = FakeAuth(user_response, raise_error)


def test_get_current_user_allows_allowlisted_email(monkeypatch):
    fake_client = FakeSupabaseClient(FakeUserResponse(FakeUser("user-123", "allowed@example.com")))
    monkeypatch.setattr(auth.db, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(config, "ALLOWED_EMAILS", ["allowed@example.com"])

    user_id = auth.get_current_user(authorization="Bearer valid-token")

    assert user_id == "user-123"


def test_get_current_user_rejects_non_allowlisted_email(monkeypatch):
    fake_client = FakeSupabaseClient(FakeUserResponse(FakeUser("user-456", "stranger@example.com")))
    monkeypatch.setattr(auth.db, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(config, "ALLOWED_EMAILS", ["allowed@example.com"])

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization="Bearer valid-token")

    assert exc_info.value.status_code == 403


def test_get_current_user_rejects_invalid_token(monkeypatch):
    fake_client = FakeSupabaseClient(None, raise_error=True)
    monkeypatch.setattr(auth.db, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(config, "ALLOWED_EMAILS", ["allowed@example.com"])

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization="Bearer bad-token")

    assert exc_info.value.status_code == 401


def test_get_current_user_rejects_malformed_header():
    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(authorization="not-a-bearer-token")

    assert exc_info.value.status_code == 401
