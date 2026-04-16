# LexAra API — Project Context

## What This Is
AI-powered contract analysis engine for Canadian law (Ontario jurisdiction).
FastAPI + Claude API (Haiku) backend. Live at lexara.tech / api.lexara.tech.

## Stack
- **Backend**: FastAPI (Python 3.11), PostgreSQL, Redis, Docker
- **AI**: Claude Haiku (primary), SaulLM-7B via HuggingFace (in progress)
- **Hosting**: VPS with Docker Compose + Traefik reverse proxy
- **Repo**: github.com/mail2vimal11-arch/lexara-api
- **Branch**: claude/session-012dsnkany2l4bwt2djexmiv-U1RXA

## Current Work: SaulLM Fine-Tuning
Fine-tuning SaulLM-7B on legal/procurement data to replace Claude API as backend.

### Status
- [x] 186 FAISS-indexed reference clauses (15 categories) in `app/services/reference_data/`
- [x] 48 SACC library entries in `app/services/clause_service.py`
- [x] ~850 training examples across 6 modules (see below)
- [x] Kaggle notebook: `lexara_finetune_saullm.ipynb`
- [x] HuggingFace integration: `app/services/hf_llm_service.py`
- [ ] Kaggle training run in progress (SaulLM-7B, QLoRA, T4 GPU)
- [ ] Upload trained model to HuggingFace: `mail2vimal11-arch/lexara-legal-saullm`
- [ ] Add HF env vars to VPS and restart

### Training Data Modules
| File | Examples | Covers |
|------|----------|--------|
| `reference_data/*.py` | 489 | Clause classification, retrieval, risk |
| `training_scenarios.py` | 6 | 3-step dispute reasoning chains |
| `training_clause_pairs.py` | 14 | Vendor vs customer + metadata extraction |
| `training_drafting_style.py` | 21 | Active voice, deontic logic, CoT |
| `training_preprocessor.py` | 8 | Legalese rewrites, markdown |
| `training_insurance.py` | 15 | Risk→coverage, red flags, SACC |

### Kaggle Notebook Cells (in order)
1. Clone/pull repo + set HF_TOKEN from Kaggle Secrets
2. Install dependencies
3. Generate base training data (489 examples from repo)
4. Load advanced training data (no CUAD/MAUD — removed due to loading script restriction)
5. Load SaulLM-7B with 4-bit quantization
6. Format dataset (train/eval split)
7. Fine-tune with QLoRA (~2 hours on T4)
8. Save LoRA weights
9. Test the model
10. Upload to HuggingFace (needs HF_TOKEN secret in Kaggle)

### After Training: VPS Deploy
```bash
# Add to /opt/lexara-api/.env
HF_API_TOKEN=hf_your_token_here
HF_MODEL_ID=mail2vimal11-arch/lexara-legal-saullm
USE_LOCAL_LLM=true

docker compose restart api
```

## Key Files
| File | Purpose |
|------|---------|
| `app/services/llm_service.py` | Main Claude API calls, HF fallback routing |
| `app/services/hf_llm_service.py` | HuggingFace SaulLM client |
| `app/config.py` | All settings (HF_API_TOKEN, HF_MODEL_ID, USE_LOCAL_LLM) |
| `app/main.py` | FastAPI app, startup (no blocking ingestion) |
| `app/services/reference_data/` | 186 clauses + all training data |
| `lexara_finetune_saullm.ipynb` | Kaggle fine-tuning notebook |
| `lexara_training_data.json` | 489 base training examples (JSON) |
| `docker-compose.yml` | Traefik + API + DB + Redis |

## Analysis Modes (5 tabs in frontend)
- `summary` — plain English contract overview
- `risk_score` — 0-100 score by category
- `key_risks` — top 6 risks with recommendations
- `missing_clauses` — gaps vs jurisdiction standard
- `extract_clauses` — redline revision suggestions

## Known Issues Fixed
- Traefik stream idle timeout (was 30s, now 300s) — fixes Claude API mid-response drops
- Startup blocking ingestion removed from `main.py`
- CUAD/MAUD dataset loaders removed (HF loading script restriction)
