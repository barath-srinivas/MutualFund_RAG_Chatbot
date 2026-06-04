# Scheme registry and aliases

Formal reference for how user text maps to in-scope funds, how that interacts with the UI scheme picker, and how citations stay aligned with the resolved fund.

**Source of truth (data):** [`corpus/schemes.yaml`](../corpus/schemes.yaml)  
**Source of truth (code):** [`src/schemes/registry.py`](../src/schemes/registry.py), [`src/retrieval/preprocessor.py`](../src/retrieval/preprocessor.py)  
**Tests:** [`tests/test_scheme_registry.py`](../tests/test_scheme_registry.py)

---

## 1. Purpose

Users refer to funds informally (“bank index”, “large cap”, “PHD”). The registry maps those phrases to a stable `scheme_id` so that:

1. Retrieval filters the correct Chroma corpus partition.
2. The **Official source** link uses the canonical AMC product URL for that fund ([`corpus/urls.yaml`](../corpus/urls.yaml) / [`docs/MF_URL.md`](MF_URL.md)).
3. A stale **scheme picker** selection does not override an explicit fund name in the question.

---

## 2. Registry fields

Each of the 10 in-scope schemes defines:

| Field | Role |
|-------|------|
| `scheme_id` | Stable internal key (e.g. `icici-nifty-bank`) |
| `display_name` | Official Direct Growth name (used in prompts and UI) |
| `category` | Equity / Hybrid sub-category (UI only) |
| `groww_slug` | Groww product slug for UX alignment — **not** a citation source |
| `aliases` | Extra phrases for text resolution (case-insensitive) |

The registry also indexes `scheme_id`, `display_name`, and `groww_slug` automatically for matching.

---

## 3. Resolution precedence

Implemented in `resolve_scheme_id(message, explicit_scheme_id=…)`:

| Priority | Source | When it applies |
|----------|--------|-----------------|
| 1 | **User message** | Any alias, display name, slug, or `scheme_id` substring matches the normalized query |
| 2 | **UI `scheme_id`** | Optional scheme picker / sidebar sends `scheme_id` in `POST /chat` only if the message did **not** resolve |
| 3 | **None** | Broad or ambiguous query → retrieval may be unscoped or classifier returns `out_of_scope` |

**Rule:** Question text **always wins** over the sidebar when both identify a scheme. Example: picker on Large Cap + message “top holdings in bank index” → `icici-nifty-bank`, not `icici-large-cap`.

---

## 4. Matching rules

- Queries are **Unicode-normalized** and whitespace-collapsed (`normalize_query`).
- Matching is **case-insensitive**.
- Phrases shorter than 12 characters use **word boundaries** so `nifty 50` does not match `nifty 500`.
- Longer phrases use substring match on the normalized query.
- Lookup entries are tried **longest phrase first** to prefer specific names (e.g. Nifty 500 before Nifty 50).

---

## 5. Alias catalogue (all 10 schemes)

Aliases below are the explicit `aliases` list in `corpus/schemes.yaml`. The matcher also uses `display_name`, `scheme_id`, and `groww_slug`.

### `icici-large-cap` — ICICI Prudential Large Cap Fund Direct Growth

| Aliases |
|---------|
| Large Cap Fund, ICICI Large Cap, large cap, largecap fund |

### `icici-manufacturing` — ICICI Prudential Manufacturing Fund Direct Growth

| Aliases |
|---------|
| Manufacturing Fund, ICICI Manufacturing, manufacturing, manufacturing fund |

### `icici-phd` — ICICI Prudential Pharma Healthcare and Diagnostics (P.H.D) Fund Direct Growth

| Aliases |
|---------|
| PHD Fund, PHD, P.H.D Fund, P.H.D, Pharma Healthcare and Diagnostics, Pharma fund, PHD fund |

### `icici-us-bluechip` — ICICI Prudential US Bluechip Equity Fund Direct Growth

