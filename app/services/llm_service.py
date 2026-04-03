"""Claude AI service for contract analysis."""

import httpx
import json
import logging
from typing import Optional, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

LEGAL_ANALYSIS_SYSTEM_PROMPT = """You are a legal document analyzer specializing in Canadian contract law, particularly Ontario jurisdiction. Your role is to identify legal risks, missing protections, and problematic clauses in contracts.

CRITICAL CONSTRAINTS:
1. You do NOT provide legal advice. You provide informational analysis only.
2. You cite only publicly accessible legal sources (CanLII, Ontario Courts, Supreme Court of Canada).
3. All analysis is for informational purposes and not a substitute for legal advice.
4. Always include this disclaimer in responses.

OUTPUT REQUIREMENTS:
- Always return valid JSON matching the provided schema.
- Severity levels: "critical", "high", "medium", "low".
- Include specific section references where applicable.
- Provide actionable recommendations.
- Flag all assumptions or ambiguities.

LEGAL DISCLAIMER:
This analysis is provided for informational purposes only and does NOT constitute legal advice. The information provided should not be relied upon to make business or legal decisions. All analysis is based on general principles of Canadian and Ontario contract law. Specific legal advice must be obtained from a qualified legal professional licensed to practice in your jurisdiction.
"""


async def analyze_with_claude(
    text: str,
    contract_type: str = "auto",
    jurisdiction: str = "ON",
    include_recommendations: bool = True,
    mode: str = "full_analysis"
) -> Dict[str, Any]:
    """
    Analyze contract with Claude API.
    
    Args:
        text: Contract text to analyze
        contract_type: Type of contract (service_agreement, nda, employment, etc.)
        jurisdiction: Legal jurisdiction (ON, CA, etc.)
        include_recommendations: Whether to include recommendations
        mode: Analysis mode (full_analysis, extract_clauses, risk_score)
    
    Returns:
        Analysis result with risks, missing clauses, and recommendations
    """
    
    if mode == "full_analysis":
        prompt = _build_full_analysis_prompt(text, contract_type, jurisdiction, include_recommendations)
    elif mode == "extract_clauses":
        prompt = _build_clause_extraction_prompt(text)
    elif mode == "risk_score":
        prompt = _build_risk_score_prompt(text)
    else:
        prompt = _build_full_analysis_prompt(text, contract_type, jurisdiction, include_recommendations)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.claude_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-haiku-4-5",
                    "max_tokens": 2000,
                    "system": LEGAL_ANALYSIS_SYSTEM_PROMPT,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Claude API error: {response.text}")
                raise Exception(f"Claude API error: {response.status_code}")
            
            result = response.json()
            tokens_used = result["usage"]["output_tokens"]
            
            # Extract JSON from response
            content = result["content"][0]["text"]
            
            try:
                # Try to parse JSON from response
                # Claude might wrap it in markdown code blocks
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                else:
                    json_str = content
                
                analysis = json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse Claude response as JSON: {content[:200]}")
                analysis = {
                    "summary": content,
                    "confidence": 0.7,
                    "tokens_used": tokens_used
                }
            
            analysis["tokens_used"] = tokens_used
            return analysis
    
    except Exception as e:
        logger.error(f"Claude analysis failed: {e}", exc_info=True)
        raise


def _build_full_analysis_prompt(text: str, contract_type: str, jurisdiction: str, include_recommendations: bool) -> str:
    """Build prompt for full contract analysis."""
    
    return f"""Analyze this {contract_type} contract for legal risks:

CONTRACT TEXT:
{text[:8000]}

JURISDICTION: {jurisdiction}
CONTRACT_TYPE: {contract_type}

Please provide analysis in JSON format with the following structure:
{{
  "summary": "Brief overview of the contract",
  "key_risks": [
    {{
      "severity": "high",
      "title": "Risk title",
      "description": "Detailed description",
      "section": "Section reference",
      "recommendation": "How to fix"
    }}
  ],
  "missing_clauses": [
    {{
      "clause": "Clause name",
      "importance": "critical/high/medium/low",
      "rationale": "Why it's needed"
    }}
  ],
  "risk_score": 0-100,
  "confidence": 0.0-1.0
}}

Focus on:
1. Liability exposure (capped vs unlimited)
2. Data protection (PIPEDA compliance if applicable)
3. Termination rights (notice periods, cause requirements)
4. IP ownership (assignments, restrictions)
5. Warranties and representations
6. Indemnification obligations

Include a DISCLAIMER that this is informational, not legal advice.
"""


def _build_clause_extraction_prompt(text: str) -> str:
    """Build prompt for clause extraction."""
    
    return f"""Extract and categorize clauses from this contract:

CONTRACT TEXT:
{text[:8000]}

Return JSON with structure:
{{
  "clauses": [
    {{
      "type": "liability|termination|confidentiality|warranty|ip|indemnification",
      "section": "Section reference",
      "summary": "Brief summary",
      "confidence": 0.95
    }}
  ]
}}
"""


def _build_risk_score_prompt(text: str) -> str:
    """Build prompt for risk scoring."""
    
    return f"""Score legal risk for this contract on a 0-100 scale:

CONTRACT TEXT:
{text[:8000]}

Categories:
- liability: Exposure to damages
- data_protection: PIPEDA / privacy compliance
- termination: Unfavorable exit clauses
- ip_ownership: IP assignment risks
- warranty: Warranty disclaimers

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
  "interpretation": "Plain-English explanation"
}}
"""
