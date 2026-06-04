# Pro tester report — MF RAG ChatBot

**Role:** Professional mutual fund investor / compliance-minded QA  
**Date:** 2026-06-02  
**Method:** Live API testing at `http://127.0.0.1:8000` (35+ queries). UI not re-tested in browser this session.  
**Note:** No product code was changed for this report.

**Related:** [`context.md`](context.md) · [`edgecases.md`](edgecases.md) · [`scheme-aliases.md`](scheme-aliases.md)

---

## Executive summary

| Area | Verdict |
|------|--------|
| Single-scheme facts (TER, exit load, SIP, NAV) | **Mixed** — often OK, sometimes “not available” or wrong plan |
| Holdings | **Mixed** — index funds OK; large cap can look odd |
| Fund managers | **Good** for named schemes; **weak** for index mandate & vague “sectoral” |
| Refusals (advice / performance / PII / other AMC) | **Good** |
| Comparisons | **Fail** if user omits “compare” |
| All-funds table / catalog | **Fail** (wrong type, or 2–3 rows only) |
| Scheme picker vs text | **Good** when aliases match |
| Ambiguity (Nifty index, sectoral) | **Weak** |
| Operational (CAS / statements) | **Weak** |
| Latency | **Acceptable for demo, slow for production** |

Unit tests: **182 passed** at time of report — they do **not** catch several live LLM / table / catalog behaviours below.

---

## Critical / compliance gaps

### 1. Comparison questions not always refused

- **“Compare expense ratio of Multi Asset and Nifty 500”** → correctly refused (`advisory`).
- **“expense ratio of Multi Asset and Nifty 500”** (no “compare”) → answered **only Multi Asset** TER.

**Risk:** Looks like a comparison by omission; bypasses the advisory guardrail.

**Edge-case ref:** EC-SCOPE-13 (partial — keyword “compare” required today)

---

### 2. “List / cover all funds” mishandled

- **“List all ICICI Prudential mutual funds”** → `out_of_scope` refusal (AMFI link), **does not** list the 10 in-scope schemes.
- **“Which ICICI Prudential direct growth schemes do you cover?”** → same `out_of_scope` refusal.

**Risk:** Investors cannot discover product scope from the bot.

**Edge-case ref:** EC-SCOPE-03, EC-SCOPE-08

---

### 3. Cross-scheme tables are incomplete

| Query | Expected | Actual |
|--------|----------|--------|
| “Show me a **table** of expense ratio for **all 10 funds**” | `type=structured`, ~10 rows | `type=answer`, **one** fund (Multi Asset) |
| “**table** of exit load for all funds” | ~10 rows | `structured`, **3 rows** only |
| “table of expense ratio for all schemes” | ~10 rows | `structured`, **2 rows** |
| “list the expense ratio for **each** fund” | ~10 rows | `structured`, **2 rows** |

**Risk:** “All funds” / catalog views are unreliable for due diligence.

**Edge-case ref:** structured / catalog paths in [`context.md`](context.md) §2

---

## Scheme resolution & citations

### Works (alias + message-over-picker)

- **Bank index holdings** + Large Cap picker → correct **Nifty Bank** answer and citation.
- **Large Cap TER** + Bank picker → correct Large Cap citation.
- **Nifty 500 managers** + Bank picker → correct Nifty 500 citation and manager list.

### Still problematic

| Query | Issue |
|--------|--------|
| “Expense ratio for Nifty index fund?” | Silently resolves to **Nifty 50** (no disambiguation vs 500 / Bank / Auto). |
| “Who is the fund manager of ICICI sectoral fund?” | Long list of **AMC-level names** (e.g. Sankaran Naren) + Manufacturing citation — no “which sectoral fund?” prompt. |
| “NAV” with **no scheme** in message / API body | Answered **PHD NAV** with PHD citation — arbitrary for unscoped queries. |

**Edge-case ref:** EC-SCOPE-10, EC-SCOPE-12, EC-SCOPE-14 (picker fix OK when aliases match)

---

## Answer quality (factual)

### Missing or weak data

- **Large Cap expense ratio** → “**not available**” but still mentions min SIP / lumpsum.
- **PHD benchmark** → “not specified” then vague objective text.
- **Nifty Next 50 TER** → correctly says not in scope vs Nifty 50, but citation still points at **Nifty 50** page.

### Scope / plan confusion (Direct Growth product)

- **US Bluechip TER** → includes **regular plan 1.99%** alongside direct 1.16%. Assistant scope is **Direct Growth**; mixing plans confuses compliance-focused users.
- **“ICICI Large Cap Fund regular plan expense ratio”** → says regular TER not available (OK) but long prose; does not clearly state **assistant covers Direct Growth only**.

