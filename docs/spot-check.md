# Phase 5 spot-check — all 10 schemes

Manual release gate before demo/production. Run API locally with a populated Chroma index and Groq key configured.

**Prerequisites:** `python -m src.ingest --manifest corpus/urls.yaml` completed successfully.

## Per-scheme checklist

For each `scheme_id`, ask via UI or `POST /chat` with `scheme_id` set:

| scheme_id | Expense ratio | Exit load | Min SIP | Fund manager / index mandate |
|-----------|---------------|-----------|---------|------------------------------|
| icici-large-cap | | | | |
| icici-manufacturing | | | | |
| icici-phd | | | | |
| icici-us-bluechip | | | | |
| icici-multi-asset | | | | |
| icici-nifty-auto | | | | index wording |
| icici-nifty-50 | | | | index wording |
| icici-nifty-500 | | | | index wording |
| icici-nifty-bank | | | | index wording |
| icici-nifty-smallcap-250 | | | | index wording |

**Pass each row when:**

- Answer is ≤3 sentences (fund manager answers may use extended cap per validator).
- Exactly one official citation link (AMC product page).
- Footer `Last updated from sources: YYYY-MM-DD` is present.
- Numbers match the AMC page (spot-check in browser).
- Index funds: passive/index mandate wording — no active manager opinion.

## Sample questions

Copy into chat with the matching `scheme_id`:

```
What is the expense ratio?
What is the exit load?
What is the minimum SIP amount?
Who manages this fund?
```

## Release target

Per [implementation.md](implementation.md) §8.5: **≥ 7/10** schemes answer fund manager or index mandate correctly; all four factual topics should be spot-checked for every scheme before release.
