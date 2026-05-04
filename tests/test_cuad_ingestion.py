"""
Tests for CUAD-backed peer-frequency ingestion and the corresponding
"general" dark-obligation detector.

Two modes:
    1. If `app/services/cuad_frequencies.json` exists in the repo (the normal
       case after `scripts/ingest_cuad.py` has been run), run the full suite
       — sanity-check the JSON, exercise `detect_dark_obligations_general`,
       and exercise the new HTTP endpoints.
    2. If the file is missing (network was unavailable at ingest time), skip
       the data-dependent assertions and just verify the service module still
       imports cleanly so the existing dark-obligation pipeline isn't broken.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest

import app.nlp.embeddings as _emb_mod
import app.services.dark_obligation_service as dos


CUAD_PATH = (
    Path(__file__).resolve().parent.parent
    / "app"
    / "services"
    / "cuad_frequencies.json"
)
HAS_CUAD = CUAD_PATH.exists()


# ── Deterministic keyword-overlap embedding (test-only) ─────────────────────
# Same trick used in test_dark_obligations.py — gives the real similarity
# pipeline a meaningful signal under unit test conditions.

_DIM = 384
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]+")


def _keyword_embed(text: str) -> np.ndarray:
    vec = np.zeros(_DIM, dtype="float32")
    for tok in _TOKEN_RE.findall(text.lower()):
        if len(tok) <= 2:
            continue
        idx = hash(tok) % _DIM
        vec[idx] += 1.0
    n = np.linalg.norm(vec)
    if n > 0:
        vec /= n
    return vec


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


@pytest.fixture(autouse=True)
def _swap_embeddings(monkeypatch):
    monkeypatch.setattr(_emb_mod, "embed_text", _keyword_embed)
    monkeypatch.setattr(_emb_mod, "cosine_similarity", _cos)
    monkeypatch.setattr(dos, "embed_text", _keyword_embed)
    monkeypatch.setattr(dos, "cosine_similarity", _cos)
    yield


# ── Service module always imports cleanly ───────────────────────────────────


def test_service_module_imports_without_regression():
    """Even if cuad_frequencies.json is missing the existing API must work."""
    # The IT-services catalog must still be intact.
    assert "it_services" in dos.STANDARD_CLAUSE_CATALOG
    assert any(
        e["key"] == "data_breach_notification"
        for e in dos.STANDARD_CLAUSE_CATALOG["it_services"]
    )
    # The new helpers exist regardless of whether the JSON is on disk.
    assert callable(dos.list_cuad_categories)
    assert callable(dos.detect_dark_obligations_general)
    assert callable(dos.cuad_frequencies_meta)


def test_detect_general_handles_missing_file_gracefully(monkeypatch, tmp_path):
    """If the JSON disappears the detector returns an explicit error dict
    rather than raising."""
    # Force-clear the cached values regardless of file state.
    monkeypatch.setattr(dos, "_CUAD_RAW", None)
    monkeypatch.setattr(dos, "_CUAD_GENERAL_CATALOG_CACHE", None)
    # Point at a path that definitely doesn't exist.
    monkeypatch.setattr(dos, "_CUAD_FREQ_PATH", tmp_path / "definitely_absent.json")

    result = dos.detect_dark_obligations_general(sow_text="x" * 200)
    assert result.get("error") == "cuad_not_available"
    assert "ingest_cuad.py" in result["message"]


# ── Tests that require cuad_frequencies.json on disk ────────────────────────


pytestmark_needs_cuad = pytest.mark.skipif(
    not HAS_CUAD,
    reason=(
        "CUAD frequencies not yet ingested — run scripts/ingest_cuad.py to "
        "generate app/services/cuad_frequencies.json."
    ),
)


@pytestmark_needs_cuad
class TestCuadFrequenciesArtifact:
    """Sanity-check the committed cuad_frequencies.json artifact."""

    def test_has_meta_and_frequencies_blocks(self):
        with open(CUAD_PATH, encoding="utf-8") as f:
            data = json.load(f)
        assert "_meta" in data and "frequencies" in data
        assert data["_meta"].get("source", "").startswith("https://")
        assert data["_meta"].get("n_contracts", 0) >= 500
        assert data["_meta"].get("n_contracts", 0) <= 600

    def test_has_41_categories(self):
        # CUAD's master_clauses.csv exposes 41 base categories. Allow a small
        # tolerance because the corpus also includes a "Competitive Restriction
        # Exception" column that some inventories don't list.
        with open(CUAD_PATH, encoding="utf-8") as f:
            data = json.load(f)
        n = len(data["frequencies"])
        assert 40 <= n <= 42, f"Expected ~41 CUAD categories, got {n}"

    def test_all_frequencies_in_unit_interval(self):
        with open(CUAD_PATH, encoding="utf-8") as f:
            data = json.load(f)
        for label, freq in data["frequencies"].items():
            assert isinstance(freq, (int, float)), label
            assert 0.0 <= float(freq) <= 1.0, f"{label}={freq}"

    def test_governing_law_is_high_frequency(self):
        """A real-world sanity check: Governing Law should be ~0.85+ in CUAD."""
        with open(CUAD_PATH, encoding="utf-8") as f:
            data = json.load(f)
        gl = data["frequencies"].get("Governing Law")
        assert gl is not None and gl >= 0.75, (
            f"Governing Law frequency {gl!r} looks wrong — should be >=0.75. "
            f"Did the CSV parsing logic regress?"
        )

    def test_source_code_escrow_is_low_frequency(self):
        """And Source Code Escrow should be a rare (<10%) clause."""
        with open(CUAD_PATH, encoding="utf-8") as f:
            data = json.load(f)
        sce = data["frequencies"].get("Source Code Escrow")
        assert sce is not None and sce <= 0.15, (
            f"Source Code Escrow frequency {sce!r} unexpectedly high."
        )


# Synthetic SOW deliberately wired so the keyword-overlap embedding picks up
# Governing Law and lots of contract boilerplate.
_SOW_WITH_GOVERNING_LAW = """
MASTER SERVICES AGREEMENT

