# ADR-001: SaulLM as Primary Inference Model with Claude as Failover

- Status: Accepted
- Date: 2026-04-18
- Deciders: Josephine (founder), Solution Architect Agent

---

## Context

Lexara.tech is a Canadian contract analysis API with 5 analysis modes (summary, risk_score,
key_risks, missing_clauses, extract_clauses). The existing inference layer in
`app/services/llm_service.py` already implements a HuggingFace-first waterfall with Claude
as fallback. The Anthropic spend limit has been reached and will not reset until May 1. The
fine-tuned model (`mail2vimal11-arch/lexara-legal-saullm`) does not yet exist — only the
Kaggle training notebook and 600 examples are ready. The site must launch today. The base
model `Equall/Saul-7B-Instruct-v1` is publicly available on HuggingFace Inference API right
now.

Constraints:
- No GPU on VPS (Hostinger KVM4 is CPU-only VPS — not viable for 7B model inference)
- Claude is blocked until May 1
- Fine-tuned model is at least 1–2 days away even if training starts immediately on Kaggle
- Zero-cost launch is strongly preferred

---

## Decision

We will point `HF_MODEL_ID` at `Equall/Saul-7B-Instruct-v1` (the base SaulLM model) on
HuggingFace Serverless Inference today. We will set `USE_LOCAL_LLM=true`. Claude remains
wired as the fallback but will 4xx on every call until May 1, which is acceptable — the
waterfall will log the failure and surface the HuggingFace result. When the fine-tuned model
is ready, we swap `HF_MODEL_ID` to `mail2vimal11-arch/lexara-legal-saullm` with a single
env-var change and container restart.

---

## Options Considered

### Option A: Base SaulLM via HuggingFace Serverless Inference (free tier)
Use `Equall/Saul-7B-Instruct-v1` on HF Serverless API with a free HF token.

- Pros:
  - Available right now, zero infra cost
  - Saul-7B is pre-trained on 30B tokens of legal text (EDGAR, EU law, case law) — better
    legal domain alignment than a general 7B model
  - Instruction-tuned variant (`-Instruct-v1`) means it already follows structured prompts
  - Hot-swap path to fine-tuned model is trivial (env var)
  - All existing HF client code works unchanged
- Cons:
  - HF Serverless free tier has cold starts: model goes idle after ~15 min of no traffic,
    first request after idle returns 503 with an `estimated_time` field (typically 20–80 sec)
  - Free tier rate limits (roughly 1000 req/day per token for large models; SaulLM 7B may be
    throttled faster)
  - Base model has no Lexara-specific fine-tuning — JSON schema compliance depends entirely
    on prompt engineering, which is already done in `hf_llm_service.py`
  - 7B models reliably emit valid JSON only ~70-80% of the time without fine-tuning; the
    existing JSON extraction logic (strip fences, find `{` / `}`) handles partial failures
    but will not recover from hallucinated schemas
- Fit with existing system: Perfect — the waterfall and HF client are already written for
  exactly this model family and format
- Reversibility: Two-way door. Revert by setting `USE_LOCAL_LLM=false`

### Option B: HuggingFace Inference Endpoints (dedicated, paid)
Spin up a dedicated endpoint for SaulLM 7B at ~$0.60/hr on HF GPU hardware.

- Pros:
  - No cold starts, consistent latency (~3–6 sec per request on T4)
  - Higher rate limits
- Cons:
  - ~$14/day even at idle; ~$430/month if left running
  - Requires HF Inference Endpoints setup (not instant — account approval can take hours)
  - Overkill for launch-day traffic volume (likely single-digit concurrent users)
  - Does not solve the quality gap vs fine-tuned model
- Fit with existing system: Drop-in (same HF API URL structure)
- Reversibility: Two-way door. Can shut down endpoint and revert

### Option C: Self-host SaulLM on VPS
Run the 7B model on the Hostinger KVM4 VPS using llama.cpp or Ollama with CPU inference.

- Pros:
  - No per-request cost after initial setup
  - No cold starts once loaded
- Cons:
  - KVM4 has no GPU. SaulLM-7B in 4-bit quantization requires ~5–6 GB RAM and takes
    40–120 seconds per inference request on CPU — completely unusable for a web product
  - Would need to load the model into the same container as the FastAPI app, replacing the
    thin HF API client with a heavy runtime
  - Risks OOM-killing the Postgres and Redis containers that share the VPS
