# Project Context: Mutual Fund FAQ Assistant

## Purpose

Build a **facts-only** FAQ assistant for mutual fund schemes, using **Groww** as the reference product context. The assistant answers objective, verifiable questions by retrieving information **only** from official public sources (AMC websites, AMFI, SEBI). It must **not** provide investment advice, opinions, or recommendations.

Core principle: **accuracy and compliance over “intelligence.”** Users get verified, source-backed information—never advisory or speculative content.

---

## Objective

Implement a lightweight **Retrieval-Augmented Generation (RAG)** assistant that:

- Answers factual queries about mutual fund schemes (including **fund management** disclosures published by the AMC)
- Uses a curated corpus of official documents
- Returns concise, source-backed responses

---

## Target Users

- Retail investors comparing mutual fund schemes
- Customer support and content teams handling repetitive mutual fund queries

---

## Scope of Work

### 1. Corpus Definition

**Selected AMC:** [ICICI Prudential Mutual Fund](https://groww.in/mutual-funds/filter?fund_house=%5B%22ICICI+Prudential+Mutual+Fund%22%5D) (Groww fund-house filter used as product reference only).

**Scheme scope:** The assistant is limited to **10 ICICI Prudential direct-growth schemes** (table below), within the broader [ICICI Prudential fund house on Groww](https://groww.in/mutual-funds/filter?fund_house=%5B%22ICICI+Prudential+Mutual+Fund%22%5D). Queries about other schemes, other AMCs, or comparisons outside this set are **out of scope** and should be refused or redirected per refusal rules.

For each in-scope scheme, build corpus material from **official public sources** (ICICI Prudential AMC site, AMFI, SEBI), such as:

- Scheme factsheets (including **fund manager** name, tenure, and related disclosures where published)
- KIM (Key Information Memorandum)
- SID (Scheme Information Document)
- AMC scheme pages and **fund-management** sections on the AMC site (official manager listings per scheme)
- AMC FAQ / help pages
- AMFI / SEBI guidance pages (shared across schemes)
- Statement and tax document download guides

**Source policy:** Citations and retrieval must use official public sources only (AMC, AMFI, SEBI). **No** third-party blogs or aggregator sites. Groww URLs below are **reference product context** for naming, categories, and UX alignment—not citation sources.

#### In-scope schemes (10 funds)

**Canonical AMC URLs** (ingest and citations): [`MF_URL.md`](MF_URL.md) — **only** these `www.icicipruamc.com` product pages; no PDF factsheets, Groww, or other URLs in the live corpus.

| # | Scheme (Direct Growth) | `scheme_id` |
|---|------------------------|-------------|
| 1 | ICICI Prudential Large Cap Fund | `icici-large-cap` |
| 2 | ICICI Prudential Manufacturing Fund | `icici-manufacturing` |
| 3 | ICICI Prudential Pharma Healthcare and Diagnostics (P.H.D) Fund | `icici-phd` |
| 4 | ICICI Prudential US Bluechip Equity Fund | `icici-us-bluechip` |
| 5 | ICICI Prudential Multi Asset Fund | `icici-multi-asset` |
| 6 | ICICI Prudential Nifty Auto Index Fund | `icici-nifty-auto` |
| 7 | ICICI Prudential Nifty 50 Index Fund | `icici-nifty-50` |
| 8 | ICICI Prudential Nifty 500 Index Fund | `icici-nifty-500` |
| 9 | ICICI Prudential Nifty Bank Index Fund | `icici-nifty-bank` |
| 10 | ICICI Prudential Nifty Smallcap 250 Index Fund | `icici-nifty-smallcap-250` |

**Scheme aliases and resolution:** Users may type informal names (e.g. “bank index”, “large cap”). The registry maps these to `scheme_id`; **question text overrides** the UI scheme picker when both apply. Canonical list and rules: [`scheme-aliases.md`](scheme-aliases.md). Data: `corpus/schemes.yaml`.

Groww links remain **product reference only** (naming/UX), not citation or ingest sources.

### 2. FAQ Assistant Behavior

**In-scope query examples:**

| Topic | Example |
|-------|---------|
| Fees | Expense ratio of a scheme |
| Charges | Exit load details |
| Investment minimums | Minimum SIP amount |
| Tax / lock-in | ELSS lock-in period |
| Risk | Riskometer classification |
| Benchmark | Benchmark index |
| Operations | How to download statements or capital gains reports |
| Fund management | Who manages the Large Cap Fund? Since when? Co-manager / fund-management team (per official disclosure) |

**Fund management responses** must stick to **verifiable disclosures** from official documents (e.g. current fund manager name, appointment or management start date, co-managers, and other fields explicitly stated on the factsheet, KIM, SID, or AMC scheme page). Do **not** offer opinions on manager skill, track record interpretation, or suitability.

**Every factual response must:**

- Use the **default prose cap of at most 3 sentences** for normal Q&A (`type=answer`) — short, facts-only answers
- **Relax the 3-sentence rule** when the user clearly wants more coverage:
  - **Tabular / table / list-all / compare all funds:** return `type=structured` with a table (up to 12 in-scope rows) and an optional **2-sentence** summary instead of the 3-sentence prose cap
  - **Detailed / complete / full list** (e.g. “list all fund managers”, “give full holdings”, “detailed breakdown”): allow a longer prose answer (higher sentence cap in validator + prompt); do not truncate lists of names, holdings, or rows that appear in context
  - **Fund management** (who manages, fund managers): allow listing **every** disclosed manager name from context (see implementation notes below)
- Include **exactly one** official citation per answer, exposed as the UI **“Official source”** link (`citation_url` in the API) — **not** as a raw URL in the chat message body
- End with footer: `Last updated from sources: <date>` in the API `answer` field (the UI may show the date separately in the message footer)

**Performance-related queries:** Do not compute or compare returns. Provide a link to the **official factsheet** only.

### 3. Refusal Handling

Refuse non-factual or advisory queries, e.g.:

- “Should I invest in this fund?”
- “Which fund is better?”
- “Is this fund manager good?” / “Which manager is better?” (subjective or comparative)

Also refuse or clarify when the user asks about a **scheme not in the in-scope list** or about **other AMCs**, or about **fund managers not disclosed** for an in-scope scheme in the corpus.

Refusal responses must:

- Be polite and clear
- Reinforce the facts-only limitation
- Include a relevant **educational link** (e.g., AMFI or SEBI resource)

### 4. User Interface (Minimal)

- Welcome message
- **Three** example questions (mix of fee/ops and **fund management**, e.g. “Who manages the Technology fund?”)
- Visible disclaimer: **“Facts-only. No investment advice.”**

---

## Constraints

### Data and sources

- Official public sources only (AMC, AMFI, SEBI)
- No third-party blogs or aggregators

### Privacy and security

**Do not** collect, store, or process:

- PAN or Aadhaar numbers
- Account numbers
- OTPs
- Email addresses or phone numbers

### Content

- No investment advice or recommendations
- No performance comparisons or return calculations
- No subjective commentary on fund managers (skill, ranking, or “best” manager)
- Performance questions → official factsheet link only

### Transparency

- Short, factual, verifiable answers
- Every answer: source link + last updated date

---

## Expected Deliverables

| Deliverable | Contents |
|-------------|----------|
| **README** | Setup instructions; selected AMC and schemes; RAG architecture overview; known limitations |
| **Disclaimer** | “Facts-only. No investment advice.” (UI and docs) |

---

## Success Criteria

- Accurate retrieval of factual mutual fund information (including fund management disclosures)
- Strict facts-only responses (no advisory drift)
- Consistent, valid source citations (one per answer)
- Proper refusal of advisory / comparative queries
- Clean, minimal, user-friendly interface

---

## Implementation Notes (for agents and developers)

- **Phase plan:** [`implementation.md`](implementation.md)
- **Edge cases / QA:** [`edgecases.md`](edgecases.md)
- **Stack direction:** Lightweight RAG (ingest official URLs per scheme → chunk/embed → retrieve → generate with strict prompts).
- **Embeddings:** Local **[BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5)** (384 dimensions) via `sentence-transformers`; stored in Chroma at `data/chroma/`. Same model embeds corpus chunks at ingest and user queries at retrieval. No paid embedding API; first run downloads the model from Hugging Face.
- **Generation (Phase 2+):** **[Groq](https://console.groq.com/)** chat API — free tier; default model `llama-3.3-70b-versatile`; API key in `.env` as `GROQ_API_KEY`. OpenAI-compatible endpoint at `https://api.groq.com/openai/v1`.
- **Scope guard:** Restrict retrieval and answers to the **10 in-scope schemes** above; treat unknown scheme names as out of scope.
- **Corpus source of truth:** [`MF_URL.md`](MF_URL.md) → `corpus/urls.yaml` (`doc_type: amc_product_page`). **Daily refresh:** GitHub Actions at 10:00 IST ([`ingest-schedule.md`](ingest-schedule.md)). Manual re-ingest: `python -m src.ingest --force`.
- **AMC product pages (SPA):** ICICI AMC pages are React SPAs; static HTTP fetch is insufficient. Ingest uses **Playwright** (`src/ingest/amc_spa.py`) to:
  - Load each product URL from `MF_URL.md`
  - Expand tabs **Holdings**, **Fund Manager**, **Sectors** (and capture `apimf.icicipruamc.com` JSON: portfolio, metrics, fund details)
  - Resolve **Direct Growth** `schemeCode` from the fund-details API (URL fund id ≠ API scheme code)
  - Avoid clicking the **Scheme Plan** dropdown (Direct/Regular) before tabs — it opens a MUI menu that blocks tab clicks
  - Prefer network capture + `page.request` for portfolio APIs; dismiss overlays (Escape) before tab clicks
- **Parser sections:** `src/ingest/parsers/amc_fund_parser.py` emits **Top holdings**, **Sector allocation**, **Fund Manager**, **Fund metrics**, etc., for retrieval.
- **Citations:** Prefer canonical AMC product URLs (`factsheet_canonical` in manifest). Reject `chrome-extension://` and legacy `digitalfactsheet` PDF links (`src/retrieval/citations.py`).
- **Fund management:** Tag chunks with `topic=fund_management`; boost on “fund manager” queries. List **all** manager names present in context.
- **Scheme resolution:** Text in the user question **overrides** the sidebar scheme picker when both are set (`src/retrieval/preprocessor.py`). All 10 funds have documented informal aliases ([`scheme-aliases.md`](scheme-aliases.md)). Prevents e.g. Large Cap selected + “holdings in bank index” → wrong fund and wrong **Official source** URL.
- **Fund managers (chat):** When a **Fund Manager** chunk is retrieved, the API may answer deterministically from corpus (`src/retrieval/fund_manager_answer.py`) so all listed names appear without LLM truncation. For fund-manager questions, the LLM sees **only** Fund Manager context blocks (not TER/SIP/metrics) to avoid unrelated facts in the reply.
- **Citation in UI:** `answer` is plain prose (no `https://` URLs). `citation_url` is rendered only as the **Official source** button/link (`frontend/src/lib/format.ts` strips any stray URLs from the body). Validator (`src/guardrails/validator.py`) removes URLs from text and sets `citation_url` separately.
- **Answer length / validator** (`src/guardrails/validator.py`):
  - Default **`type=answer`:** ≤3 sentences (`answer_max_sentences`)
  - **Fund-management intent:** ≤6 sentences (`answer_max_sentences_fund_management`); prompt asks for every manager name
  - **Honorifics:** Sentence splitting must **not** treat `Mr.` / `Ms.` / `Mrs.` / `Dr.` as sentence ends (otherwise lists truncate mid-name)
  - **Tabular requests:** `type=structured` — table + short summary; not subject to 3-sentence prose cap
  - **Detailed requests:** When the user asks for **detailed**, **complete**, **full**, or **all** items in prose, relax the 3-sentence cap (same policy as fund-management lists); prefer structured table when the user asks for a **table**
- **Prompting / guardrails:** Single citation, footer date, refusal templates; sentence cap varies by intent (see above).
- **Corpus maintenance:** Track `Last updated from sources` from `fetched_at` per source; purge orphaned Chroma sources on full ingest when URLs are removed from manifest.
- **Reference UX:** Groww-style factual help; compliance-first, not conversational financial advice.

---

## Canonical Disclaimer

> Facts-only. No investment advice.

---

## Source Document

Full problem statement: [`problemstatement.txt`](problemstatement.txt)
