"""
HuggingFace Inference API service for LexAra legal model.
Calls the fine-tuned SaulLM model hosted on HuggingFace.
Falls back to Claude API if HuggingFace is unavailable.
"""

import httpx
import json
import logging
from typing import Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

HF_API_URL = "https://api-inference.huggingface.co/models/{model_id}"


def _build_prompt(text: str, mode: str, contract_type: str = "auto", jurisdiction: str = "ON") -> str:
    """Build instruction prompt matching the fine-tuning format."""

    if mode == "classify":
        return (
            f"### Instruction:\n"
            f"Classify this procurement clause. Return JSON with clause_type, risk_level, jurisdiction.\n\n"
            f"### Input:\n{text[:4000]}\n\n"
            f"### Response:\n"
        )

    if mode == "risk_analysis":
        return (
            f"### Instruction:\n"
            f"Analyze this clause for procurement risks and suggest improvements. Return JSON.\n\n"
            f"### Input:\n{text[:4000]}\n\n"
            f"### Response:\n"
        )

    if mode == "summary":
        return (
            f"### Instruction:\n"
            f"Summarize this {contract_type} contract for a {jurisdiction} jurisdiction procurement officer. "
            f"Return JSON with summary, contract_type, jurisdiction, confidence.\n\n"
            f"### Input:\n{text[:6000]}\n\n"
            f"### Response:\n"
        )

    if mode == "risk_score":
        return (
            f"### Instruction:\n"
            f"Score the legal risk of this {contract_type} contract under {jurisdiction} law. "
            f"Return JSON with overall_risk_score (0-100), risk_level, scores_by_category, interpretation.\n\n"
            f"### Input:\n{text[:6000]}\n\n"
            f"### Response:\n"
        )

    if mode == "key_risks":
        return (
            f"### Instruction:\n"
            f"Identify the top legal risks in this {contract_type} contract under {jurisdiction} law. "
            f"Return JSON with key_risks array (severity, title, description, recommendation).\n\n"
            f"### Input:\n{text[:6000]}\n\n"
            f"### Response:\n"
        )

    if mode == "missing_clauses":
        return (
            f"### Instruction:\n"
            f"Identify important clauses missing from this {contract_type} contract under {jurisdiction} law. "
            f"Return JSON with missing_clauses array (clause, importance, rationale).\n\n"
            f"### Input:\n{text[:6000]}\n\n"
            f"### Response:\n"
        )

    if mode == "extract_clauses":
        return (
            f"### Instruction:\n"
            f"Suggest redline revisions for risky clauses in this {contract_type} contract under {jurisdiction} law. "
            f"Return JSON with clauses array (type, severity, original, revised, rationale).\n\n"
            f"### Input:\n{text[:6000]}\n\n"
            f"### Response:\n"
        )

    # Default: general query
    return (
        f"### Instruction:\n{mode}\n\n"
        f"### Input:\n{text[:4000]}\n\n"
        f"### Response:\n"
    )


async def analyze_with_huggingface(
    text: str,
    contract_type: str = "auto",
    jurisdiction: str = "ON",
    mode: str = "summary",
    **kwargs
) -> Dict[str, Any]:
    """
    Call the fine-tuned LexAra legal model on HuggingFace Inference API.

    Requires settings.hf_api_token and settings.hf_model_id to be configured.
    """
    if not settings.hf_api_token or not settings.hf_model_id:
        raise ValueError("HuggingFace not configured: set HF_API_TOKEN and HF_MODEL_ID")

    prompt = _build_prompt(text, mode, contract_type, jurisdiction)
    url = HF_API_URL.format(model_id=settings.hf_model_id)

    headers = {
        "Authorization": f"Bearer {settings.hf_api_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 1024,
            "temperature": 0.1,
            "do_sample": True,
            "return_full_text": False,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 503:
                # Model is loading — HuggingFace cold start
                logger.warning("HuggingFace model loading, falling back to Claude")
                raise Exception("Model loading")

            if response.status_code != 200:
                logger.error(f"HuggingFace API error: {response.status_code} — {response.text}")
                raise Exception(f"HuggingFace API error: {response.status_code}")

            result = response.json()

            # HF returns list of generated texts
            if isinstance(result, list) and len(result) > 0:
                content = result[0].get("generated_text", "").strip()
            else:
                content = str(result).strip()

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                content = content[start:end]

            analysis = json.loads(content)
            analysis["tokens_used"] = 0  # HF free tier doesn't report tokens
            analysis["model"] = "lexara-legal-saullm"
            return analysis

    except json.JSONDecodeError as e:
        logger.error(f"HuggingFace JSON parse failed: {e}")
        raise
    except Exception as e:
        logger.error(f"HuggingFace analysis failed: {e}")
        raise
