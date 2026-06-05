# Deployment issues captured (Railway + GitHub Actions)

Session log for first-time production deploy of **MutualFund_RAG_Chatbot** to [Railway](https://railway.app/) (API) and [GitHub Actions](https://github.com/barath-srinivas/MutualFund_RAG_Chatbot) (daily ingest). Written for future debugging and onboarding.

**Related docs:** [Deployment-plan.md](Deployment-plan.md) · [ingest-schedule.md](ingest-schedule.md) · [deployment.md](deployment.md)

**Outcome (2026-06-05):** Corpus ingest succeeded on Railway Hobby with increased memory — `chunk_count: 70`, `sources_processed: 10`, `sources_failed: 0`. **Vercel frontend** and **CORS update** remain pending.

---

## Summary table

| # | Issue | Symptom | Fix / commit |
|---|--------|---------|----------------|
| 1 | Empty GitHub repo | Push to new remote | Init git in project root; push to `main` |
| 2 | Git push email privacy | `GH007` push rejected | Commit author `user@users.noreply.github.com` |
| 3 | Missing GitHub secrets | Workflow exit 1 immediately | Repository secrets `RAILWAY_API_BASE_URL`, `INGEST_TRIGGER_SECRET` |
| 4 | `${PORT}` not expanded | Healthcheck fail; uvicorn `--port '${PORT}'` | Shell wrapper in `railway.toml`, `Dockerfile`, `Procfile` — `dd8a12d` |
| 5 | Playwright browser missing | Ingest fails on AMC pages (Docker build) | `playwright install chromium` in `Dockerfile` — `d91f033` |
| 6 | HTTP 301 on ingest trigger | GitHub: `Ingest trigger failed (HTTP 301)` | `RAILWAY_API_BASE_URL` must be `https://…` (no `http://`) — `757579a` |
| 7 | Long POST killed by proxy | Workflow ~12s–2min then fail; empty corpus | Background ingest + poll `/corpus-status` — `05f381e` |
| 8 | False workflow success | Green job in ~1 min; `last_ingest` still null | Poll with `jq` (compact JSON has no space after `:`) — `4509d70` |
| 9 | Out of memory (trial) | OOM badge; container restart ~1 min into ingest; count stuck at 7 | Upgrade Hobby + increase service memory (2GB+); optional `EMBEDDING_BATCH_SIZE=8` |
| 10 | Chroma posthog telemetry | `capture() takes 1 positional argument but 3 were given` | Harmless — ignore during ops |
| 11 | Private vs public URL | Confusion over `*.railway.internal` | GitHub/Vercel use **public** `https://….up.railway.app` only |
| 12 | Vercel build — missing `@/data/*` | `Module not found: '@/data/schemes'` | `.gitignore` `data/` → `/data/`; commit `frontend/src/data/*.ts` |
| 13 | Scheduled ingest never fired | No run at 10:00 IST; all runs `workflow_dispatch` | GitHub cron not queued — wait for next slot or push to `main` to resync |

---

## 1. GitHub repository and first push

**Symptom:** Project lived under parent `Cursor Files` git (wrong remote `testingproject.git`); new repo [MutualFund_RAG_Chatbot](https://github.com/barath-srinivas/MutualFund_RAG_Chatbot) was empty.

**Fix:** `git init` inside `MF_RAG_ChatBot/`, initial commit (167 files, `.env` gitignored), `origin` → MutualFund_RAG_Chatbot.

**Follow-up:** Push blocked with `GH007` (private email in commit). Use GitHub noreply email for commits: `barath-srinivas@users.noreply.github.com`.

---

## 2. GitHub Actions — missing repository secrets

**Symptom:** Workflow **Daily corpus refresh (10:00 IST)** failed in ~12s with:

```text
Set repository secrets RAILWAY_API_BASE_URL and INGEST_TRIGGER_SECRET
```

**Cause:** Workflow reads `${{ secrets.* }}`; empty secrets fail the guard in `.github/workflows/daily-ingest.yml`.

**Fix:**

| Secret | Value |
|--------|--------|
| `RAILWAY_API_BASE_URL` | Public API URL, e.g. `https://mutualfundragchatbot-production.up.railway.app` — **no** trailing slash, **no** `/internal/ingest` |
| `INGEST_TRIGGER_SECRET` | Same random string as Railway variable `INGEST_TRIGGER_SECRET` |

Use **Repository secrets** (not Environment secrets). Railway must have `ENABLE_INTERNAL_INGEST=true` and the same secret.

**Generate secret (example):** `openssl rand -hex 32`

---

## 3. Railway healthcheck — `${PORT}` literal

**Symptom:** Deploy failed at healthcheck. Deploy logs:

```text
Error: Invalid value for '--port': '${PORT}' is not a valid integer.
```

**Cause:** `startCommand` ran without a shell; Railway’s `PORT` env was not expanded.

**Fix (commit `dd8a12d`):**

- `railway.toml`: `sh -c 'exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT}'`
- `Dockerfile` / `Procfile`: same pattern

**Verify:** Deploy logs show `Uvicorn running on http://0.0.0.0:8080` (or similar numeric port), service **Online**.

---

## 4. Railway build path — Dockerfile without Playwright browsers

**Symptom:** API healthy but ingest never populated Chroma; AMC `amc_product_page` sources need Playwright.

**Cause:** Railway built from **Dockerfile** (not full `railway.toml` buildCommand). Dockerfile installed Python `playwright` package but not Chromium binaries.

**Fix (commit `d91f033`):** After `pip install`, add:

```dockerfile
playwright install chromium && playwright install-deps chromium
```

**Note:** `railway.toml` buildCommand already includes Playwright; Dockerfile path must match for Docker-based deploys.

---

## 5. GitHub ingest trigger — HTTP 301 redirect

**Symptom:** Workflow annotation: `Ingest trigger failed (HTTP 301)`.

**Cause:** `RAILWAY_API_BASE_URL` used `http://` or wrong host; Railway redirects to HTTPS.

**Fix:**

- Set secret to `https://mutualfundragchatbot-production.up.railway.app`
- Workflow validates `https://` prefix (commit `757579a`)

---

## 6. Synchronous ingest vs HTTP / proxy timeouts

**Symptom:** Workflow ran 2–12 minutes then failed; `/corpus-status` stayed `chunk_count: 0`, `last_ingest: null`. Railway HTTP logs showed only `GET /corpus-status`, no long-running ingest completion.

**Cause:** `POST /internal/ingest` ran **full ingest inside the HTTP request** (30–60+ min). Railway/proxy closed the connection; GitHub `curl` exited with error.

**Fix (commit `05f381e`):**

- API returns **202 Accepted** immediately; ingest runs in a **background thread** (`src/api/internal_ingest.py`).
- Workflow polls `GET /corpus-status` until `last_ingest != null` (up to ~120 min).

---

## 7. False positive workflow success (~1 minute)

**Symptom:** GitHub job **Success** in ~1m 9s while `last_ingest` was still `null`.

**Cause:** Poll step grepped for `"last_ingest": null` (space before `null`). API returns compact JSON: `"last_ingest":null`. Grep never matched “still null” → workflow assumed done.

**Fix (commit `4509d70`):** Use `jq -e '.last_ingest != null'` instead of grep.

---

## 8. Out of memory — trial plan (critical)

**Symptom:**

- Railway UI: **Out of memory** badge (count 1).
- Deploy log timeline:
  - `02:25:44` — `Starting scheduled corpus ingest`, `POST /internal/ingest` **202**
  - `02:26:04` — `Loading embedding model BAAI/bge-small-en-v1.5 on cpu`
  - `02:26:43` — **`Starting Container`** again (process killed / restarted)
- After restart: only `GET /corpus-status` every ~60s (GitHub poll); no further ingest logs.
- `chunk_count` stuck at **7**; `last_ingest: null`.

**Cause:** Peak RAM = Playwright/Chromium + sentence-transformers (BGE) + Chroma + API. **Trial** RAM too small; OOM killer restarted container; **background ingest thread died** and was not resumed.

**Fix:**

1. Upgrade to **Railway Hobby** (or higher).
2. Service **Settings → Resources**: memory **≥ 2 GB** (4 GB if OOM persists).
3. Optional variable: `EMBEDDING_BATCH_SIZE=8`.
4. Re-trigger ingest (`POST /internal/ingest` or GitHub workflow).
5. **Fallback on low RAM:** Railway Shell, one fund per run:
   ```bash
   python -m src.ingest --manifest corpus/urls.yaml --no-save-raw --source-id <manifest-source-id>
   ```
   Ten IDs in `corpus/urls.yaml` (e.g. `icici-nifty-50-amc-product-page`).

**Successful run (Hobby + more memory):**

```json
{
  "chunk_count": 70,
  "last_ingest": {
    "run_id": "ingest_20260605T030632Z",
    "finished_at": "2026-06-05T03:12:13.984184+00:00",
    "sources_processed": 10,
    "sources_failed": 0,
    "total_chunks": 70
  }
}
```

`chunk_count` increased in **multiples of ~7** during the run (one AMC page ≈ 7 chunks).

---

## 9. Noisy but harmless log lines

### Chroma PostHog telemetry

```text
ERROR chromadb.telemetry.product.posthog Failed to send telemetry event ClientStartEvent:
capture() takes 1 positional argument but 3 were given
```

**Cause:** Chroma ↔ PostHog version mismatch for optional telemetry.

**Action:** Ignore. Does not block ingest. Often appears on every `GET /corpus-status` because each request opens a Chroma client.

### Repeated `GET /corpus-status`

During GitHub workflow poll, HTTP/deploy logs show only corpus-status + posthog errors. **Not** ingest progress — check deploy logs for `Starting scheduled corpus ingest` / `Corpus ingest finished`.

---

## 10. Configuration clarifications

### Private vs public Railway URL

| URL | Use |
|-----|-----|
| `https://mutualfundragchatbot-production.up.railway.app` | GitHub `RAILWAY_API_BASE_URL`, Vercel `NEXT_PUBLIC_API_BASE_URL`, browser, curl |
| `mutualfundragchatbot.railway.internal` | Only other Railway services in same project (optional cron); **not** for GitHub Actions |

### Railway variables (API service)

| Variable | Production value |
|----------|------------------|
| `GROQ_API_KEY` | Required for `/chat` |
| `VECTOR_DB_PATH` | `data/chroma` |
| `ENABLE_INTERNAL_INGEST` | `true` |
| `INGEST_TRIGGER_SECRET` | Long random; same as GitHub secret |
| `CORS_ORIGINS` | Vercel URL(s) + localhost — still has placeholder `https://your-app.vercel.app` until Vercel deploy |

### Volume

Mount at `/app/data` so `data/chroma` and `last_ingest.json` persist across deploys.

---

## 11. Deploy log vs HTTP log (where to look)

| Log | When to use |
|-----|-------------|
| **Build logs** | Image build, pip, Playwright install failures |
| **Deploy logs** | Uvicorn startup, `Starting scheduled corpus ingest`, OOM/restart, `Corpus ingest finished` |
| **HTTP logs** | `POST /internal/ingest` 202, `GET /corpus-status`, 401/403/404 on trigger |

---

## 12. Still pending (post-corpus)

| Item | Status |
|------|--------|
| **Vercel** — import repo, root `frontend/`, `NEXT_PUBLIC_API_BASE_URL` | Pending |
| **CORS_ORIGINS** — replace placeholder with real Vercel URL(s) | Pending |
| **Scheduled ingest** — cron `30 4 * * *` UTC (10:00 IST) | Configured; **first auto run missed 2026-06-05** — see §14; verify **Scheduled** trigger on 2026-06-06 |

---

## 13. Vercel build — `@/data/*` module not found

**Symptom:** `npm run build` failed on Vercel in ~18s:

```text
Module not found: Can't resolve '@/data/examples'
Module not found: Can't resolve '@/data/schemes'
```

**Cause:** Root `.gitignore` had `data/`, which ignored **any** `data/` folder in the repo — including `frontend/src/data/schemes.ts` and `examples.ts`. Files existed locally but were never pushed to GitHub.

**Fix:** Change `.gitignore` to `/data/` (repo-root Chroma volume only) and commit `frontend/src/data/*.ts`.

**Verify:** Vercel redeploy succeeds; scheme picker and example questions render.

---

## 14. GitHub Actions — scheduled cron did not fire (2026-06-05)

**Symptom:** No workflow run at **10:00 IST** (04:30 UTC) on 2026-06-05. Corpus was refreshed only via **manual** runs (`workflow_dispatch`).

**Evidence (via `gh run list --workflow=daily-ingest.yml`):**

- **9** runs total — **all** `event: workflow_dispatch`; **zero** `event: schedule`.
- Query for `2026-06-05T04:00–05:00Z` returned **no runs** (scheduled slot is `30 4 * * *` UTC).
- Manual runs on 2026-06-05: **03:06 UTC** (08:36 IST, success), **10:00 UTC** (15:30 IST, success). The 10:00 **UTC** run is **not** the cron slot (cron is 04:30 UTC = 10:00 IST).

**Ruled out (workflow config is correct):**

| Check | Status |
|-------|--------|
| Cron `30 4 * * *` in `.github/workflows/daily-ingest.yml` | OK |
| Workflow on `main` since initial commit (`44ddfef`) | OK |
| `gh workflow list` → **active** | OK |
| Repo public; Actions enabled | OK |
| Secrets / Railway ingest | OK — manual runs succeed, `last_ingest` updates |

If secrets or Railway were wrong, GitHub would still **create** a scheduled run (it would fail). **No run was created** — GitHub’s scheduler never queued the job.

**Likely causes:**

1. **New repo / first cron slot** — Repo and workflow are ~1 day old; GitHub sometimes skips the first eligible `schedule` event even when `workflow_dispatch` works.
2. **Dropped scheduled job** — [GitHub docs](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule): under load, queued cron jobs can be **delayed or dropped** with no run record.
3. **Scheduler sync** — Occasional backend glitches; a harmless commit to `main` can re-register the cron.

**Action:**

1. **2026-06-06 ~10:00 IST (04:30 UTC):** Actions → **Daily corpus refresh (10:00 IST)** → confirm trigger shows **Scheduled** (not “Manually run by…”).
2. If still no scheduled run: push a trivial commit to `main` or re-save the workflow file to resync.
3. Until cron is verified, manual **Run workflow** is a safe fallback (corpus already updated on 2026-06-05 via manual run #9).

**Verify scheduled vs manual:**

```bash
gh run list --workflow=daily-ingest.yml --limit 5 --json event,createdAt,conclusion
# expect event: "schedule" after a successful cron fire
```

---

## Commits referenced

| Commit | Summary |
|--------|---------|
| `44ddfef` | Initial GitHub push |
| `dd8a12d` | Fix `${PORT}` expansion |
| `d91f033` | Playwright Chromium in Dockerfile |
| `00f8e4c` | Log HTTP status in workflow |
| `757579a` | Require `https://` for API base URL |
| `05f381e` | Background ingest + status polling |
| `4509d70` | `jq` poll fix for compact JSON |

---

## Quick troubleshooting (future)

| Symptom | Check |
|---------|--------|
| Workflow fails immediately | GitHub secrets; `https://` URL |
| Workflow HTTP 301 | `RAILWAY_API_BASE_URL` must be `https://` |
| Workflow HTTP 401/403 | `INGEST_TRIGGER_SECRET` match Railway ↔ GitHub |
| Workflow HTTP 404 | `ENABLE_INTERNAL_INGEST=true` |
| `chunk_count` 0, `last_ingest` null | Ingest never completed; trigger `POST /internal/ingest` |
| Count stuck, only `/corpus-status` in logs | OOM restart; increase memory or one-fund shell ingest |
| Count rises by ~7, `last_ingest` null | In progress — wait for full run |
| Chroma posthog errors | Ignore |
| No run at 10:00 IST; only manual runs | GitHub cron not queued — see §14; check `event: schedule` via `gh run list` |
