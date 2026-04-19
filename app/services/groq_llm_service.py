"""
Groq Inference service for LexAra contract analysis.
Uses Groq's free OpenAI-compatible API with Llama/Mistral models.
Falls back to Claude if Groq is unavailable.
"""

import httpx
import json
import logging
from typing import Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are a legal document analyzer specializing in Canadian contract law (Ontario jurisdiction).
CRITICAL: Always return valid JSON only. No markdown, no explanation outside the JSON.
This analysis is informational only — NOT legal advice."""


def _build_messages(text: str, mode: str, contract_type: str = "auto", jurisdiction: str = "ON") -> list:
    """Build chat messages for Groq (OpenAI format)."""

    prompts = {
        "summary": (
            f"Summarize this {contract_type} contract in plain English for a non-lawyer.\n\n"
            f"CONTRACT (first 6000 chars):\n{text[:6000]}\n\n"
            f"Return JSON:\n"
            f'{{"summary": "2-3 sentence overview", "contract_type": "detected type", '
            f'"jurisdiction": "{jurisdiction}", "confidence": 0.0-1.0}}'
        ),
        "risk_score": (
            f"Score the legal risk of this {contract_type} contract under {jurisdiction} law. "
            f"0=no risk, 100=extreme risk.\n\n"
            f"CONTRACT:\n{text[:6000]}\n\n"
            f"Return JSON:\n"
            f'{{"overall_risk_score": 0-100, "risk_level": "low|medium|high|critical", '
            f'"scores_by_category": {{"liability": 0-100, "data_protection": 0-100, '
            f'"termination": 0-100, "ip_ownership": 0-100, "warranty": 0-100}}, '
            f'"interpretation": "1-2 sentence explanation"}}'
        ),
        "key_risks": (
            f"Identify the top legal risks in this {contract_type} contract under {jurisdiction} law.\n\n"
            f"CONTRACT:\n{text[:6000]}\n\n"
            f"Return JSON with up to 6 risks:\n"
            f'{{"key_risks": [{{"severity": "critical|high|medium|low", "title": "Short title", '
            f'"description": "What the risk is", "section": "Which section", '
            f'"recommendation": "How to fix"}}]}}'
        ),
        "missing_clauses": (
            f"Identify important clauses MISSING from this {contract_type} contract under {jurisdiction} law.\n\n"
            f"CONTRACT:\n{text[:6000]}\n\n"
            f"Return JSON:\n"
            f'{{"missing_clauses": [{{"clause": "Clause name", "importance": "critical|high|medium|low", '
            f'"rationale": "Why needed"}}]}}'
        ),
        "extract_clauses": (
            f"Review this {contract_type} contract and suggest redline revisions for risky clauses under {jurisdiction} law.\n\n"
            f"CONTRACT:\n{text[:6000]}\n\n"
            f"Return JSON with up to 6 revisions:\n"
            f'{{"clauses": [{{"type": "liability|termination|ip|indemnification|warranty|confidentiality|payment|other", '
            f'"severity": "high|medium", "original": "The problematic clause", '
            f'"revised": "Improved replacement", "rationale": "Why this is better"}}]}}'
        ),
    }

    user_prompt = prompts.get(mode, prompts["summary"])

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


async def analyze_with_groq(
    text: str,
    contract_type: str = "auto",
    jurisdiction: str = "ON",
    mode: str = "summary",
    **kwargs
) -> Dict[str, Any]:
    """Call Groq's API for contract analysis. OpenAI-compatible format."""

    if not settings.groq_api_key:
        raise ValueError("Groq not configured: set GROQ_API_KEY")

    messages = _build_messages(text, mode, contract_type, jurisdiction)

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.groq_model,
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(GROQ_API_URL, headers=headers, json=payload)

            if response.status_code == 429:
                logger.warning("Groq rate limited, falling back to Claude")
                raise Exception("Groq rate limited")

            if response.status_code != 200:
                logger.error(f"Groq API error: status={response.status_code} body={response.text[:300]}")
                raise Exception(f"Groq API error: {response.status_code}")

            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            tokens_used = result.get("usage", {}).get("total_tokens", 0)

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                content = content[start:end]

            analysis = json.loads(content)
            analysis["tokens_used"] = tokens_used
            analysis["model"] = settings.groq_model

            # Normalize key_risks
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

            # Normalize missing_clauses
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
        logger.error(f"Groq JSON parse failed: {e} | content: {content[:300]}")
        raise Exception("Failed to parse Groq response")
    except Exception as e:
        logger.error(f"Groq analysis failed: {e}")
        raise
