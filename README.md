# LexAra — AI-Powered Contract Analysis Engine

Analyze contracts instantly with Claude AI. Extract risks, missing clauses, and actionable recommendations—built for startups, lawyers, and small businesses in Canada.

**Live:** [lexara.tech](https://lexara.tech)  
**API Docs:** [api.lexara.tech/docs](https://api.lexara.tech/docs)  
**Status:** [status.lexara.tech](https://status.lexara.tech)

---

## 🚀 Quick Start

### Installation

```bash
# Clone
git clone https://github.com/mail2vimal11-arch/lexara-api.git
cd lexara-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Run Locally

```bash
# Development server (auto-reload)
python -m uvicorn app.main:app --reload

# Navigate to http://localhost:8000/docs for interactive API docs
```

### Deploy

```bash
# Automated: push to main → deploy.yml runs tests, builds the image to GHCR,
# and rolls the api service on the VPS (deploy is gated on tests passing).
# Manual fallback: see CLAUDE.md → Deploy Workflow.
```

---

## 📚 API Endpoints

### Analyze Contract

```bash
curl -X POST https://api.lexara.tech/v1/analyze \
  -H "Authorization: Bearer sk_live_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This Agreement...",
    "contract_type": "service_agreement",
    "jurisdiction": "ON"
  }'
```

**Response:**
```json
{
  "analysis_id": "anal_5f8c9d3e2a1b4",
  "backend": "claude",
  "summary": "Software-as-a-Service Agreement with 2-year term...",
  "risk_score": 72,
  "key_risks": [
    {
      "severity": "high",
      "title": "Unlimited Liability",
      "section": "Section 8.2",
      "recommendation": "Cap liability at 12 months of fees"
    }
  ],
  "processing_time_ms": 2300,
  "tokens_used": 1850
}
```

### Extract Clauses

```bash
curl -X POST https://api.lexara.tech/v1/extract-clauses \
  -H "Authorization: Bearer sk_live_abc123" \
  -d '{"text": "...", "clause_types": ["liability", "termination"]}'
```

### Check Usage

```bash
curl -X GET https://api.lexara.tech/v1/usage \
  -H "Authorization: Bearer sk_live_abc123"
```

---

## 🏗️ Architecture

- **Backend:** FastAPI (Python 3.11+)
- **AI:** Claude API (Anthropic)
- **Database:** PostgreSQL
- **Cache:** Redis
- **Billing:** Stripe
- **Hosting:** Docker Compose + Traefik on a VPS
- **CI/CD:** GitHub Actions

---

## 📖 Documentation

- [API Reference](./docs/API.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)
- [Pricing & Plans](./docs/PRICING.md)
- [Contributing](./CONTRIBUTING.md)

---

## 💳 Pricing

| Plan | Price | Analyses/mo | Features |
|------|-------|------------|----------|
| **Free** | $0 | 5 | Basic analysis |
| **Starter** | $19/mo | 50 | Full legal analysis |
| **Growth** | $59/mo | 500 | API + webhooks |
| **Business** | $199/mo | ∞ | Dedicated support |

[View full pricing →](./docs/PRICING.md)

---

## 🔐 Security & Privacy

- **PIPEDA Compliant:** No contract storage by default
- **Encryption:** TLS 1.3 in transit, AES-256 at rest
- **Compliance:** Ontario contract law, AODA accessible design

[Privacy Policy](./docs/PRIVACY.md) | [Security](./docs/SECURITY.md)

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## 📄 License

MIT License — See [LICENSE](./LICENSE) for details

---

## 📞 Support

- **Email:** support@lexara.tech
- **Docs:** [api.lexara.tech/docs](https://api.lexara.tech/docs)

---

**Built with ❤️ for Canadian legal professionals**