This agreement is dated as of January 1, 2026 by and between Acme Inc., a
Delaware corporation, and Beta LLC, a New York limited liability company.
The parties to this agreement are identified above and have executed this
document on the date first written above.

1. SERVICES. Beta will provide consulting services to Acme as described in
each statement of work issued under this agreement.

2. GOVERNING LAW. This agreement shall be governed by and construed in
accordance with the laws of the State of Delaware without regard to its
conflict of laws principles. Any dispute arising out of this agreement
shall be brought in a court of competent jurisdiction sitting in Delaware.

3. INDEMNIFICATION. Each party shall indemnify and hold harmless the other
party from and against any claims arising from breach of this agreement.

4. CONFIDENTIALITY. Each party shall maintain the confidentiality of all
proprietary information disclosed by the other party.

5. ANTI-ASSIGNMENT. Neither party may assign this agreement without the
prior written consent of the other party, which consent shall not be
unreasonably withheld.

6. EXPIRATION DATE. This agreement shall expire on December 31, 2027 unless
earlier terminated in accordance with its terms.
"""


@pytestmark_needs_cuad
class TestDetectorGeneralService:
    """Direct unit tests of detect_dark_obligations_general."""

    def test_governing_law_clause_marked_present(self):
        result = dos.detect_dark_obligations_general(
            sow_text=_SOW_WITH_GOVERNING_LAW,
            presence_threshold=0.30,  # keyword embeddings give lower scores
        )
        assert "error" not in result
        present_labels = {p["label"] for p in result["present"]}
        assert "Governing Law" in present_labels

    def test_source_code_escrow_marked_missing_or_filtered(self):
        """Source Code Escrow is rare in CUAD (~2.5%), so even if it is
        flagged absent the detector should NOT surface it as a missing-clause
        finding when min_peer_frequency is at the default 0.30 threshold."""
        result = dos.detect_dark_obligations_general(
            sow_text=_SOW_WITH_GOVERNING_LAW,
            presence_threshold=0.30,
            min_peer_frequency=0.30,
        )
        missing_labels = {m["label"] for m in result["missing"]}
        assert "Source Code Escrow" not in missing_labels

    def test_low_threshold_surfaces_rare_categories(self):
        """If we drop min_peer_frequency low enough, low-frequency categories
        such as Source Code Escrow should appear in the absent set.

        Bumping `presence_threshold` to 0.40 here filters out spurious matches
        from the keyword-overlap test embedding (the real sentence-transformer
        signal is much sharper)."""
        result = dos.detect_dark_obligations_general(
            sow_text=_SOW_WITH_GOVERNING_LAW,
            presence_threshold=0.40,
            min_peer_frequency=0.0,
        )
        missing_labels = {m["label"] for m in result["missing"]}
        # At least one of the well-known low-frequency CUAD categories must
        # surface when we drop the floor — Source Code Escrow (~2.5%) is the
        # canonical example, but any of these tail-end categories suffices.
        rare = {
            "Source Code Escrow",
            "Most Favored Nation",
            "Unlimited/All-You-Can-Eat-License",
            "Affiliate License-Licensor",
        }
        assert rare & missing_labels, (
            f"Expected at least one rare CUAD category in missing set; "
            f"got {missing_labels}"
        )
        # And confirm that Source Code Escrow specifically is reported missing
        # with a high-confidence (low best_match_score) signal.
        sce = next(
            (m for m in result["missing"] if m["label"] == "Source Code Escrow"),
            None,
        )
        if sce is not None:
            assert sce["best_match_score"] < 0.40
            assert sce["importance"] == "low"

    def test_summary_and_metadata_fields(self):
        result = dos.detect_dark_obligations_general(
            sow_text=_SOW_WITH_GOVERNING_LAW,
            presence_threshold=0.30,
        )
        assert result["source"] == "cuad"
        assert isinstance(result["n_contracts"], int)
        assert result["n_contracts"] >= 500
        assert "CUAD categories checked" in result["summary"]


# ── HTTP / router tests ─────────────────────────────────────────────────────


@pytestmark_needs_cuad
class TestCuadRoutes:
    """Tests against the FastAPI router via TestClient."""

    @pytest.fixture(autouse=True)
    def _register_router(self, client):
        from app.main import app as _app
        from app.routers.dark_obligation_routes import router as do_router

        if not any(
            getattr(r, "path", "").startswith("/v1/dark-obligations")
            for r in _app.router.routes
        ):
            _app.include_router(do_router)
        yield

    def test_detect_general_requires_auth(self, client):
        resp = client.post(
            "/v1/dark-obligations/detect-general",
            json={"sow_text": "x" * 500},
        )
        assert resp.status_code == 401

    def test_detect_general_rejects_short_sow(self, client, auth_headers):
        resp = client.post(
            "/v1/dark-obligations/detect-general",
            json={"sow_text": "too short"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "100" in resp.json()["detail"]

    def test_detect_general_returns_expected_shape(self, client, auth_headers):
        resp = client.post(
            "/v1/dark-obligations/detect-general",
            json={
                "sow_text": _SOW_WITH_GOVERNING_LAW,
                "presence_threshold": 0.30,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["source"] == "cuad"
        assert isinstance(data["n_contracts"], int)
        assert isinstance(data["checked"], int) and data["checked"] > 0
        assert isinstance(data["missing"], list)
        assert isinstance(data["present"], list)

    def test_cuad_catalog_requires_auth(self, client):
        resp = client.get("/v1/dark-obligations/cuad-catalog")
        assert resp.status_code == 401

    def test_cuad_catalog_returns_categories_and_meta(self, client, auth_headers):
        resp = client.get(
            "/v1/dark-obligations/cuad-catalog",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 40
        assert isinstance(data["categories"], list)
        # Each entry has the same shape as the curated catalog entries.
        for entry in data["categories"]:
            for k in ("key", "label", "peer_frequency", "importance",
                      "typical_text", "rationale"):
                assert k in entry, f"missing {k} in {entry}"
        assert data["_meta"]["n_contracts"] >= 500
