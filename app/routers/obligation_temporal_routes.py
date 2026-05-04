"""Feature 3: Obligation Matrix — temporal graph endpoints.

POST   /v1/procurement/obligations/analyze         extract + persist + resolve
PATCH  /v1/procurement/contracts/{cid}/anchors     update anchor dates, re-resolve
GET    /v1/procurement/contracts/{cid}/timeline    return projected timeline

Notes
-----
The obligation pre-extraction (modal verbs, party detection) here is a
deliberately simple v1 sentence-splitter. The temporal extractor is the
heavyweight piece; obligation extraction can be swapped in later without
touching the persistence or resolver layers.
"""

from __future__ import annotations

import re
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.obligation_temporal import (
    ContractObligation,
    ContractAnchor,
    ObligationTemporalSpec,
    ObligationTemporalResolution,
    Holiday,
)
from app.models.user import User
from app.security import get_current_user
from app.services.obligation_resolver import (
    Resolution,
    Status,
    resolve_contract_timeline,
)

router = APIRouter(prefix="/obligations", tags=["Obligations (Feature 3)"])


# ---------- Pydantic schemas ----------

class AnalyzeMeta(BaseModel):
    contract_id: str
    project_start_date: Optional[date] = None
    known_crown_entities: list[str] = Field(default_factory=list)
    known_vendor_entities: list[str] = Field(default_factory=list)
    jurisdiction: str = "CA-FED"


class AnalyzeRequest(BaseModel):
    document_text: str
    meta: AnalyzeMeta


class AnchorUpdate(BaseModel):
    anchor_key: str
    resolved_date: Optional[date] = None
    label: Optional[str] = None


class AnchorPatchRequest(BaseModel):
    anchors: list[AnchorUpdate]


class ResolutionOut(BaseModel):
    obligation_id: str
    spec_id: str
    text: str
    party: Optional[str]
    section_ref: Optional[str]
    raw_phrase: Optional[str]
    projected_date: Optional[date]
    status: str
    dependency_path: list[str]


# ---------- Endpoints ----------

