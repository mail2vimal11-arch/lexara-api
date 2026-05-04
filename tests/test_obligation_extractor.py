"""
Unit tests for the obligation_extractor service.

The LLM call is mocked — these tests exercise the prompt-building, JSON
parsing, and per-entry validation logic. Real network calls never happen.
"""

import asyncio
import json

import pytest

from app.services import obligation_extractor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _patch_llm(monkeypatch, response):
    """Patch analyze_with_claude on the llm_service module so the extractor's
    lazy `from app.services.llm_service import analyze_with_claude` picks up
    the stub.
    """
    from app.services import llm_service

    async def _fake(**kwargs):
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(llm_service, "analyze_with_claude", _fake)


SAMPLE_SOW = (
    "The Vendor shall pay invoices within 60 days of receipt. "
    "The Contractor shall deliver the migrated system within 30 days of "
    "contract signature. Service Provider shall maintain 99.9% uptime "
    "measured monthly."
)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestExtractObligationsHappyPath:
    def test_returns_three_validated_obligations(self, monkeypatch):
        llm_payload = json.dumps([
            {
                "obligation_type": "payment",
                "party": "us",
                "description": "Pay vendor invoices within 60 days of receipt.",
                "deadline_days_from_trigger": 60,
                "trigger_event": "invoice_received",
                "source_clause_text": "The Vendor shall pay invoices within 60 days of receipt.",
                "_extraction_confidence": "high",
            },
            {
                "obligation_type": "delivery",
                "party": "counterparty",
                "description": "Deliver the migrated system within 30 days.",
                "deadline_days_from_trigger": 30,
                "trigger_event": "contract_signature",
                "source_clause_text": "The Contractor shall deliver the migrated system within 30 days of contract signature.",
            },
            {
                "obligation_type": "sla",
                "party": "counterparty",
                "description": "Maintain 99.9% monthly uptime.",
                "trigger_event": "monthly_measurement",
                "source_clause_text": "Service Provider shall maintain 99.9% uptime measured monthly.",
            },
        ])
        _patch_llm(monkeypatch, llm_payload)

        result = _run(
            obligation_extractor.extract_obligations_from_text(
                sow_text=SAMPLE_SOW,
                contract_type="it_services",
                jurisdiction_code="ON",
            )
        )
        assert len(result) == 3

        types = [o["obligation_type"] for o in result]
        assert types == ["payment", "delivery", "sla"]

        # Validate the payment row in detail.
        payment = result[0]
        assert payment["party"] == "us"
        assert payment["deadline_days_from_trigger"] == 60
        assert payment["trigger_event"] == "invoice_received"
        assert payment["_extraction_confidence"] == "high"
        assert payment["source_clause_text"].startswith("The Vendor shall pay")

        # No DB-managed fields snuck in.
        for o in result:
            assert "id" not in o
            assert "contract_id" not in o
            assert "user_id" not in o
            assert "created_at" not in o

    def test_response_already_a_python_list(self, monkeypatch):
        """Some helpers parse the JSON for us — the extractor should accept a
        ready-made list as well as a string."""
        _patch_llm(monkeypatch, [
            {
                "obligation_type": "payment",
                "party": "us",
                "description": "Pay something.",
            }
        ])

        result = _run(
            obligation_extractor.extract_obligations_from_text(SAMPLE_SOW)
        )
        assert len(result) == 1
        assert result[0]["obligation_type"] == "payment"

    def test_response_dict_with_obligations_key(self, monkeypatch):
        _patch_llm(monkeypatch, {
            "obligations": [
                {
                    "obligation_type": "delivery",
                    "party": "counterparty",
                    "description": "Deliver thing.",
                }
            ]
        })
        result = _run(obligation_extractor.extract_obligations_from_text(SAMPLE_SOW))
        assert len(result) == 1
        assert result[0]["obligation_type"] == "delivery"


# ---------------------------------------------------------------------------
# Defensive parsing: prose around the JSON block
# ---------------------------------------------------------------------------

class TestProseAroundJSON:
    def test_prose_then_json(self, monkeypatch):
        wrapped = (
            "Sure! Here are the obligations I found in your text:\n\n"
            '[{"obligation_type":"payment","party":"us",'
            '"description":"Pay invoices within 60 days."}]\n\n'
            "Let me know if you would like me to look at anything else."
        )
        _patch_llm(monkeypatch, wrapped)
        result = _run(obligation_extractor.extract_obligations_from_text(SAMPLE_SOW))
        assert len(result) == 1
        assert result[0]["obligation_type"] == "payment"

    def test_markdown_fenced_json(self, monkeypatch):
        wrapped = (
            "Here you go:\n\n"
            "```json\n"
            '[{"obligation_type":"reporting","party":"counterparty",'
            '"description":"Submit monthly status reports."}]\n'
            "```\n\nDone."
        )
        _patch_llm(monkeypatch, wrapped)
        result = _run(obligation_extractor.extract_obligations_from_text(SAMPLE_SOW))
        assert len(result) == 1
        assert result[0]["obligation_type"] == "reporting"


