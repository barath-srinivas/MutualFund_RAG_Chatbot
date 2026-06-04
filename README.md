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
