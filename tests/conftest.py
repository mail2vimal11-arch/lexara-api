"""
Shared fixtures for E2E tests.
Uses FastAPI TestClient with SQLite in-memory DB and mocked external services.
"""

import os
import sys
import uuid

# Set required env vars BEFORE any app imports (Settings is evaluated at import time)
os.environ["CLAUDE_API_KEY"] = "test-key-for-e2e"
os.environ["RECEIPTS_API_KEY"] = "test-receipts-key"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake_key_for_e2e"
os.environ["STRIPE_PUBLISHABLE_KEY"] = "pk_test_fake_key_for_e2e"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_fake_for_e2e"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-jwt-secret-e2e-1234567890"
os.environ["SECRET_KEY"] = "test-secret-key-e2e"
os.environ["DEBUG"] = "false"

from unittest.mock import MagicMock
import pytest
import numpy as np
import sqlalchemy as _sa
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

# ── Monkey-patch create_engine to handle SQLite ──────────────────────────────
# app.database.session calls create_engine() at module level with pool_size and
# max_overflow, which SQLite does not support. We wrap it to strip those params.

_original_create_engine = _sa.create_engine


def _patched_create_engine(url, **kwargs):
    if str(url).startswith("sqlite"):
        kwargs.pop("pool_size", None)
        kwargs.pop("max_overflow", None)
        kwargs.pop("pool_pre_ping", None)
        # Use StaticPool so all connections share the same in-memory DB
        from sqlalchemy.pool import StaticPool
        kwargs["poolclass"] = StaticPool
        kwargs["connect_args"] = {"check_same_thread": False}
    return _original_create_engine(url, **kwargs)


_sa.create_engine = _patched_create_engine

# Stub out heavy ML modules before any app import pulls them in
_mock_faiss = MagicMock()
_mock_faiss_index = MagicMock()
_mock_faiss_index.ntotal = 0  # Empty index returns int, not MagicMock
_mock_faiss.IndexFlatL2.return_value = _mock_faiss_index
sys.modules["faiss"] = _mock_faiss
sys.modules["sentence_transformers"] = MagicMock()

# Patch embed_text early — the module will be imported by the app
import app.nlp.embeddings as _emb_mod  # noqa: E402


def _fake_embed_text(text):
    np.random.seed(hash(text) % 2**32)
    return np.random.rand(384).astype("float32")


_emb_mod._get_model = MagicMock()
_emb_mod.embed_text = _fake_embed_text
_emb_mod.cosine_similarity = lambda a, b: float(
    np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
)

# Now safe to import the app
from app.database.session import Base, get_db, engine as app_engine  # noqa: E402
from app.main import app  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

# Restore original create_engine for any later usage
_sa.create_engine = _original_create_engine


# ── DB fixture setup ─────────────────────────────────────────────────────────

