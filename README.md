# MF RAG ChatBot

Facts-only FAQ assistant for **10 ICICI Prudential direct-growth mutual fund schemes**. Answers use official sources only (AMC, AMFI, SEBI)—not investment advice.

> Facts-only. No investment advice.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/context.md](docs/context.md) | Product scope, schemes, compliance rules |
| [docs/scheme-aliases.md](docs/scheme-aliases.md) | Scheme registry, alias catalogue, resolution precedence |
| [docs/architecture.md](docs/architecture.md) | RAG system design |
| [docs/implementation.md](docs/implementation.md) | Phase-wise build plan |
| [docs/ingest-schedule.md](docs/ingest-schedule.md) | Daily 10:00 AM IST refresh (GitHub Actions → Railway) |
| [docs/Deployment-plan.md](docs/Deployment-plan.md) | Production deploy checklist (Railway + Vercel) |
| [docs/railway-ingest.md](docs/railway-ingest.md) | Railway API ingest endpoint + optional Railway cron |
| [docs/edgecases.md](docs/edgecases.md) | QA edge cases and corner scenarios |
| [docs/protester.md](docs/protester.md) | Pro investor QA report (live API testing) |
| [docs/problemstatement.txt](docs/problemstatement.txt) | Original problem statement |

## Requirements

- Python 3.11+

## Setup (Phase 0)

```bash
cd MF_RAG_ChatBot
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # Windows: copy .env.example .env
```

For Phase 1 (ingest / Chroma / **local BGE embeddings**), also install:

```bash
pip install -r requirements-phase1.txt
```

Embeddings use **[BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5)** locally via `sentence-transformers` — no embedding API key. The first ingest or retrieval run downloads the model (~130 MB) from Hugging Face into your local cache.

Configure in `.env` (optional overrides):

```bash
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DEVICE=cpu
VECTOR_DB_PATH=data/chroma
```

## Groq LLM (Phase 2+)