| Aliases |
|---------|
| US Bluechip, US Bluechip Equity Fund, Bluechip Equity Fund, us bluechip, us bluechip fund |

### `icici-multi-asset` — ICICI Prudential Multi Asset Fund Direct Growth

| Aliases |
|---------|
| Multi Asset Fund, Multi Asset, Dynamic Plan, ICICI Prudential Dynamic Plan, multi asset fund, dynamic plan fund |

**Note:** Groww slug `icici-prudential-dynamic-plan-direct-growth` maps here (legacy “Dynamic Plan” naming).

### `icici-nifty-auto` — ICICI Prudential Nifty Auto Index Fund Direct Growth

| Aliases |
|---------|
| Nifty Auto Index, Auto Index Fund, auto index, nifty auto, nifty auto index |

### `icici-nifty-50` — ICICI Prudential Nifty 50 Index Direct Plan Growth

| Aliases |
|---------|
| Nifty 50 Index, Nifty 50, Nifty index fund, nifty 50 index, nifty50 |

### `icici-nifty-500` — ICICI Prudential Nifty 500 Index Fund Direct Growth

| Aliases |
|---------|
| Nifty 500 Index, Nifty 500, nifty 500 index, nifty500 |

### `icici-nifty-bank` — ICICI Prudential Nifty Bank Index Fund Direct Growth

| Aliases |
|---------|
| Nifty Bank Index, Bank Index Fund, bank index, Nifty Bank, banking index fund |

### `icici-nifty-smallcap-250` — ICICI Prudential Nifty Smallcap 250 Index Fund Direct Growth

| Aliases |
|---------|
| Nifty Smallcap 250, Smallcap 250 Index, ICICI small cap fund, smallcap 250, small cap 250, nifty smallcap, nifty smallcap 250, smallcap index |

---

## 6. UI scheme picker

- **Frontend:** optional dropdown sends `scheme_id` on every `POST /chat` ([`frontend/src/components/ChatComposer.tsx`](../frontend/src/components/ChatComposer.tsx)).
- **When to use:** questions that do not name a fund (e.g. “What is the expense ratio?” with a fund pre-selected).
- **When it is ignored:** any message that resolves to a `scheme_id` via §3.
- **UX tip:** After switching funds in chat, either name the fund in the message or change the picker to avoid confusion.

---

## 7. Citations

After resolution, `preferred_citation_url()` prefers the manifest **factsheet canonical** URL for that `scheme_id`. Wrong resolution therefore produces wrong retrieval **and** wrong **Official source** links — alias coverage is a P0 correctness requirement.

---

## 8. Maintenance

1. Edit **`corpus/schemes.yaml`** (add aliases; do not duplicate conflicting short phrases across schemes).
2. Add or extend tests in **`tests/test_scheme_registry.py`** (`test_informal_aliases_resolve`, scheme-specific cases).
3. Restart the API (registry is loaded at startup; cached via `get_scheme_registry()`).
4. Update **this document** if the alias policy or catalogue changes.
5. Groww renames/slugs: update `groww_slug` and aliases when product pages drift ([`architecture.md`](architecture.md) §13).

**Do not** cite Groww URLs; aliases are for resolution only.

---

## 9. Related edge cases

See [`edgecases.md`](edgecases.md) §2.2 (ambiguous names, picker vs text, abbreviations). Key IDs: EC-SCOPE-04, EC-SCOPE-10, EC-SCOPE-11, EC-SCOPE-14, EC-SCOPE-16.

---

## 10. Verification checklist

| Check | Expected |
|-------|----------|
| `pytest tests/test_scheme_registry.py` | All pass, including `test_informal_aliases_resolve` |
| Picker = Large Cap, ask “holdings in bank index” | Answer + citation for Nifty Bank Index (`…/nifty-bank-index-fund/1839`) |
| Picker = Nifty Bank, ask “fund managers of nifty 500” | Answer + citation for Nifty 500 (`…/nifty-500-index-fund/1884`) |
| Ask “TER for large cap” with any picker | `icici-large-cap` |