@event.listens_for(app_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_TestSessionLocal = sessionmaker(bind=app_engine, autocommit=False, autoflush=False)


def _override_get_db():
    db = _TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


# ── Sample data ──────────────────────────────────────────────────────────────

SAMPLE_CONTRACT = """
MASTER SERVICES AGREEMENT

This Master Services Agreement ("Agreement") is entered into as of January 1, 2025
("Effective Date") by and between Acme Corp., a corporation organized under the
laws of Ontario, Canada ("Client"), and TechVendor Inc., a corporation organized
under the laws of British Columbia, Canada ("Service Provider").

1. SERVICES
The Service Provider agrees to provide software development and IT consulting
services ("Services") as described in each Statement of Work ("SOW") executed
pursuant to this Agreement. Each SOW shall specify the scope, deliverables,
timeline, and fees for the particular engagement.

2. TERM AND TERMINATION
This Agreement shall commence on the Effective Date and continue for a period
of two (2) years ("Initial Term"), unless earlier terminated. Either party may
terminate this Agreement upon sixty (60) days written notice. In the event of a
material breach, the non-breaching party may terminate upon thirty (30) days
written notice if the breach remains uncured.

3. FEES AND PAYMENT
Client shall pay Service Provider the fees set forth in each SOW. Payment shall
be due within thirty (30) days of receipt of invoice. Late payments shall accrue
interest at the rate of 1.5% per month or the maximum rate permitted by law,
whichever is less.

4. CONFIDENTIALITY
Each party agrees to maintain the confidentiality of all proprietary information
disclosed by the other party during the term of this Agreement. Confidential
information shall not include information that: (a) is or becomes publicly
available; (b) was known to the receiving party prior to disclosure; (c) is
independently developed by the receiving party; or (d) is disclosed pursuant
to a court order.

5. INTELLECTUAL PROPERTY
All intellectual property developed by Service Provider specifically for Client
under this Agreement ("Work Product") shall be the exclusive property of Client
upon full payment. Service Provider retains ownership of all pre-existing
intellectual property, tools, and methodologies.

6. LIABILITY
Neither party shall be liable for any indirect, incidental, special, or
consequential damages arising out of this Agreement. The total aggregate liability
of either party shall not exceed the fees paid or payable under this Agreement
during the twelve (12) month period preceding the claim.

7. GOVERNING LAW
This Agreement shall be governed by and construed in accordance with the laws of
the Province of Ontario and the federal laws of Canada applicable therein.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the Effective Date.
"""

SAMPLE_CLAUSE_TEXT = (
    "The Contractor shall indemnify and hold harmless the Crown from and against "
    "all claims, losses, damages, costs, expenses, and liabilities arising out of "
    "or in connection with the performance or non-performance of the Work."
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once before tests, drop after."""
    from app.models import user, clause, tender, audit  # noqa: F401
    Base.metadata.create_all(bind=app_engine)
    yield
    Base.metadata.drop_all(bind=app_engine)


@pytest.fixture(scope="session")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="session")
def test_user_credentials():
    uid = uuid.uuid4().hex[:8]
    return {
        "username": f"e2etest_{uid}",
        "email": f"e2etest_{uid}@lexara-test.dev",
        "password": "TestPass!2025secure",
        "role": "procurement",
    }


@pytest.fixture(scope="session")
def auth_token(client, test_user_credentials):
    """Register a test user and return the JWT access token."""
    resp = client.post("/v1/auth/register", json=test_user_credentials)
    assert resp.status_code in (200, 400), f"Register: {resp.status_code} {resp.text}"

    resp = client.post("/v1/auth/login", json={
        "username": test_user_credentials["username"],
        "password": test_user_credentials["password"],
    })
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert "access_token" in data
    return data["access_token"]


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ── Mock Claude API responses ────────────────────────────────────────────────

MOCK_SUMMARY_RESPONSE = {
    "summary": "This is a standard Master Services Agreement between Acme Corp and TechVendor Inc for software development and IT consulting services under Ontario law.",
    "contract_type": "service_agreement",
    "jurisdiction": "ON",
    "confidence": 0.92,
    "tokens_used": 150,
}

MOCK_RISK_SCORE_RESPONSE = {
    "overall_risk_score": 45,
    "risk_level": "medium",
    "scores_by_category": {
        "liability": 50,
        "data_protection": 60,
        "termination": 30,
        "ip_ownership": 40,
        "warranty": 55,
    },
    "interpretation": "Moderate risk due to broad liability limitation and lack of data protection clause.",
    "tokens_used": 180,
}

MOCK_KEY_RISKS_RESPONSE = {
    "key_risks": [
        {
            "severity": "high",
            "title": "Broad Liability Limitation",
            "description": "The liability cap is broad and may not adequately protect either party.",
            "section": "Section 6",
            "recommendation": "Consider adding carve-outs for gross negligence and wilful misconduct.",
        },
        {
            "severity": "medium",
            "title": "No Data Protection Clause",
            "description": "Agreement lacks provisions for handling personal data under PIPEDA.",
            "section": None,
            "recommendation": "Add a privacy and data protection schedule.",
        },
    ],
    "tokens_used": 200,
}

MOCK_MISSING_CLAUSES_RESPONSE = {
    "missing_clauses": [
        {
            "clause": "Force Majeure",
            "importance": "high",
            "rationale": "No provision for unforeseeable events that could prevent performance.",
        },
        {
            "clause": "Dispute Resolution",
            "importance": "medium",
            "rationale": "No alternative dispute resolution mechanism before litigation.",
        },
    ],
    "tokens_used": 160,
}

MOCK_EXTRACT_CLAUSES_RESPONSE = {
    "clauses": [
        {
            "type": "termination",
            "section": "Section 2",
            "summary": "Either party may terminate with 60 days notice or 30 days for material breach.",
            "confidence": 0.95,
        },
        {
            "type": "liability",
            "section": "Section 6",
            "summary": "Excludes indirect damages and caps aggregate liability at 12 months of fees.",
            "confidence": 0.93,
        },
    ],
    "tokens_used": 170,
}
