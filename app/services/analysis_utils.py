"""Shared normalization helpers for LLM analysis responses.

CA-016: extracted from llm_service.py and groq_llm_service.py to eliminate
copy-paste drift between the Claude and Groq tiers.
"""


def normalize_analysis(analysis: dict) -> dict:
    """Normalize key_risks and missing_clauses to canonical schema.

    LLM responses vary: key_risks may be a dict keyed by risk name, or a list
    of dicts. missing_clauses items may be strings or dicts with different field
    names. This function coerces both to the shapes expected by the Pydantic
    response models in app/routers/contracts.py.

    Modifies *analysis* in-place and returns it.
    """
    if "key_risks" in analysis:
        raw = analysis["key_risks"]
        if isinstance(raw, dict):
            raw = [
                {"title": k, **v} if isinstance(v, dict)
                else {"title": k, "description": str(v), "severity": "medium"}
                for k, v in raw.items()
            ]
        analysis["key_risks"] = [
            {
                "severity": r.get("severity", "medium"),
                "title": r.get("title", ""),
                "description": r.get("description", ""),
                "section": r.get("section"),
                "recommendation": r.get("recommendation"),
            }
            for r in raw if isinstance(r, dict)
        ]

    if "missing_clauses" in analysis:
        raw = analysis["missing_clauses"]
        normalized = []
        for mc in raw:
            if isinstance(mc, dict):
                normalized.append({
                    "clause": mc.get("clause", mc.get("name", str(mc))),
                    "importance": mc.get("importance", mc.get("severity", "medium")),
                    "rationale": mc.get("rationale", mc.get("reason", "")),
                })
            else:
                normalized.append({"clause": str(mc), "importance": "medium", "rationale": ""})
        analysis["missing_clauses"] = normalized

    return analysis
