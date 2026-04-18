"""Claude AI service for contract analysis - tab-based focused prompts."""

import httpx
import json
import logging
from typing import Optional, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a legal document analyzer specializing in Canadian contract law (Ontario jurisdiction).
CRITICAL: Always return valid JSON only. No markdown, no explanation outside the JSON.
This analysis is informational only — NOT legal advice."""


async def analyze_with_claude(
    text: str,
    contract_type: str = "auto",
    jurisdiction: str = "ON",
    include_recommendations: bool = True,
    mode: str = "summary",
    **kwargs
) -> Dict[str, Any]:
    """Call Claude with a focused prompt based on the requested tab/mode.
    If use_local_llm is enabled, tries HuggingFace (SaulLM) first."""

    # Try HuggingFace first if configured
    if settings.use_local_llm and settings.hf_api_token and settings.hf_model_id:
        try:
            from app.services.hf_llm_service import analyze_with_huggingface
            result = await analyze_with_huggingface(
                text, contract_type, jurisdiction, mode, **kwargs
            )
            logger.info(f"HuggingFace ({mode}): success")
            return result
        except Exception as e:
            logger.warning(f"HuggingFace failed, falling back to Claude: {e}")

    prompts = {
        "summary": _prompt_summary,
        "risk_score": _prompt_risk_score,
        "key_risks": _prompt_key_risks,
        "missing_clauses": _prompt_missing_clauses,
        "extract_clauses": _prompt_extract_clauses,
    }

    prompt_fn = prompts.get(mode, _prompt_summary)
    prompt = prompt_fn(text, contract_type, jurisdiction)

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.claude_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-4-5-haiku-20250514",
                    "max_tokens": 2048,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )

            if response.status_code != 200:
                logger.error(
                    f"Claude API error: status={response.status_code} "
                    f"body={response.text[:1000]}"
                )
                raise Exception(f"Claude API error: {response.status_code}")

            result = response.json()
            tokens_used = result["usage"]["output_tokens"]
            content = result["content"][0]["text"].strip()

            # Strip markdown code fences if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Find JSON boundaries
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                content = content[start:end]

            analysis = json.loads(content)
            analysis["tokens_used"] = tokens_used

            # Normalize key_risks (list or dict → list of RiskFlag dicts)
            if "key_risks" in analysis:
                raw = analysis["key_risks"]
                if isinstance(raw, dict):
                    raw = [{"title": k, **v} if isinstance(v, dict) else {"title": k, "description": str(v), "severity": "medium"} for k, v in raw.items()]
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

            # Normalize missing_clauses (list of dicts or strings)
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

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {e} | content: {content[:300]}")
        raise Exception("Failed to parse Claude response")
    except Exception as e:
        logger.error(f"Claude analysis failed: {e}", exc_info=True)
        raise


# ── Focused prompts per tab ───────────────────────────────────────────────────

def _prompt_summary(text: str, contract_type: str, jurisdiction: str) -> str:
    return f"""Summarize this {contract_type} contract in plain English for a non-lawyer.

CONTRACT (first 6000 chars):
{text[:6000]}

Return JSON:
{{
  "summary": "2-3 sentence plain-English overview of what this contract does",
  "contract_type": "detected type (service_agreement|nda|employment|lease|other)",
  "jurisdiction": "{jurisdiction}",
  "confidence": 0.0-1.0
}}"""


def _prompt_risk_score(text: str, contract_type: str, jurisdiction: str) -> str:
    return f"""Score the legal risk of this {contract_type} contract under {jurisdiction} law. 0=no risk, 100=extreme risk.

CONTRACT (first 6000 chars):
{text[:6000]}

Return JSON:
{{
  "overall_risk_score": 0-100,
  "risk_level": "low|medium|high|critical",
  "scores_by_category": {{
    "liability": 0-100,
    "data_protection": 0-100,
    "termination": 0-100,
    "ip_ownership": 0-100,
    "warranty": 0-100
  }},
  "interpretation": "1-2 sentence plain English explanation of the score"
}}"""


def _prompt_key_risks(text: str, contract_type: str, jurisdiction: str) -> str:
    return f"""Identify the top legal risks in this {contract_type} contract under {jurisdiction} law.

CONTRACT (first 6000 chars):
{text[:6000]}

Return JSON with up to 6 risks:
{{
  "key_risks": [
    {{
      "severity": "critical|high|medium|low",
      "title": "Short risk title",
      "description": "What the risk is and why it matters",
      "section": "Which section/clause (if identifiable)",
      "recommendation": "How to fix or mitigate it"
    }}
  ]
}}"""


def _prompt_missing_clauses(text: str, contract_type: str, jurisdiction: str) -> str:
    return f"""Identify important clauses that are MISSING from this {contract_type} contract under {jurisdiction} law.

CONTRACT (first 6000 chars):
{text[:6000]}

Return JSON:
{{
  "missing_clauses": [
    {{
      "clause": "Clause name",
      "importance": "critical|high|medium|low",
      "rationale": "Why this clause is needed and what risk its absence creates"
    }}
  ]
}}"""


def _prompt_extract_clauses(text: str, contract_type: str, jurisdiction: str) -> str:
    return f"""You are a Canadian contract lawyer. Review this {contract_type} contract and suggest redline revisions for clauses rated high or medium risk under {jurisdiction} law.

CONTRACT (first 6000 chars):
{text[:6000]}

Return JSON with up to 6 clause revisions:
{{
  "clauses": [
    {{
      "type": "liability|termination|ip|indemnification|warranty|confidentiality|payment|other",
      "severity": "high|medium",
      "original": "The exact problematic clause text (or summary if long)",
      "revised": "Your suggested improved replacement clause language",
      "rationale": "One sentence: why this revision protects the parties better under Ontario law"
    }}
  ]
}}

Only include clauses that are high or medium risk. Skip low risk or missing clauses (those are covered elsewhere)."""