@router.post("/analyze")
def analyze_obligations(
    req: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract obligations + temporal specs, persist, resolve."""
    # Lazy-import the extractor so test envs without spaCy still load this router.
    from app.nlp.temporal_extractor import extract_temporal_spec

    contract_id = req.meta.contract_id

    # Wipe prior analysis for this contract — re-analysis is the common path.
    _purge_contract(db, contract_id)

    # 1. Pre-extract obligation sentences.
    obligations = _extract_obligation_sentences(
        req.document_text,
        crown_aliases=req.meta.known_crown_entities,
        vendor_aliases=req.meta.known_vendor_entities,
    )
    if not obligations:
        return {"obligations": [], "anchors": [], "timeline": []}

    # 2. Seed anchors. Always create the canonical four; extractor matches
    #    against these by anchor_key.
    anchor_rows = _seed_anchors(db, contract_id, project_start=req.meta.project_start_date)
    anchor_key_to_id = {a.anchor_key: a.anchor_id for a in anchor_rows}

    # 3. Persist obligations + temporal specs.
    spec_rows: list[dict] = []
    for ob in obligations:
        obligation = ContractObligation(
            contract_id=contract_id,
            section_ref=ob.get("section_ref"),
            text=ob["text"],
            party=ob.get("party"),
            modal_verb=ob.get("modal_verb"),
        )
        db.add(obligation)
        db.flush()  # populate obligation_id

        spec_dict = extract_temporal_spec(ob["text"])
        anchor_id = anchor_key_to_id.get(spec_dict.pop("anchor_key", None))

        spec = ObligationTemporalSpec(
            obligation_id=obligation.obligation_id,
            kind=spec_dict["kind"],
            absolute_date=spec_dict.get("absolute_date"),
            offset_value=spec_dict.get("offset_value"),
            offset_unit=spec_dict.get("offset_unit"),
            direction=spec_dict.get("direction"),
            anchor_id=anchor_id,
            anchor_obligation_id=None,  # cross-ref pass fills later
            recurrence_rule=spec_dict.get("recurrence_rule"),
            raw_phrase=spec_dict.get("raw_phrase"),
            confidence=spec_dict.get("confidence", 1.0),
        )
        db.add(spec)
        db.flush()

        spec_rows.append(_spec_to_dict(spec))

    # 4. Resolve and persist projections.
    holidays = _load_holidays(db, req.meta.jurisdiction)
    anchor_dates = {a.anchor_id: a.resolved_date for a in anchor_rows if a.resolved_date}
    resolutions = resolve_contract_timeline(spec_rows, anchor_dates, holidays)
    _persist_resolutions(db, resolutions)
    db.commit()

    return {
        "contract_id": contract_id,
        "obligations_extracted": len(obligations),
        "timeline": _serialize_timeline(db, contract_id),
    }


@router.patch("/contracts/{contract_id}/anchors")
def patch_anchors(
    contract_id: str,
    req: AnchorPatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update anchor dates and re-resolve the timeline.

    This is the magic moment: user types one date, every relative deadline
    in the contract gets re-projected.
    """
    for upd in req.anchors:
        anchor = (
            db.query(ContractAnchor)
              .filter(
                  ContractAnchor.contract_id == contract_id,
                  ContractAnchor.anchor_key == upd.anchor_key,
              ).one_or_none()
        )
        if anchor is None:
            anchor = ContractAnchor(
                contract_id=contract_id,
                anchor_key=upd.anchor_key,
                label=upd.label or upd.anchor_key.replace("_", " ").title(),
                source="user_input",
            )
            db.add(anchor)
        if upd.resolved_date is not None:
            anchor.resolved_date = upd.resolved_date
        if upd.label is not None:
            anchor.label = upd.label

    db.flush()
    _recompute(db, contract_id)
    db.commit()

    return {"timeline": _serialize_timeline(db, contract_id)}


@router.get("/contracts/{contract_id}/timeline")
def get_timeline(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    timeline = _serialize_timeline(db, contract_id)
    if not timeline:
        raise HTTPException(404, f"No obligations analyzed for contract {contract_id}")
    return {"contract_id": contract_id, "timeline": timeline}


# ---------- Internals ----------

_MODAL_RE = re.compile(
    r"(?P<sentence>[^.;]*\b(?P<modal>shall|must|will|may)\b[^.;]*[.;])",
    re.IGNORECASE,
)
_SECTION_RE = re.compile(r"^\s*(?:Section\s+)?(\d+(?:\.\d+)*(?:\([a-z]\))?)", re.IGNORECASE)


def _extract_obligation_sentences(
    document_text: str,
    crown_aliases: list[str],
    vendor_aliases: list[str],
) -> list[dict]:
    """Stub obligation splitter. Real version lives elsewhere — this is enough
    to drive the temporal pipeline end-to-end."""
    crown_set  = {a.lower() for a in crown_aliases}
    vendor_set = {a.lower() for a in vendor_aliases}

    out = []
    for match in _MODAL_RE.finditer(document_text):
        sentence = match.group("sentence").strip()
        modal = match.group("modal").lower()
        lower = sentence.lower()

        if any(v in lower for v in vendor_set) or "contractor" in lower:
            party = "contractor"
        elif any(c in lower for c in crown_set) or "crown" in lower:
            party = "crown"
        else:
            party = "unclear"

        section_match = _SECTION_RE.search(sentence)
        section_ref = section_match.group(1) if section_match else None

        out.append({
            "text": sentence,
            "modal_verb": modal,
            "party": party,
            "section_ref": section_ref,
        })
    return out


def _seed_anchors(
    db: Session,
    contract_id: str,
    project_start: Optional[date],
) -> list[ContractAnchor]:
    canonical = [
        ("contract_award", "Contract Award", project_start),
        ("effective_date", "Effective Date", project_start),
        ("go_live",        "Go-Live", None),
        ("acceptance",     "Acceptance", None),
    ]
    rows = []
    for key, label, seed_date in canonical:
        existing = (
            db.query(ContractAnchor)
              .filter(
                  ContractAnchor.contract_id == contract_id,
                  ContractAnchor.anchor_key == key,
              ).one_or_none()
        )
        if existing:
            rows.append(existing)
            continue
        anchor = ContractAnchor(
            contract_id=contract_id,
            anchor_key=key,
            label=label,
            resolved_date=seed_date,
            source="user_input" if seed_date else "extracted",
        )
        db.add(anchor)
        db.flush()
        rows.append(anchor)
    return rows


def _load_holidays(db: Session, jurisdiction: str) -> set[date]:
    rows = db.query(Holiday).filter(Holiday.jurisdiction == jurisdiction).all()
    return {r.holiday_date for r in rows}


def _spec_to_dict(spec: ObligationTemporalSpec) -> dict:
    return {
        "spec_id": spec.spec_id,
        "obligation_id": spec.obligation_id,
        "kind": spec.kind,
        "absolute_date": spec.absolute_date,
        "offset_value": spec.offset_value,
        "offset_unit": spec.offset_unit,
        "direction": spec.direction,
        "anchor_id": spec.anchor_id,
        "anchor_obligation_id": spec.anchor_obligation_id,
    }


def _persist_resolutions(db: Session, resolutions: dict[str, Resolution]) -> None:
    for spec_id, res in resolutions.items():
        existing = (
            db.query(ObligationTemporalResolution)
              .filter(ObligationTemporalResolution.spec_id == spec_id)
              .one_or_none()
        )
        if existing:
            existing.projected_date  = res.projected_date
            existing.status          = res.status.value
            existing.dependency_path = res.dependency_path
        else:
            db.add(ObligationTemporalResolution(
                spec_id=spec_id,
                projected_date=res.projected_date,
                status=res.status.value,
                dependency_path=res.dependency_path,
            ))


def _recompute(db: Session, contract_id: str) -> None:
    # Pull all specs for this contract via obligations FK.
    spec_rows = (
        db.query(ObligationTemporalSpec)
          .join(ContractObligation,
                ContractObligation.obligation_id == ObligationTemporalSpec.obligation_id)
          .filter(ContractObligation.contract_id == contract_id)
          .all()
    )
    if not spec_rows:
        return

    anchors = (
        db.query(ContractAnchor)
          .filter(ContractAnchor.contract_id == contract_id)
          .all()
    )
    anchor_dates = {a.anchor_id: a.resolved_date for a in anchors if a.resolved_date}

    holidays = _load_holidays(db, "CA-FED")  # TODO: store jurisdiction per contract
    spec_dicts = [_spec_to_dict(s) for s in spec_rows]
    resolutions = resolve_contract_timeline(spec_dicts, anchor_dates, holidays)
    _persist_resolutions(db, resolutions)


def _serialize_timeline(db: Session, contract_id: str) -> list[dict]:
    rows = (
        db.query(
            ContractObligation,
            ObligationTemporalSpec,
            ObligationTemporalResolution,
        )
        .join(ObligationTemporalSpec,
              ObligationTemporalSpec.obligation_id == ContractObligation.obligation_id)
        .outerjoin(ObligationTemporalResolution,
                   ObligationTemporalResolution.spec_id == ObligationTemporalSpec.spec_id)
        .filter(ContractObligation.contract_id == contract_id)
        .all()
    )
    return [
        {
            "obligation_id": ob.obligation_id,
            "spec_id": spec.spec_id,
            "text": ob.text,
            "party": ob.party,
            "section_ref": ob.section_ref,
            "raw_phrase": spec.raw_phrase,
            "projected_date": (res.projected_date.isoformat()
                               if res and res.projected_date else None),
            "status": res.status if res else "ambiguous",
            "dependency_path": (res.dependency_path or []) if res else [],
        }
        for ob, spec, res in rows
    ]


def _purge_contract(db: Session, contract_id: str) -> None:
    """Cascade-deletes via FK; explicit query so the order is deterministic."""
    obligations = (
        db.query(ContractObligation.obligation_id)
          .filter(ContractObligation.contract_id == contract_id)
          .all()
    )
    obligation_ids = [o.obligation_id for o in obligations]
    if obligation_ids:
        # Specs and resolutions cascade via FK ON DELETE CASCADE.
        db.query(ContractObligation).filter(
            ContractObligation.obligation_id.in_(obligation_ids)
        ).delete(synchronize_session=False)
    db.flush()