# ---------------------------------------------------------------------------
# Defensive parsing: malformed / unparseable JSON
# ---------------------------------------------------------------------------

class TestMalformedJSON:
    def test_garbage_string_returns_empty_list(self, monkeypatch):
        _patch_llm(monkeypatch, "this is not json at all, sorry")
        result = _run(obligation_extractor.extract_obligations_from_text(SAMPLE_SOW))
        assert result == []

    def test_truncated_json_returns_empty_list(self, monkeypatch):
        _patch_llm(monkeypatch, '[{"obligation_type":"payment","party":"us"')
        result = _run(obligation_extractor.extract_obligations_from_text(SAMPLE_SOW))
        assert result == []

    def test_llm_raises_returns_empty_list(self, monkeypatch):
        _patch_llm(monkeypatch, RuntimeError("LLM provider down"))
        result = _run(obligation_extractor.extract_obligations_from_text(SAMPLE_SOW))
        assert result == []

    def test_dict_response_with_no_array(self, monkeypatch):
        _patch_llm(monkeypatch, {"unexpected_shape": "no list anywhere"})
        result = _run(obligation_extractor.extract_obligations_from_text(SAMPLE_SOW))
        assert result == []


# ---------------------------------------------------------------------------
# Per-entry validation
# ---------------------------------------------------------------------------

class TestPerEntryValidation:
    def test_drops_unknown_obligation_type(self, monkeypatch):
        _patch_llm(monkeypatch, json.dumps([
            {  # bad type
                "obligation_type": "carrier_pigeon_delivery",
                "party": "us",
                "description": "Send a pigeon.",
            },
            {  # good
                "obligation_type": "payment",
                "party": "us",
                "description": "Pay invoices.",
            },
        ]))
        result = _run(obligation_extractor.extract_obligations_from_text(SAMPLE_SOW))
        assert len(result) == 1
        assert result[0]["obligation_type"] == "payment"

    def test_drops_unknown_party(self, monkeypatch):
        _patch_llm(monkeypatch, json.dumps([
            {
                "obligation_type": "payment",
                "party": "third_party_courier",
                "description": "Pay couriers.",
            },
            {
                "obligation_type": "payment",
                "party": "counterparty",
                "description": "Pay invoices.",
            },
        ]))
        result = _run(obligation_extractor.extract_obligations_from_text(SAMPLE_SOW))
        assert len(result) == 1
        assert result[0]["party"] == "counterparty"

    def test_drops_missing_description(self, monkeypatch):
        _patch_llm(monkeypatch, json.dumps([
            {"obligation_type": "payment", "party": "us"},  # no description
            {
                "obligation_type": "payment",
                "party": "us",
                "description": "Real description.",
            },
        ]))
        result = _run(obligation_extractor.extract_obligations_from_text(SAMPLE_SOW))
        assert len(result) == 1
        assert result[0]["description"] == "Real description."

    def test_coerces_string_days_to_int(self, monkeypatch):
        _patch_llm(monkeypatch, json.dumps([
            {
                "obligation_type": "payment",
                "party": "us",
                "description": "Pay in 45 days.",
                "deadline_days_from_trigger": "45",
            }
        ]))
        result = _run(obligation_extractor.extract_obligations_from_text(SAMPLE_SOW))
        assert result[0]["deadline_days_from_trigger"] == 45

    def test_strips_dollar_and_comma_from_amounts(self, monkeypatch):
        _patch_llm(monkeypatch, json.dumps([
            {
                "obligation_type": "delivery",
                "party": "counterparty",
                "description": "Deliver stuff.",
                "penalty_amount_cad": "$5,000",
                "liability_cap_cad": "$250,000",
            }
        ]))
        result = _run(obligation_extractor.extract_obligations_from_text(SAMPLE_SOW))
        assert result[0]["penalty_amount_cad"] == 5000.0
        assert result[0]["liability_cap_cad"] == 250000.0

    def test_drops_invalid_extraction_confidence(self, monkeypatch):
        _patch_llm(monkeypatch, json.dumps([
            {
                "obligation_type": "payment",
                "party": "us",
                "description": "Pay.",
                "_extraction_confidence": "extremely_high",
            }
        ]))
        result = _run(obligation_extractor.extract_obligations_from_text(SAMPLE_SOW))
        assert "_extraction_confidence" not in result[0]


# ---------------------------------------------------------------------------
# Empty input short-circuit
# ---------------------------------------------------------------------------

def test_empty_sow_text_returns_empty_without_calling_llm(monkeypatch):
    called = {"v": False}

    from app.services import llm_service

    async def _fake(**kwargs):
        called["v"] = True
        return "[]"

    monkeypatch.setattr(llm_service, "analyze_with_claude", _fake)

    result = _run(obligation_extractor.extract_obligations_from_text(""))
    assert result == []
    assert called["v"] is False
