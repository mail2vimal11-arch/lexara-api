"""
ProcurementGuardrail — deterministic veto layer over generated negotiation moves.

Loads rules from rules/**/*.json at startup. Every rule is data, owned by
counsel, and can be amended without code changes. The guardrail runs both
pre-inference (refuse to prompt the model on a clearly illegal move) and
post-inference (NER + regex check of the generated text).

Scope: applies to Canadian government tendering — federal trade agreements
(CFTA, CETA, CUSMA), federal acts (Competition Act, Government Contracts
Regulations), and provincial/territorial regimes (BOBI, Construction Act,
LCOP, etc.). New jurisdictions are added by dropping JSON files into
rules/<region>/.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Literal

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

Severity = Literal["hard_block", "soft_warn", "advisory"]


class AppliesWhen(BaseModel):
    procurement_value_gte_cad: float | None = None
    procurement_value_lt_cad: float | None = None
    buyer_types: list[str] | None = None
    industries: list[str] | None = None
    covered_under_ceta_annex: bool | None = None

    def matches(self, ctx: dict[str, Any]) -> bool:
        v = ctx.get("procurement_value_cad")
        if self.procurement_value_gte_cad is not None and (v is None or v < self.procurement_value_gte_cad):
            return False
        if self.procurement_value_lt_cad is not None and (v is None or v >= self.procurement_value_lt_cad):
            return False
        if self.buyer_types and ctx.get("buyer_type") not in self.buyer_types:
            return False
        if self.industries and ctx.get("industry") not in self.industries and "any" not in self.industries:
            # "any" is an explicit wildcard for rules that apply universally
            if ctx.get("industry") != "any":
                return False
        if self.covered_under_ceta_annex is True and not ctx.get("covered_under_ceta_annex"):
            return False
        return True


class Forbid(BaseModel):
    move_types: list[str] = Field(default_factory=list)
    text_patterns: list[str] = Field(default_factory=list)
    entity_swaps: list[str] = Field(default_factory=list)
    # If any of these substrings (case-insensitive) appears in the move text,
    # text_pattern matches are suppressed — useful for "X unless Y" rules
    # like 'brand name without "or equivalent"'.
    unless_text_contains: list[str] = Field(default_factory=list)


class Rule(BaseModel):
    id: str
    statute: str
    jurisdiction: str
    section: str
    version_as_of: date
    effective_date: date
    superseded_by: str | None = None
    last_reviewed: date
    last_reviewed_by: str
    source_url: str
    applies_when: AppliesWhen = Field(default_factory=AppliesWhen)
    forbid: Forbid
    severity: Severity
    reason: str
    remediation_hint: str | None = None
    notes: str | None = None

    @field_validator("id")
    @classmethod
    def slug_only(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", v):
            raise ValueError(f"rule id must be lowercase, digits, dots, or hyphens, got: {v!r}")
        return v


@dataclass(frozen=True)
class Move:
    clause_id: str
    move_type: str
    target_text: str


@dataclass(frozen=True)
class Trigger:
    rule_id: str
    statute: str
    section: str
    severity: Severity
    reason: str
    remediation_hint: str | None
    matched_via: Literal["move_type", "text_pattern", "entity_swap"]


class ProcurementGuardrail:
    """
    Deterministic veto layer. Stateless after construction; safe to share.

    Usage:
        gr = ProcurementGuardrail.load("rules")
        triggers = gr.screen(move, context)
        if any(t.severity == "hard_block" for t in triggers):
            ...  # refuse
    """

    REVIEW_WINDOW_DAYS = 180

    def __init__(self, rules: list[Rule]):
        self._rules = [r for r in rules if r.superseded_by is None and r.effective_date <= date.today()]
        self._stale = self._find_stale(rules)
        if self._stale:
            logger.warning(
                "procurement_guardrail.stale_rules count=%d ids=%s",
                len(self._stale),
                [r.id for r in self._stale],
            )

    @classmethod
    def load(cls, root: str | Path) -> "ProcurementGuardrail":
        root = Path(root)
        if not root.exists():
            raise FileNotFoundError(f"rules directory not found: {root}")
        rules: list[Rule] = []
        for path in sorted(root.rglob("*.json")):
            if path.parent.name == "fixtures":
                continue
            try:
                payload = json.loads(path.read_text())
            except json.JSONDecodeError as e:
                raise ValueError(f"malformed rule file {path}: {e}") from e
            for raw in payload.get("rules", []):
                rules.append(Rule(**raw))
        cls._check_unique_ids(rules)
        logger.info("procurement_guardrail.loaded count=%d", len(rules))
        return cls(rules)

    @staticmethod
    def _check_unique_ids(rules: Iterable[Rule]) -> None:
        seen: dict[str, str] = {}
        for r in rules:
            if r.id in seen:
                raise ValueError(f"duplicate rule id: {r.id}")
            seen[r.id] = r.statute

    @classmethod
    def _find_stale(cls, rules: Iterable[Rule]) -> list[Rule]:
        cutoff = date.today() - timedelta(days=cls.REVIEW_WINDOW_DAYS)
        return [r for r in rules if r.last_reviewed < cutoff and r.superseded_by is None]

    def screen(self, move: Move, context: dict[str, Any]) -> list[Trigger]:
        triggers: list[Trigger] = []
        for rule in self._rules:
            if not rule.applies_when.matches(context):
                continue
            via = self._matches(rule, move)
            if via is not None:
                triggers.append(
                    Trigger(
                        rule_id=rule.id,
                        statute=rule.statute,
                        section=rule.section,
                        severity=rule.severity,
                        reason=rule.reason,
                        remediation_hint=rule.remediation_hint,
                        matched_via=via,
                    )
                )
        return triggers

    @staticmethod
    def _matches(rule: Rule, move: Move) -> Literal["move_type", "text_pattern", "entity_swap"] | None:
        if move.move_type in rule.forbid.move_types:
            return "move_type"
        haystack_lower = move.target_text.lower()
        suppressed = any(s.lower() in haystack_lower for s in rule.forbid.unless_text_contains)
        if not suppressed:
            for pattern in rule.forbid.text_patterns:
                if re.search(pattern, move.target_text):
                    return "text_pattern"
        return None

    def is_blocked(self, triggers: list[Trigger]) -> bool:
        return any(t.severity == "hard_block" for t in triggers)

    @property
    def stale_rules(self) -> list[Rule]:
        return list(self._stale)
