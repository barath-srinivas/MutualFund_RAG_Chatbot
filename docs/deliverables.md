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
