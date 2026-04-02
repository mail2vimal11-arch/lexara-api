# LexRisk API Reference

Complete API documentation for LexRisk contract analysis engine.

**Base URL:** `https://api.lexrisk.com/v1`

---

## Authentication

All API requests require a valid API key in the Authorization header:

```bash
curl https://api.lexrisk.com/v1/analyze-contract \
  -H "Authorization: Bearer sk_live_YOUR_API_KEY"
```

---

## Analyze Contract

**Endpoint:** `POST /analyze-contract`

Analyze any contract for legal risks, missing clauses, and recommendations.

### Request

```json
{
  "text": "Full contract text here...",
  "contract_type": "service_agreement",
  "jurisdiction": "ON",
  "include_recommendations": true
}
```

**Parameters:**
- `text` (required): Contract text (100-50,000 characters)
- `contract_type` (optional): Type of contract
  - `service_agreement`
  - `nda`
  - `employment`
  - `license`
  - `vendor`
  - `auto` (auto-detect)
- `jurisdiction` (optional): Legal jurisdiction
  - `ON` (Ontario)
  - `CA` (Canada)
  - Default: `ON`
- `include_recommendations` (optional): Include actionable recommendations. Default: `true`

### Response

```json
{
  "analysis_id": "anal_5f8c9d3e2a1b4",
  "backend": "claude",
  "summary": "Software-as-a-Service Agreement providing cloud services...",
  "confidence": 0.92,
  "tokens_used": 1850,
  "risk_score": 72,
  "key_risks": [
    {
      "severity": "high",
      "title": "Unlimited Liability",
      "description": "Contract does not cap liability for indirect damages.",
      "section": "Section 8.2",
      "recommendation": "Add liability cap: 'Liability shall not exceed 12 months of fees paid.'"
    },
    {
      "severity": "medium",
      "title": "Termination Notice Period",
      "description": "Vendor may terminate with 30 days' notice without cause.",
      "section": "Section 5.1",
      "recommendation": "Negotiate longer notice period (90 days) or require cause for termination."
    }
  ],
  "missing_clauses": [
    {
      "clause": "Data Protection (PIPEDA Compliance)",
      "importance": "critical",
      "rationale": "Contract handles personal data. Must include PIPEDA compliance obligations."
    },
    {
      "clause": "Limitation of Liability",
      "importance": "high",
      "rationale": "No cap on damages. Standard practice is 12 months of fees."
    }
  ],
  "processing_time_ms": 2300,
  "cost_cents": 3
}
```

---

## Extract Clauses

**Endpoint:** `POST /extract-clauses`

Extract and categorize specific clauses from a contract.

### Request

```json
{
  "text": "Contract text...",
  "clause_types": ["liability", "termination", "confidentiality"]
}
```

### Response

```json
{
  "analysis_id": "anal_5f8c9d3e2a1b4",
  "clauses": [
    {
      "type": "liability",
      "section": "Section 8",
      "summary": "Liability capped at 12 months of fees for direct damages...",
      "confidence": 0.98
    },
    {
      "type": "termination",
      "section": "Section 5",
      "summary": "Either party may terminate with 30 days' notice...",
      "confidence": 0.95
    }
  ],
  "tokens_used": 920
}
```

---

## Calculate Risk Score

**Endpoint:** `POST /risk-score`

Get a quantified risk score (0-100) for a contract.

### Request

```json
{
  "text": "Contract text...",
  "weighting": {
    "liability": 0.25,
    "data_protection": 0.30,
    "termination": 0.15,
    "ip_ownership": 0.20,
    "warranty": 0.10
  }
}
```

### Response

```json
{
  "overall_risk_score": 72,
  "risk_level": "high",
  "scores_by_category": {
    "liability": 85,
    "data_protection": 60,
    "termination": 55,
    "ip_ownership": 90,
    "warranty": 40
  },
  "interpretation": "This contract presents elevated risk, primarily due to unlimited IP assignment and uncapped liability.",
  "tokens_used": 1200
}
```

---

## Check Usage

**Endpoint:** `GET /usage`

View your current API usage and quota.

### Response

```json
{
  "plan": "growth",
  "analyses_used_this_month": 150,
  "analyses_limit": 500,
  "remaining_quota": 350,
  "reset_date": "2026-05-01T00:00:00Z",
  "overage_cost_per_analysis": 0.12,
  "estimated_overage_charges": 0.00,
  "next_billing_date": "2026-05-01T00:00:00Z"
}
```

---

## Health Check

**Endpoint:** `GET /health`

Check API status.

### Response

```json
{
  "status": "healthy",
  "timestamp": "2026-04-02T11:27:49Z",
  "version": "1.0.0"
}
```

---

## Error Handling

All errors return JSON with an error code and message:

```json
{
  "error": "invalid_request",
  "message": "Contract text exceeds 50,000 characters.",
  "request_id": "req_abc123"
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `invalid_request` | 400 | Invalid request parameters |
| `unauthorized` | 401 | Invalid or missing API key |
| `rate_limited` | 429 | Too many requests |
| `internal_error` | 500 | Internal server error |

---

## Rate Limiting

Rate limits are per plan:

| Plan | Limit |
|------|-------|
| Free | 1 req/sec |
| Starter | 5 req/sec |
| Growth | 10 req/sec |
| Business | 20 req/sec |

Rate limit info is in response headers:
- `X-RateLimit-Limit`: Requests per second
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets

---

## Examples

### Python

```python
import requests

api_key = "sk_live_YOUR_API_KEY"
headers = {"Authorization": f"Bearer {api_key}"}

response = requests.post(
    "https://api.lexrisk.com/v1/analyze-contract",
    headers=headers,
    json={
        "text": "Full contract text...",
        "contract_type": "service_agreement"
    }
)

result = response.json()
print(f"Risk Score: {result['risk_score']}")
for risk in result['key_risks']:
    print(f"- {risk['title']} ({risk['severity']})")
```

### JavaScript

```javascript
const apiKey = "sk_live_YOUR_API_KEY";

const response = await fetch("https://api.lexrisk.com/v1/analyze-contract", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${apiKey}`,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    text: "Full contract text...",
    contract_type: "service_agreement"
  })
});

const result = await response.json();
console.log(`Risk Score: ${result.risk_score}`);
```

---

## Support

- **Docs:** [docs.lexrisk.com](https://docs.lexrisk.com)
- **Email:** support@lexrisk.com
- **Discord:** [join.lexrisk.com](https://discord.gg/lexrisk)