- Fit with existing system: Requires significant new code (replace hf_llm_service.py entirely)
- Reversibility: One-way door effectively — lots of work to undo

### Option D: Wait for Claude spend reset (May 1)
Do nothing and launch after May 1.

- Pros: Claude quality is proven, JSON compliance is near-perfect
- Cons: 13-day delay. This is a non-starter given the stated requirement.
- Reversibility: N/A

---

## Rationale

Option A is the only choice that satisfies today's launch constraint with no new code and
zero cost. Option B costs money the project does not need to spend at launch volume. Option C
is technically infeasible on the VPS hardware. Option D misses the launch date entirely.

The quality risk of base SaulLM is real but bounded: Saul-7B-Instruct is the strongest
openly-available legal-domain 7B model. The prompts in `hf_llm_service.py` are tight
(they specify exact JSON schemas and field names). The existing JSON extraction code in both
services is defensive. The biggest risk is the 503 cold start — addressed below under
consequences.

---

## Consequences

**Positive:**
- Site launches today with no additional cost
- Fine-tuned model swap requires zero code changes (env var only)
- Base SaulLM quality is genuinely better than a general-purpose 7B for legal text — it
  understands Ontario/Canadian contract concepts without prompting
- When Claude resets on May 1, the system automatically improves: Claude will service
  the fallback path correctly

**Negative:**
- Cold start 503s: the first request after ~15 min of idle will fail over to Claude (which
  also fails), resulting in a 500 to the user. This is a real UX problem.
  **Mitigation:** Add a warm-up poller — see Code Changes Required below.
- JSON schema compliance ~70–80% for base model. The extract_clauses and key_risks modes
  (more complex schemas) are the highest-risk endpoints. Some requests will fail JSON parsing
  and return 500s.
  **Mitigation:** The `analyze_with_huggingface` function already has try/except on
  JSONDecodeError and re-raises — the router catches it and returns HTTP 500. This is
  acceptable until fine-tuning is done.
- HF free tier rate limit: if traffic exceeds ~50–100 requests/hour on a 7B model, HF will
  429. Monitor and upgrade to PRO ($9/mo) or Inference Endpoints if this becomes an issue.