Answer generation uses **[Groq](https://console.groq.com/)** (free tier) — not OpenAI. Embeddings stay local; only chat completion calls Groq.

1. Create a free account at [console.groq.com](https://console.groq.com/)
2. Create an API key at [console.groq.com/keys](https://console.groq.com/keys)
3. Copy `.env.example` to `.env` and set:

```bash
GROQ_API_KEY=gsk_your_key_here
LLM_MODEL=llama-3.3-70b-versatile
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_TEMPERATURE=0.1
```

For Phase 2, also install the OpenAI SDK (Groq uses an OpenAI-compatible API):

```bash
pip install openai>=1.0.0
```

**Do not commit `.env`** — it is gitignored. Never put `GROQ_API_KEY` in code or docs.

## Run API

```bash
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

- Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Metrics snapshot: [http://127.0.0.1:8000/metrics](http://127.0.0.1:8000/metrics) (retrieval hit rate, refusal rate, latency p95)
- OpenAPI docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

`POST /chat` is rate-limited per client IP (default 30 requests/minute; see `CHAT_RATE_LIMIT_PER_MINUTE` in `.env.example`).

For Phase 2+, also install:

```bash
pip install -r requirements-phase2.txt
```

## Deploy: Railway (backend) + Vercel (frontend)

| Layer | Platform | Responsibility |
|-------|----------|----------------|
| **API** | [Railway](https://railway.app/) | FastAPI, Chroma (`data/chroma/`), Groq, ingest |
| **UI** | [Vercel](https://vercel.com/) | Chat UI; calls Railway `/chat` |

### Railway checklist (backend + automatic 10:00 IST refresh)

**Guide:** [docs/railway-ingest.md](docs/railway-ingest.md)

1. **API service** — `railway.toml`, volume at `data/`, `VECTOR_DB_PATH=data/chroma`, `ENABLE_INTERNAL_INGEST=true`, `INGEST_TRIGGER_SECRET=<random>`, `GROQ_API_KEY`, `CORS_ORIGINS`.
2. **Bootstrap** ingest once (shell): `python -m src.ingest --manifest corpus/urls.yaml --no-save-raw`
3. **Cron service** — second service, `railway.ingest.toml`, `INGEST_TRIGGER_URL` → API private URL, same secret.
4. Users get refreshed corpus after each daily cron; check `GET /corpus-status` on the API.

### Vercel checklist (frontend)

1. Create a Vercel project with **root directory** = `frontend/` (when the UI app lives there).
2. Copy [frontend/.env.example](frontend/.env.example) → `.env.local` locally; in Vercel set:
   - `NEXT_PUBLIC_API_BASE_URL` = `https://<your-railway-service>.up.railway.app` (no trailing slash)
3. Deploy `frontend/` per [frontend/README.md](frontend/README.md) and [docs/deployment.md](docs/deployment.md).
4. Open the Vercel URL and confirm chat hits Railway (browser Network tab → `POST .../chat`).
5. If CORS errors appear, add the exact Vercel origin to Railway `CORS_ORIGINS` and redeploy the API.

### Local full-stack dev

| App | URL | Env |
|-----|-----|-----|
| API | `http://127.0.0.1:8000` | repo `.env` |
| UI | `http://localhost:3000` | `frontend/.env.local` with `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000` |

Default `CORS_ORIGINS` already allows `localhost:3000` and `5173`.

## Tests

```bash
pytest
```

### Evaluation (Phase 5)

Golden suites live under `tests/eval/`. Structural scoring checks citation allowlist, sentence caps, footers, and refusal routes.

```bash
# CI-friendly — mocked retriever/LLM (no Groq or Chroma required)
python tests/eval/run_eval.py --suite all --mock

# Live — real index + Groq (requires ingest + GROQ_API_KEY)
python tests/eval/run_eval.py --suite factual --live
```

Release gates ([implementation.md](docs/implementation.md) §8.5):

| Suite | Gate |
|-------|------|
| Factual (`golden_factual.yaml`, 52 cases) | ≥ 85% pass |
| Refusals (`golden_refusals.yaml`) | 100% pass |

Manual spot-check for all 10 schemes: [docs/spot-check.md](docs/spot-check.md).

## Ingest corpus (Phase 1)

Dry-run (fetch + parse + chunk counts; no embed/store):

```bash
python -m src.ingest --manifest corpus/urls.yaml --dry-run
```

Full ingest (embed with **BAAI/bge-small-en-v1.5**, persist to `data/chroma/`):

```bash
python -m src.ingest --manifest corpus/urls.yaml
```

Run logs are written to `corpus/manifests/ingest_*.json`. Re-runs skip unchanged sources by `content_hash`. Use `--force` to re-index after chunker or parser changes.

**Daily refresh at 10:00 AM IST (production):** Railway cron → `POST /internal/ingest` on the API — [docs/railway-ingest.md](docs/railway-ingest.md). GitHub Actions ingest is manual/CI only.

```bash
python -m src.ingest --manifest corpus/urls.yaml --force
```

Single source (debug):

```bash
python -m src.ingest --source-id icici-flexicap-amc-scheme --dry-run
```

## Project layout (Phase 0)

```
corpus/
  schemes.yaml         # 10-scheme registry (aliases: docs/scheme-aliases.md)
  urls.yaml            # Official URL manifest (19 sources)
  coverage-matrix.md   # Scheme × doc_type coverage
  raw/                 # Fetched snapshots (gitignored)
frontend/              # Next.js chat UI (Vercel)
  .env.example         # NEXT_PUBLIC_API_BASE_URL for Vercel
  src/app/             # App Router pages
  src/components/      # Chat, disclaimer, examples, scheme picker
  README.md            # UI contract + deploy notes
docs/
  deployment.md        # Railway + Vercel step-by-step
src/
  api/app.py           # FastAPI application (+ CORS)
  config/settings.py   # Environment configuration
  schemes/registry.py  # Scheme resolution
  retrieval/           # Retriever, intent, assembler
  guardrails/          # Classifier, validator, templates, PII
  llm/                 # Groq client + prompts
  ingest/              # Fetcher, parsers, chunker, embedder, Chroma store, CLI
  logging_config.py    # Structured logging with PII redaction
Procfile               # Railway start command
Dockerfile             # Optional API container (Phase 5)
docker-compose.yml     # API + data/chroma volume
tests/eval/            # Golden YAML + run_eval.py
.github/workflows/     # daily-ingest.yml, eval.yml
```

## Docker (optional)

```bash
docker compose up --build
```

Mount `data/chroma` via the compose volume after running ingest locally or copy an existing index.

## In-scope schemes (10)

| # | Scheme | `scheme_id` |
|---|--------|-------------|
| 1 | ICICI Prudential Large Cap Fund Direct Growth | `icici-large-cap` |
| 2 | ICICI Prudential Manufacturing Fund Direct Growth | `icici-manufacturing` |
| 3 | ICICI Prudential Pharma Healthcare and Diagnostics (P.H.D) Fund | `icici-phd` |
| 4 | ICICI Prudential US Bluechip Equity Fund Direct Growth | `icici-us-bluechip` |
| 5 | ICICI Prudential Multi Asset Fund Direct Growth | `icici-multi-asset` |
| 6 | ICICI Prudential Nifty Auto Index Fund Direct Growth | `icici-nifty-auto` |
| 7 | ICICI Prudential Nifty 50 Index Direct Plan Growth | `icici-nifty-50` |
| 8 | ICICI Prudential Nifty 500 Index Fund Direct Growth | `icici-nifty-500` |
| 9 | ICICI Prudential Nifty Bank Index Fund Direct Growth | `icici-nifty-bank` |
| 10 | ICICI Prudential Nifty Smallcap 250 Index Fund Direct Growth | `icici-nifty-smallcap-250` |

Aliases and resolution rules: [docs/scheme-aliases.md](docs/scheme-aliases.md).

## Known limitations

- **Stale corpus:** Answers reflect the last successful ingest; footer dates show source fetch time. Production refresh: GitHub Actions at 10:00 IST → Railway API (see [docs/ingest-schedule.md](docs/ingest-schedule.md)).
- **10-scheme cap:** Queries about other AMCs or ICICI schemes outside the registry receive an out-of-scope refusal.
- **Index funds:** Nifty index schemes may describe a passive/index mandate rather than a named active manager; wording follows AMC disclosures only.
- **AMC page corpus:** Ingest uses `www.icicipruamc.com` product pages (not separate PDF factsheets); layout changes may require parser updates.
- **No investment advice:** Classifier and validator block recommendations, comparisons, and subjective manager opinions; performance questions link to official sources without return calculations.

## Security & privacy

- No PII fields in the UI; chat input is scanned for PAN/Aadhaar/phone/email patterns.
- User messages are not persisted; logs redact PII-like patterns.
- Secrets (`GROQ_API_KEY`) stay in environment variables only.
- `/chat` rate limiting reduces abuse (configurable per minute).

## Implementation status

| Phase | Status |
|-------|--------|
| 0 — Foundation | Complete |
| 1 — Corpus & ingest | Complete — fetch, parse, chunk, embed, Chroma index, CLI |
| 2 — RAG & API | Complete — `/chat`, Groq, retrieval, validator |
| 3 — Guardrails | Complete — classifier, refusals, PII guard |
| 4 — UI | Complete — Next.js app in `frontend/` (Vercel) |
| 5 — Ops & release | Complete — daily ingest workflow, metrics, eval runner, Docker, README |

See [docs/implementation.md](docs/implementation.md) for details.


# Project deliverables (reference)

Checklist of expected submission artifacts and where they live in this repo. Use this page as a single index; details are inlined or linked below.

| # | Deliverable | Location in repo |
|---|-------------|------------------|
| 1 | Source list (15–25 official URLs) | [§1](#1-source-list-csvmd) — canonical: [`corpus/urls.yaml`](../corpus/urls.yaml), human list: [`docs/MF_URL.md`](MF_URL.md) |
| 2 | README (setup, scope, limits) | [`README.md`](../README.md) — summary in [§2](#2-readme-setup-scope-limits) |
| 3 | Sample Q&A (5–10 queries + answers + links) | [§3](#3-sample-qa) — eval questions: [`tests/eval/golden_factual.yaml`](../tests/eval/golden_factual.yaml) |
| 4 | Disclaimer snippet (UI) | [§4](#4-disclaimer-snippet) — code: [`frontend/src/components/DisclaimerBanner.tsx`](../frontend/src/components/DisclaimerBanner.tsx) |

**Note on URL count:** The problem statement targets **15–25** official URLs (AMC + AMFI + SEBI). The **live ingest manifest** currently lists **10** ICICI Prudential AMC product pages only (`shared_sources: []` in `corpus/urls.yaml`). AMFI/SEBI shared pages are documented in [`docs/context.md`](context.md) but not wired into the active corpus yet.

---

## 1. Source list (CSV/MD)

**Canonical machine-readable manifest:** `corpus/urls.yaml`  
**Human source-of-truth list:** `docs/MF_URL.md`

### Markdown table (10 ingested AMC product pages)

| # | `scheme_id` | Scheme (Direct Growth) | Official URL |
|---|-------------|------------------------|--------------|
| 1 | `icici-large-cap` | ICICI Prudential Large Cap Fund | https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-large-cap-fund/211 |
| 2 | `icici-manufacturing` | ICICI Prudential Manufacturing Fund | https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-manufacturing-fund/1657 |
| 3 | `icici-phd` | ICICI Prudential Pharma Healthcare and Diagnostics (P.H.D) Fund | https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-pharma-healthcare-and-diagnostics--p.h.d-fund/1634 |
| 4 | `icici-us-bluechip` | ICICI Prudential US Bluechip Equity Fund | https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-us-bluechip-equity-fund/437 |
| 5 | `icici-multi-asset` | ICICI Prudential Multi Asset Fund | https://www.icicipruamc.com/mutual-fund/hybrid-funds/icici-prudential-multi-asset-fund/55 |
| 6 | `icici-nifty-auto` | ICICI Prudential Nifty Auto Index Fund | https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-auto-index-fund/1851 |
| 7 | `icici-nifty-50` | ICICI Prudential Nifty 50 Index Fund | https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-50-index-fund/57 |
| 8 | `icici-nifty-500` | ICICI Prudential Nifty 500 Index Fund | https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-500-index-fund/1884 |
| 9 | `icici-nifty-bank` | ICICI Prudential Nifty Bank Index Fund | https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-bank-index-fund/1839 |
| 10 | `icici-nifty-smallcap-250` | ICICI Prudential Nifty Smallcap 250 Index Fund | https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-smallcap-250-index-fund/1828 |

### CSV (copy-paste)

```csv
scheme_id,scheme_name,url,doc_type,domain
icici-large-cap,ICICI Prudential Large Cap Fund Direct Growth,https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-large-cap-fund/211,amc_product_page,icicipruamc.com
icici-manufacturing,ICICI Prudential Manufacturing Fund Direct Growth,https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-manufacturing-fund/1657,amc_product_page,icicipruamc.com
icici-phd,ICICI Prudential PHD Fund Direct Growth,https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-pharma-healthcare-and-diagnostics--p.h.d-fund/1634,amc_product_page,icicipruamc.com
icici-us-bluechip,ICICI Prudential US Bluechip Equity Fund Direct Growth,https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-us-bluechip-equity-fund/437,amc_product_page,icicipruamc.com
icici-multi-asset,ICICI Prudential Multi Asset Fund Direct Growth,https://www.icicipruamc.com/mutual-fund/hybrid-funds/icici-prudential-multi-asset-fund/55,amc_product_page,icicipruamc.com
icici-nifty-auto,ICICI Prudential Nifty Auto Index Fund Direct Growth,https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-auto-index-fund/1851,amc_product_page,icicipruamc.com
icici-nifty-50,ICICI Prudential Nifty 50 Index Fund Direct Growth,https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-50-index-fund/57,amc_product_page,icicipruamc.com
icici-nifty-500,ICICI Prudential Nifty 500 Index Fund Direct Growth,https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-500-index-fund/1884,amc_product_page,icicipruamc.com
icici-nifty-bank,ICICI Prudential Nifty Bank Index Fund Direct Growth,https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-bank-index-fund/1839,amc_product_page,icicipruamc.com
icici-nifty-smallcap-250,ICICI Prudential Nifty Smallcap 250 Index Fund Direct Growth,https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-smallcap-250-index-fund/1828,amc_product_page,icicipruamc.com
```

**Policy:** Ingest and citations use **only** `www.icicipruamc.com` pages above. No Groww, blogs, or third-party aggregators as corpus sources.

---

## 2. README (setup, scope, limits)

**Full document:** [`README.md`](../README.md)

### Setup (condensed)

1. **Python env:** `python -m venv .venv` → activate → `pip install -r requirements.txt` (+ `requirements-phase1.txt` for ingest, `requirements-phase2.txt` for chat).
2. **Config:** `cp .env.example .env` — set `GROQ_API_KEY`, optional `EMBEDDING_*`, `VECTOR_DB_PATH=data/chroma`.
3. **Ingest:** `python -m src.ingest --manifest corpus/urls.yaml` (BGE embeddings local; first run downloads model).
4. **API:** `uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload`
5. **UI:** `cd frontend` → `cp .env.example .env.local` → `npm install` → `npm run dev` → `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`
6. **Production:** Railway (API + Chroma volume + daily ingest) + Vercel (`frontend/`) — see [`docs/deployment.md`](deployment.md), [`docs/railway-ingest.md`](railway-ingest.md).

### Scope (AMC + schemes)

| Item | Value |
|------|--------|
| **AMC** | ICICI Prudential Mutual Fund |
| **Plans** | Direct Growth only (10 schemes) |
| **Registry** | `corpus/schemes.yaml` — aliases in [`docs/scheme-aliases.md`](scheme-aliases.md) |
| **Topics** | Expense ratio, exit load, min SIP, benchmark, fund management / index mandate, holdings (where on AMC page) |
| **Out of scope** | Other AMCs, schemes outside the 10, investment advice, performance comparisons, PII |

### Known limitations (from README)

- **Stale corpus** — Answers reflect last successful ingest; footer shows source fetch date. Production refresh: daily 10:00 IST (GitHub Actions / Railway).
- **10-scheme cap** — Other ICICI or non-ICICI schemes → out-of-scope refusal.
- **Index funds** — Passive/index mandate wording; not active-manager opinions.
- **AMC HTML only** — No separate PDF factsheets in live manifest; AMC layout changes may need parser updates.
- **No advice** — Classifier/validator block recommendations, subjective opinions, and return calculations.
- **QA caveats** — See [`docs/protester.md`](protester.md): multi-scheme tables, “list all funds”, and comparison-without-“compare” are known weak spots.

---

## 3. Sample Q&A

Representative queries with **answer shape** and **Official source** links (UI shows link via `citation_url`, not raw URLs in prose). Exact numbers change when AMC pages update — re-verify after ingest.

| # | User query | `scheme_id` | Assistant answer (summary) | Official source |
|---|------------|-------------|----------------------------|-----------------|
| 1 | What is the expense ratio of the Large Cap Fund? | `icici-large-cap` | Short factual TER for Direct Growth plan from AMC page; ≤3 sentences; footer `Last updated from sources: YYYY-MM-DD`. | https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-large-cap-fund/211 |
| 2 | What is the exit load for the Multi Asset Fund? | `icici-multi-asset` | Exit load terms as stated on AMC product page (e.g. redemption within stated period). | https://www.icicipruamc.com/mutual-fund/hybrid-funds/icici-prudential-multi-asset-fund/55 |
| 3 | Who manages the Manufacturing Fund? | `icici-manufacturing` | Names / roles from official fund-management disclosure on AMC page. | https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-manufacturing-fund/1657 |
| 4 | What are the top holdings in the bank index fund? | `icici-nifty-bank` | Listed holdings and weights from AMC page (bank names where disclosed). | https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-bank-index-fund/1839 |
| 5 | What is the minimum SIP for US Bluechip? | `icici-us-bluechip` | Minimum SIP / investment amount from AMC page. | https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-us-bluechip-equity-fund/437 |
| 6 | Who manages the Nifty 50 Index Fund? | `icici-nifty-50` | Index/passive mandate or disclosed manager text per AMC (no performance opinion). | https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-50-index-fund/57 |
| 7 | Should I invest in the Large Cap Fund? | — | **Refusal** (`advisory`): facts-only assistant; no investment advice. No numeric recommendation. | — |
| 8 | What was the 3 year return of Large Cap? | `icici-large-cap` | **Refusal** (`performance`): no return calculation; may point to official AMC page for disclosures. | https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-large-cap-fund/211 |
| 9 | What is HDFC Flexi Cap expense ratio? | — | **Refusal** (`out_of_scope`): only 10 ICICI Prudential Direct Growth schemes covered. | — |
| 10 | Compare expense ratio of Multi Asset and Nifty 500 | — | **Refusal** (`advisory`) when phrased as comparison; see [`docs/protester.md`](protester.md) for edge cases without the word “compare”. | — |

**UI example chips (auto-send on click):** same as rows 1–3 — [`frontend/src/data/examples.ts`](../frontend/src/data/examples.ts).

**Regenerate live samples:** API up → `POST http://127.0.0.1:8000/chat` with `{"message":"...","scheme_id":"..."}` or use the Vercel UI; manual gate: [`docs/spot-check.md`](spot-check.md).

---

## 4. Disclaimer snippet

**Exact UI copy** (sticky banner):

> **Facts-only. No investment advice.**

**Implementation:**

```tsx
// frontend/src/components/DisclaimerBanner.tsx
<span>Facts-only. No investment advice.</span>
```

Also echoed at the top of [`README.md`](../README.md) and in [`docs/context.md`](context.md) (Canonical Disclaimer).

---

## Quick file map

```
README.md                 # Setup, deploy, 10 schemes, known limitations
corpus/urls.yaml          # Ingest + citation allowlist
docs/MF_URL.md            # Human URL list (source of truth)
docs/deliverables.md      # This file
docs/spot-check.md        # Manual Q&A checklist per scheme
tests/eval/golden_*.yaml  # Automated factual + refusal cases
frontend/.../DisclaimerBanner.tsx
```

