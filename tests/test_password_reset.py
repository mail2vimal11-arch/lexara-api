"""Password reset flow — /v1/auth/forgot-password and /v1/auth/reset-password."""

import re
import uuid

import pytest


@pytest.fixture
def reset_user(client):
    creds = {
        "username": f"resetuser_{uuid.uuid4().hex[:8]}",
        "email": f"reset_{uuid.uuid4().hex[:8]}@example.com",
        "password": "OldPassw0rd!",
    }
    r = client.post("/v1/auth/register", json=creds)
    assert r.status_code == 200
    return creds


def _request_reset_token(client, email, monkeypatch):
    """Trigger forgot-password and capture the emailed reset link's token."""
    captured = {}

    def fake_send(to, subject, body):
        captured["to"], captured["body"] = to, body
        return True

    monkeypatch.setattr("app.routers.auth_routes.send_email", fake_send)
    r = client.post("/v1/auth/forgot-password", json={"email": email})
    assert r.status_code == 200
    m = re.search(r"reset_token=(\S+)", captured["body"])
    assert m, "reset link missing from email body"
    return m.group(1)


class TestForgotPassword:
    def test_unknown_email_gets_same_generic_answer(self, client):
        r = client.post("/v1/auth/forgot-password",
                        json={"email": "nobody@example.com"})
        assert r.status_code == 200
        assert "reset link" in r.json()["message"]

    def test_known_email_sends_link_to_that_address(self, client, reset_user, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            "app.routers.auth_routes.send_email",
            lambda to, subject, body: captured.update(to=to) or True)
        r = client.post("/v1/auth/forgot-password", json={"email": reset_user["email"]})
        assert r.status_code == 200
        assert captured["to"] == reset_user["email"]


class TestResetPassword:
    def test_full_flow_old_password_dies_new_password_works(
            self, client, reset_user, monkeypatch):
        token = _request_reset_token(client, reset_user["email"], monkeypatch)

        r = client.post("/v1/auth/reset-password",
                        json={"token": token, "new_password": "NewPassw0rd!"})
        assert r.status_code == 200

        old = client.post("/v1/auth/login", json={
            "username": reset_user["username"], "password": reset_user["password"]})
        assert old.status_code == 401
        new = client.post("/v1/auth/login", json={
            "username": reset_user["username"], "password": "NewPassw0rd!"})
        assert new.status_code == 200
        assert "access_token" in new.json()

    def test_token_is_single_use(self, client, reset_user, monkeypatch):
        token = _request_reset_token(client, reset_user["email"], monkeypatch)
        first = client.post("/v1/auth/reset-password",
                            json={"token": token, "new_password": "NewPassw0rd!"})
        assert first.status_code == 200
        replay = client.post("/v1/auth/reset-password",
                             json={"token": token, "new_password": "Hacked123!"})
        assert replay.status_code == 400

    def test_garbage_token_rejected(self, client):
        r = client.post("/v1/auth/reset-password",
                        json={"token": "not-a-jwt", "new_password": "Whatever1!"})
        assert r.status_code == 400

    def test_login_jwt_cannot_reset_password(self, client, reset_user):
        login = client.post("/v1/auth/login", json={
            "username": reset_user["username"], "password": reset_user["password"]})
        access_token = login.json()["access_token"]
        r = client.post("/v1/auth/reset-password",
                        json={"token": access_token, "new_password": "Sneaky123!"})
        assert r.status_code == 400  # wrong purpose claim

    def test_short_password_rejected(self, client, reset_user, monkeypatch):
        token = _request_reset_token(client, reset_user["email"], monkeypatch)
        r = client.post("/v1/auth/reset-password",
                        json={"token": token, "new_password": "short"})
        assert r.status_code == 400