**Neutral:**
- `tokens_used` will report 0 for HF requests (HF free tier doesn't return token counts) —
  this is cosmetic, already hard-coded in `hf_llm_service.py` line 157
- The `model` field in responses will say "lexara-legal-saullm" even though we're using the
  base model — update this string if you want accurate attribution

---

## Code Changes Required

The existing code is structurally sufficient. Two targeted changes are needed:

### Change 1 — Fix the cold-start 503 handling (CRITICAL for launch)

Current behavior (`hf_llm_service.py` line 128–131): on 503, raises `Exception("Model
loading")`, which triggers the Claude fallback, which also fails, yielding a 500 to the user.

Required behavior: On 503, retry after the `estimated_time` the HF API advertises, up to
once, before raising.

Add this block to `hf_llm_service.py` after the `response = await client.post(...)` line:

```python
if response.status_code == 503:
    body = response.json() if response.headers.get("content-type","").startswith("application/json") else {}
    wait_sec = min(body.get("estimated_time", 30), 60)
    logger.warning(f"HuggingFace model loading, retrying in {wait_sec}s")
    await asyncio.sleep(wait_sec)
    response = await client.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"HuggingFace still not ready after retry: {response.status_code}")
```

Add `import asyncio` at the top of `hf_llm_service.py`.

The httpx client timeout is already 120 seconds, which is sufficient to absorb a 60-second
retry wait.

### Change 2 — Add a warm-up endpoint or startup ping (RECOMMENDED)

Add a FastAPI startup event that fires a no-op request to the HF model at container boot,
so the model is warm before the first real user request. This is a single async GET to the
HF model status URL.

Alternatively, configure a cron/healthcheck that hits `/contracts/summary` with a trivial
test payload every 10 minutes to prevent the model going idle.

The simplest option on the VPS: add to `docker-compose.yml`:

```yaml
  hf-warmer:
    image: curlimages/curl:latest
    restart: always
    entrypoint: >
      sh -c "while true; do
        curl -s -o /dev/null -X POST
          https://api-inference.huggingface.co/models/Equall/Saul-7B-Instruct-v1
          -H 'Authorization: Bearer $HF_API_TOKEN'
          -H 'Content-Type: application/json'
          -d '{\"inputs\": \"ping\"}';
        sleep 600;
      done"
    env_file: .env
    networks:
      - internal
```

This costs nothing and keeps the model warm at HF by pinging it every 10 minutes.

---

## Env Vars Required on VPS .env

Add exactly these three lines to the `.env` file on the VPS. No other changes needed.

```
USE_LOCAL_LLM=true
HF_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
HF_MODEL_ID=Equall/Saul-7B-Instruct-v1
```

`CLAUDE_API_KEY` must remain set (even if exhausted) because `claude_api_key: str` in
`config.py` is a required field with no default — removing it will cause pydantic to fail
at startup.

---

## Fine-Tuned Model Swap Procedure

When `mail2vimal11-arch/lexara-legal-saullm` is published to HuggingFace after Kaggle
training:

1. On the VPS, edit `.env`: change `HF_MODEL_ID=Equall/Saul-7B-Instruct-v1` to
   `HF_MODEL_ID=mail2vimal11-arch/lexara-legal-saullm`
2. Run `docker compose up -d --no-deps api` (restarts only the API container, zero
   downtime on the website/db/redis)
3. Confirm with one test request to `POST /contracts/summary`

No code changes. No redeployment via GitHub pipeline needed (env var is injected at
container runtime from the `.env` file).

The prompt format in `hf_llm_service.py` already uses the `### Instruction: / ### Input: /
### Response:` format which is the standard Alpaca fine-tuning format — this is the correct
format for the fine-tuned model once trained.

---

## Risk Assessment: Base SaulLM vs Fine-Tuned vs Claude

| Dimension | Claude (blocked) | Base SaulLM-7B | Fine-Tuned SaulLM |
|---|---|---|---|
| JSON schema compliance | ~99% | ~70-80% | ~90-95% |
| Canadian contract knowledge | High (training data) | High (legal pretraining) | High + task-tuned |
| Ontario-specific clauses | Good | Good | Best |
| Latency (warm) | 3–5 sec | 4–8 sec | 4–8 sec |
| Latency (cold start) | None | 20–80 sec (503) | 20–80 sec (503) |
| Cost | ~$0.01/req | Free (within limits) | Free (within limits) |
| Quality of extract_clauses | Excellent | Acceptable | Good |
| Quality of risk_score | Excellent | Good | Very Good |

Assessment: Base SaulLM is **acceptable for launch**. It is a legal-domain specialist model
and will produce substantively correct output for simple contracts (NDAs, service agreements).
Complex multi-party commercial contracts or Ontario-specific regulatory clauses are where
quality will degrade most noticeably. For an early-launch product with a small user base,
this is an acceptable tradeoff.

The highest-risk mode is `extract_clauses` — it requires generating `original` + `revised`
clause text and a structured array with 5 fields per clause. This is where a base 7B model
is most likely to either truncate or hallucinate field names. If pre-launch testing shows
consistent failures on this endpoint, consider temporarily disabling it (return a 503
"coming soon" response) and launching with the other 4 modes only.

---

## Revisit Triggers

- Fine-tuned model becomes available on HuggingFace → swap `HF_MODEL_ID`, re-evaluate JSON
  compliance rate after 50 real requests
- Claude spend resets May 1 → decide whether to keep SaulLM as primary or revert to Claude
  primary (Claude primary is higher quality; SaulLM primary is lower cost — this is a
  business decision)
- HF free tier 429 rate limiting observed in production → upgrade to HF PRO ($9/mo) or
  dedicated Inference Endpoint
- User reports of obviously wrong risk scores or hallucinated clause text → disable
  extract_clauses endpoint, accelerate fine-tuning

---

## References

- Saul-7B model card: https://huggingface.co/Equall/Saul-7B-Instruct-v1
- SaulLM paper (legal LLM pretraining methodology): https://arxiv.org/abs/2403.03883
- HuggingFace Serverless Inference rate limits: https://huggingface.co/docs/api-inference/rate-limits
- HuggingFace Inference Endpoints pricing: https://huggingface.co/docs/inference-endpoints/pricing
- Existing waterfall code: `app/services/llm_service.py` lines 29–38
- HF client with cold-start handling: `app/services/hf_llm_service.py` lines 124–131