**Edge-case ref:** EC-SCOPE-06

### Holdings

- **Large Cap “top holdings”** → includes **GOI 2064/2065, NABARD**, etc. May match AMC page, but reads like debt/sovereign in an equity “top holdings” answer.
- **Bank index holdings** → sensible bank names and weights (**good**).

### Index / passive funds — “Who manages…”

- **Nifty 50 / Nifty Bank** → lists **named managers** (Solanki, Patel, etc.). Docs expect **passive / index mandate** wording, not active-manager-style lists.

**Edge-case ref:** EC-SCOPE-20

### ELSS

- **“ELSS lock-in for Large Cap?”** → **0 years lock-in** on Large Cap. Prefer: none of the 10 are ELSS; **not applicable**.

**Edge-case ref:** EC-SCOPE-07

### Riskometer

- **Large Cap riskometer** → returns **“6”** without standard **Very High / Moderately High** style label from factsheets.

---

## Refusals & guardrails

| Feature | Result |
|--------|--------|
| “Should I invest…?” | Refused `advisory` |
| “Which is better…?” | Refused `advisory` |
| “Is the manager good?” | Refused `advisory` |
| “3 year return…” | Refused `performance` (links Large Cap factsheet — per design) |
| HDFC fund | Refused `out_of_scope` |
| PAN in message | Refused `pii`, no citation |
| “Compare A and B” **without** “compare” | **Not refused** — see §1 |

**Correct behaviour:** **“ICICI Prudential Bluechip fund”** (not in the 10) → `out_of_scope` (distinct from in-scope **US Bluechip**).

---

## Operational / shared topics

- **“How do I download my capital gains statement?”** → generic “do not have verified information”, **no citation**.

**Edge-case ref:** EC-CORPUS-10, operational_shared route

---

## Performance & UX

- Many answers: **~10–15 s** (embeddings + LLM).
- Fund-manager deterministic path: often **&lt;1 s**.
- **UI not browser-tested** this session; verify manually: disclaimer, example chips, scheme picker, structured table UI, API error banners.

---

## What works well

- Facts-only positioning; refusals for clear advisory / performance / PII / other-AMC cases.
- **Message overrides picker** when aliases match (bank index / large cap / nifty 500).
- **Dynamic Plan → Multi Asset**, manufacturing exit load, US Bluechip SIP, auto holdings, NAV with clear scheme context.
- **Meta “context provided…”** not observed on PHD NAV retest (validator/prompt fix effective).
- **Official source** link separate from answer body; no raw URLs in prose in samples checked.

---

## Recommended fix priority (backlog)

| Pri | Item |
|-----|------|
| P0 | Refuse **multi-scheme numeric comparisons** even without the word “compare”. |
| P0 | **Catalog / scope** intents: list 10 schemes by name (not `out_of_scope`). |
| P0 | **Structured tables**: all schemes with data, or explicit “missing” per row. |
| P1 | **Disambiguation** for “Nifty index”, “sectoral fund”. |
| P1 | **Direct Growth only** in answers; avoid regular-plan TER unless explicit. |
| P1 | **Index fund manager** answers: passive mandate wording. |
| P1 | **Unscoped** one-word queries (“NAV”) — require picker or ask which fund. |
| P2 | Operational topics (CAS / statements) — corpus or template + citation. |
| P2 | Riskometer: label + value, not number alone. |
| P2 | Latency / caching for repeat queries. |

---

## Sample queries used (repro)

```
# Scheme resolution
which are the top holdings in bank index?     [picker: icici-large-cap]
What is the expense ratio for large cap?      [picker: icici-nifty-bank]
Who are the fund managers of nifty 500?      [picker: icici-nifty-bank]

# Refusals
Should I invest in Large Cap fund?
Which is better Multi Asset or Large Cap?
What was the 3 year return of Large Cap?
What is HDFC Flexi Cap expense ratio?

# Tables / catalog
Show me a table of expense ratio for all 10 funds
table of exit load for all funds
List all ICICI Prudential mutual funds
Which ICICI Prudential direct growth schemes do you cover?

# Ambiguity
Expense ratio for Nifty index fund?
Who is the fund manager of ICICI sectoral fund?
NAV                                          [no scheme_id]

# Comparisons
Compare expense ratio of Multi Asset and Nifty 500
expense ratio of Multi Asset and Nifty 500

# Other
How do I download my capital gains statement?
What is ELSS lock-in for Large Cap?
My PAN is ABCDE1234F what is my folio balance?
```

---

## Sign-off

| Reviewer | Date | Notes |
|----------|------|-------|
| | | |

*End of report.*
