"""
Regression tests for the /v1/risk-score "Invalid or expired token" bug.

Root cause (two parts):
  1. script.js sends `Authorization: Bearer demo-api-key-lexara` — a hardcoded
     non-JWT string — for ALL landing-page demo calls. decode_token tries to
     parse it as JWT, fails with JWTError, and returns the misleading
     "Invalid or expired token" error (implying the token was once valid but
     expired, when actually it was never a JWT at all).

  2. decode_token catches ALL JWTError subtypes under one generic message.
     A genuinely expired JWT and a totally invalid token produce the exact same
     "Invalid or expired token" response, making it impossible for the client
     to know whether to silently refresh vs. show a credentials-error.

These tests fail BEFORE the fix and pass AFTER.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from jose import jwt as jose_jwt

from tests.conftest import SAMPLE_CONTRACT


JWT_SECRET = "test-jwt-secret-e2e-1234567890"
JWT_ALG    = "HS256"


def _make_token(payload: dict) -> str:
    return jose_jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _expired_token() -> str:
    return _make_token({
        "sub": "some_user",
        "role": "procurement",
        "exp": datetime.utcnow() - timedelta(hours=2),  # expired 2 h ago
    })


def _non_jwt_api_key() -> str:
    return "demo-api-key-lexara"  # exactly what script.js sends


# ─── 1. Non-JWT token (the demo-key bug) ──────────────────────────────────────


class TestNonJWTTokenOnRiskScore:
    """
    script.js sends `Authorization: Bearer demo-api-key-lexara`.
    This is not a JWT: the backend should return 401 with a clear
    "Invalid authentication token" message — NOT "Invalid or expired token"
    (which falsely implies the user had a session that timed out).
    """

    def test_non_jwt_key_returns_401(self, client):
        resp = client.post(
            "/v1/risk-score",
            headers={"Authorization": f"Bearer {_non_jwt_api_key()}"},
            json={"text": SAMPLE_CONTRACT},
        )
        assert resp.status_code == 401

    def test_non_jwt_key_does_not_say_expired(self, client):
        """
        'expired' in the error implies the user had a valid session.
        A garbage API key should say 'Invalid authentication token'.

        FAILS before fix: returns "Invalid or expired token" which contains 'expired'.
        """
        resp = client.post(
            "/v1/risk-score",
            headers={"Authorization": f"Bearer {_non_jwt_api_key()}"},
            json={"text": SAMPLE_CONTRACT},
        )
        detail = resp.json().get("detail", "")
        assert "expired" not in detail.lower(), (
            f"Non-JWT key should not produce 'expired' in detail. Got: {detail!r}\n"
            f"This misleads the user into thinking they had a valid session that timed out."
        )

    def test_non_jwt_key_detail_message(self, client):
        """
        FAILS before fix: detail is "Invalid or expired token".
        PASSES after fix: detail is "Invalid authentication token".
        """
        resp = client.post(
            "/v1/risk-score",
            headers={"Authorization": f"Bearer {_non_jwt_api_key()}"},
            json={"text": SAMPLE_CONTRACT},
        )
        assert resp.status_code == 401
        detail = resp.json().get("detail", "")
        assert detail == "Invalid authentication token", (
            f"Expected 'Invalid authentication token', got {detail!r}"
        )


# ─── 2. Expired JWT token ─────────────────────────────────────────────────────


class TestExpiredTokenOnRiskScore:
    """
    When a user's JWT expires (default was 60 min — too short for legal work),
    the error should clearly say 'Token has expired. Please log in again.'
    so the frontend can redirect to login rather than showing a generic error.

    FAILS before fix: both expired JWTs and invalid tokens return
    "Invalid or expired token" making them indistinguishable.
    """

    def test_expired_token_returns_401(self, client):
        resp = client.post(
            "/v1/risk-score",
            headers={"Authorization": f"Bearer {_expired_token()}"},
            json={"text": SAMPLE_CONTRACT},
        )
        assert resp.status_code == 401

    def test_expired_token_detail_message(self, client):
        """
        FAILS before fix: detail is "Invalid or expired token".
        PASSES after fix: detail is "Token has expired. Please log in again."
        """
        resp = client.post(
            "/v1/risk-score",
            headers={"Authorization": f"Bearer {_expired_token()}"},
            json={"text": SAMPLE_CONTRACT},
        )
        assert resp.status_code == 401
        detail = resp.json().get("detail", "")
        assert detail == "Token has expired. Please log in again.", (
            f"Expected expiry-specific message, got {detail!r}"
        )

    def test_expired_token_returns_www_authenticate_header(self, client):
        """
        RFC 6750 requires WWW-Authenticate: Bearer on 401 responses.
        FAILS before fix: header is absent.
        """
        resp = client.post(
            "/v1/risk-score",
            headers={"Authorization": f"Bearer {_expired_token()}"},
            json={"text": SAMPLE_CONTRACT},
        )
        assert resp.status_code == 401
        assert "www-authenticate" in resp.headers, (
            "Missing WWW-Authenticate header — required by RFC 6750 for 401 Bearer responses"
        )


# ─── 3. Valid token still works ───────────────────────────────────────────────


class TestValidTokenStillWorks:
    """Regression guard: the fix must not break valid auth."""

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_fresh_jwt_returns_200(self, mock_claude, client, auth_headers):
        from tests.conftest import MOCK_RISK_SCORE_RESPONSE
        mock_claude.return_value = MOCK_RISK_SCORE_RESPONSE
        resp = client.post(
            "/v1/risk-score",
            headers=auth_headers,
            json={"text": SAMPLE_CONTRACT},
        )
        assert resp.status_code == 200, f"Valid token rejected: {resp.text}"
        assert "overall_risk_score" in resp.json()

    def test_expired_token_does_not_grant_access(self, client):
        resp = client.post(
            "/v1/risk-score",
            headers={"Authorization": f"Bearer {_expired_token()}"},
            json={"text": SAMPLE_CONTRACT},
        )
        assert resp.status_code == 401

    def test_tampered_token_rejected(self, client):
        """A token with invalid signature is rejected."""
        good_token = _make_token({"sub": "user", "role": "procurement",
                                  "exp": datetime.utcnow() + timedelta(hours=1)})
        # Tamper with the signature
        parts = good_token.split(".")
        tampered = parts[0] + "." + parts[1] + ".invalidsignature"
        resp = client.post(
            "/v1/risk-score",
            headers={"Authorization": f"Bearer {tampered}"},
            json={"text": SAMPLE_CONTRACT},
        )
        assert resp.status_code == 401

    @patch("app.routers.contracts.analyze_with_claude", new_callable=AsyncMock)
    def test_other_endpoints_unaffected(self, mock_claude, client, auth_headers):
        """Fix must not break /v1/summary or /v1/key-risks."""
        from tests.conftest import MOCK_SUMMARY_RESPONSE, MOCK_KEY_RISKS_RESPONSE
        mock_claude.return_value = MOCK_SUMMARY_RESPONSE
        r1 = client.post("/v1/summary", headers=auth_headers,
                         json={"text": SAMPLE_CONTRACT})
        mock_claude.return_value = MOCK_KEY_RISKS_RESPONSE
        r2 = client.post("/v1/key-risks", headers=auth_headers,
                         json={"text": SAMPLE_CONTRACT})
        assert r1.status_code == 200, f"/v1/summary broken: {r1.text}"
        assert r2.status_code == 200, f"/v1/key-risks broken: {r2.text}"
