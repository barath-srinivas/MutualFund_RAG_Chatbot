# Known issues

## 1. Official source link pointed to outdated PDF — **fixed**

**Was:** UI “Official source” sometimes opened a `chrome-extension://…` wrapper around `digitalfactsheet.icicipruamc.com/.../fund-factsheet-for-january-2026.pdf`.

**Fix:** Corpus is limited to AMC product pages in `docs/MF_URL.md`. Citations prefer `factsheet_canonical` (www.icicipruamc.com). PDF and chrome-extension URLs are rejected in the validator.

**Verify:** Ask about Large Cap expense ratio; “Official source” should open `https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-large-cap-fund/211`.

## 2. Frontend unstyled (broken layout) — **fixed**

**Was:** Page rendered with default browser fonts; `mf-*` layout/CSS not applied (often after Tailwind v4 `@import` failed in dev).

**Fix:** Removed Tailwind from `globals.css` and PostCSS; UI uses self-contained `mf-*` styles only. Restart `npm run dev` after pulling.

## 3. Fund managers missing or wrong citation — **fixed**

**Was:** Questions like “Who are the fund managers of Nifty 500?” returned the generic fallback (“I do not have verified information…”) and sometimes linked to the **wrong** scheme (e.g. Nifty Bank URL).

**Causes:**

1. **Sidebar `scheme_id` overrode the question** — e.g. Nifty Bank selected while the user asked about Nifty 500; retrieval used the wrong fund; `answer_mentions_foreign_fund` rejected the LLM answer and fell back.
2. **Validator sentence cap** split on `Mr.` / `Ms.` and truncated manager lists (see implementation §2.1).
3. **`amc_product_page` not boosted** for fund-management retrieval (doc_type was `amc_scheme`-only in reranker).

**Fix:**

- `resolve_scheme_id()` — **message text wins** over UI `scheme_id` when both are present.
- Word-boundary alias matching (`nifty 50` no longer matches `nifty 500`).
- Deterministic fund-manager answers from the **Fund Manager** chunk when present (`src/retrieval/fund_manager_answer.py`).
- Rerank/context prioritization for `Fund Manager` sections; `amc_product_page` in fund-management doc boosts.

**Verify:** With any sidebar fund selected, ask “Who are the fund managers of nifty 500?” — answer should list all managers and cite `…/nifty-500-index-fund/1884`.

## 4. URL shown inside chat text / extra TER-SIP in fund-manager answers — **fixed**

**Was:** Answers included a raw `https://www.icicipruamc.com/...` in the message body. Fund-manager replies sometimes added expense ratio, SIP, or exit load.

**Fix:** Validator no longer appends URLs to `answer` (only `citation_url`). Prompts and fallbacks use “official source link below.” Fund-manager path uses Fund Manager chunks only and managers-only prompt rules. Frontend `answerBody()` strips any remaining URLs.

**Verify:** Ask “Who are the fund managers of the manufacturing fund?” — prose lists names only; **Official source** link appears in the footer, not as inline URL text.

## 5. Wrong fund / citation when sidebar scheme ≠ question — **fixed**

**Was:** User asked about one fund (e.g. “holdings in bank index”) while the scheme picker still had another fund (e.g. Large Cap). Short phrases like “bank index” were not in the alias list, so `resolve_scheme_id` fell back to the picker → wrong answer body and **Official source** URL.

**Fix:**

- **Message-first resolution** documented in [`scheme-aliases.md`](scheme-aliases.md).
- Informal aliases added for **all 10** schemes in `corpus/schemes.yaml` (e.g. `bank index`, `large cap`, `auto index`, `smallcap 250`).
- Tests: `test_informal_aliases_resolve`, `test_bank_index_in_message_overrides_stale_sidebar`.

**Verify:** With Large Cap selected in the sidebar, ask “which are the top holdings in bank index?” — citation should be `…/icici-prudential-nifty-bank-index-fund/1839`, not the Large Cap product page.
