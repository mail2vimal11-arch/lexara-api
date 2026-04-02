# LexRisk API — AI-Powered Contract Analysis Engine

Analyze contracts instantly with Claude AI. Extract risks, missing clauses, and actionable recommendations—built for startups, lawyers, and small businesses in Canada.

**Live:** [lexrisk.com](https://lexrisk.com)  
**API Docs:** [api.lexrisk.com/docs](https://api.lexrisk.com/docs)  
**Status:** [status.lexrisk.com](https://status.lexrisk.com)

---

## 🚀 Quick Start

### Installation

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/lexrisk-api.git
cd lexrisk-api

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

### Deploy to FastAPI.com

```bash
git push fastapi main
```

---

## 📚 API Endpoints

### Analyze Contract

```bash
curl -X POST https://api.lexrisk.com/v1/analyze \
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
curl -X POST https://api.lexrisk.com/v1/extract-clauses \
  -H "Authorization: Bearer sk_live_abc123" \
  -d '{"text": "...", "clause_types": ["liability", "termination"]}'
```

### Check Usage

```bash
curl -X GET https://api.lexrisk.com/v1/usage \
  -H "Authorization: Bearer sk_live_abc123"
```

---

## 🏗️ Architecture

- **Backend:** FastAPI (Python 3.11+)
- **AI:** Claude API (Anthropic)
- **Database:** PostgreSQL
- **Cache:** Redis
- **Billing:** Stripe
- **Hosting:** FastAPI.com
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

- **Email:** support@lexrisk.com
- **Discord:** [join.lexrisk.com](https://discord.gg/lexrisk)
- **Docs:** [docs.lexrisk.com](https://docs.lexrisk.com)

---

**Built with ❤️ for Canadian legal professionals**
