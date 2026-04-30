# Procurement Guardrail — Rule Corpus

This directory holds the deterministic rule set the `ProcurementGuardrail`
service consults before and after every generated negotiation move.
**Rules are data, not code** — counsel can amend them via PR with no
engineering involvement.

## Layout

```
rules/
├── README.md                this file
├── fixtures/test_cases.json golden test cases — every change must pass these
├── federal/                 acts and trade agreements applying Canada-wide
│   ├── cfta.json
│   ├── ceta.json
│   └── competition-act.json
├── ontario/
│   ├── bobi-2022.json
│   └── construction-act.json
├── quebec/                  (TBD)
├── british-columbia/        (TBD)
└── ...
```

## Rule schema (one rule)

| Field | Required | Description |
| --- | --- | --- |
| `id` | yes | Stable slug, never reused (`cfta-502-localpref`) |
| `statute` | yes | Statute identifier (`CFTA`, `BOBI-2022`, `Competition-Act`) |
| `jurisdiction` | yes | ISO-style code: `CA` (federal), `CA-ON`, `CA-QC`, `CA-BC`, ... |
| `section` | yes | Specific section/article (`Article 502`, `s.47(1)`) |
| `version_as_of` | yes | Date (`YYYY-MM-DD`) of statutory text this rule reflects |
| `effective_date` | yes | When the rule becomes active in the engine |
| `superseded_by` | no | Rule ID that replaces this one after amendment |
| `last_reviewed` | yes | Date of most recent counsel review (CI flags >180 d) |
| `last_reviewed_by` | yes | `counsel:initials` or email |
| `source_url` | yes | CanLII / government authoritative source |
| `applies_when` | no | Filter predicate (value threshold, buyer type, industry) |
| `forbid` | yes | `move_types[]`, `text_patterns[]` (regex), `entity_swaps[]` |
| `severity` | yes | `hard_block` / `soft_warn` / `advisory` |
| `reason` | yes | One-line plain-English explanation surfaced to the user |
| `remediation_hint` | no | Suggested compliant alternative |

## Update workflow

1. Counsel proposes amendment as a PR editing the relevant JSON file.
2. PR must include: updated `last_reviewed`, source URL, and a fixture entry
   demonstrating the rule's new behaviour.
3. CI runs `tests/test_procurement_guardrail.py` against
   `fixtures/test_cases.json`.
4. Engineering reviewer confirms schema validity (loader fails fast on bad
   rules).
5. Counsel reviewer approves the legal substance.
6. Merge → rules hot-load on next deploy.

## Conflict handling

The engine surfaces **all triggered rules**, not just the highest-priority
one. Statute conflicts — e.g. BOBI 2022 mandates Ontario-business preference
while CFTA Art. 502 prohibits inter-provincial discrimination — are resolved
downstream by the scorer + counsel, not by encoded precedence in JSON.

## Drift defence

Each rule carries `last_reviewed`. The CI test suite fails any rule older
than 180 days unless explicitly re-stamped. Amendments to underlying
statutes are caught by the fixture suite — a rule whose behaviour changes
must update or add fixtures, otherwise the test fails loudly.

## Coverage matrix

| Jurisdiction | Statute / Instrument | Seeded? | File |
| --- | --- | --- | --- |
| CA federal | CFTA — Art. 502, Art. 503 | ✓ | `federal/cfta.json` |
| CA federal | CETA — Ch. 19 | ✓ | `federal/ceta.json` |
| CA federal | Competition Act — s.47 (bid-rigging) | ✓ | `federal/competition-act.json` |
| CA federal | Copyright Act — s.13(3), s.14.1(2) (moral rights) | ✓ | `federal/copyright-act.json` |
| CA federal | Trademarks Act — s.50 (licensing/QC) | ✓ | `federal/trademarks-act.json` |
| CA federal | Patent Act — s.49 (assignments) | ✓ | `federal/patent-act.json` |
| CA federal | PIPEDA — Sch.1 cross-border | ✓ | `federal/pipeda.json` |
| CA federal | CASL — s.6 (commercial electronic messages) | ✓ | `federal/casl.json` |
| CA federal | CUSMA Ch.13, Government Contracts Regs, Defence Production Act, Investment Canada Act, Limitations Act | ✗ | TBD |
| CA‑ON | BOBI 2022 | ✓ | `ontario/bobi-2022.json` |
| CA‑ON | Construction Act — prompt payment, holdback | ✓ | `ontario/construction-act.json` |
| CA‑ON | Insurance / WSIA | ✓ | `ontario/insurance-act.json` |
| CA‑ON | Sale of Goods Act | ✓ | `ontario/sale-of-goods-act.json` |
| CA‑ON | Broader Public Sector Accountability Act, Procurement Directive, AODA, PIPA‑equivalent, Consumer Protection Act 2002 | ✗ | TBD |
| CA‑QC | Law 25 (Bill 64) — privacy | ✓ | `quebec/law-25.json` |
| CA‑QC | LCOP (public-body contracting), UPAC integrity | ✗ | TBD |
| CA‑BC | PIPA, Procurement Services Act | ✗ | TBD |
| CA‑AB / SK / MB / atlantic / territories | various | ✗ | TBD |
| EU | GDPR — Art. 28, Ch. V transfers | ✓ | `eu/gdpr.json` |
| EU | EU AI Act, ePrivacy | ✗ | TBD |

Each seeded file holds 1–2 example rules to establish shape and prove the
schema scales across statutes; full corpus build-out is a counsel-led
effort tracked separately.

## Wiring into FastAPI

Drop into the negotiation routes (`app/routers/negotiation_routes.py`):

```python
from fastapi import Depends, HTTPException
from app.services.procurement_guardrail import ProcurementGuardrail, Move

# Module-level singleton — rules load once at startup.
guardrail = ProcurementGuardrail.load("rules")

def get_guardrail() -> ProcurementGuardrail:
    return guardrail

@router.post("/{session_id}/propose")
async def propose(
    session_id: str,
    req: ProposeRequest,
    gr: ProcurementGuardrail = Depends(get_guardrail),
    db: Session = Depends(get_db),
):
    move = Move(clause_id=req.clause_id, move_type=req.move_type, target_text=req.text)
    triggers = gr.screen(move, req.context)
    if gr.is_blocked(triggers):
        raise HTTPException(422, detail={"blocked": True, "triggers": [t.__dict__ for t in triggers]})

    # Generate as normal; then post-screen the LLM response:
    raw = await llm_waterfall.generate(...)
    post_triggers = gr.screen(Move(req.clause_id, req.move_type, raw), req.context)
    if gr.is_blocked(post_triggers):
        await log_conflict(session_id, req, raw, post_triggers)   # gold DPO signal
        raise HTTPException(422, detail={"blocked": True, "triggers": [t.__dict__ for t in post_triggers]})

    return {"text": raw, "warnings": [t.__dict__ for t in post_triggers if t.severity == "soft_warn"]}
```

Three rules of the integration: (1) JSON file is the source of truth — counsel can amend without engineering involvement; (2) every `hard_block` writes to a `negotiation_conflicts` table — those rows are the highest-value DPO training signal you'll ever collect; (3) post-screening uses NER + regex, never an LLM, so a hallucinated "I checked CFTA" cannot pass.
