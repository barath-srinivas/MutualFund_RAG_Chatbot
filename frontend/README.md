# Frontend (Vercel)

Chat UI for the MF RAG assistant. Deploy this app to **Vercel**; it calls the **Railway** FastAPI backend.

## Environment

Copy `.env.example` to `.env.local` (Next.js) or `.env` (Vite):

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | Railway API root, e.g. `https://your-service.up.railway.app` |
| `NEXT_PUBLIC_APP_NAME` | Optional UI title |

**Never** put `GROQ_API_KEY` in the frontend — generation stays on Railway only.

## API contract

```http
GET  {API_BASE_URL}/health
POST {API_BASE_URL}/chat
Content-Type: application/json

{ "message": "What is the expense ratio?", "scheme_id": "icici-large-cap" }
```

`scheme_id` is optional. If the user names a fund in `message` (e.g. “bank index”, “nifty 500”), the backend resolves that fund from aliases and **ignores** a different picker value. See [`../docs/scheme-aliases.md`](../docs/scheme-aliases.md).

Response:

```json
{
  "answer": "...",
  "citation_url": "https://...",
  "last_updated": "2026-05-31",
  "type": "answer",
  "refusal_reason": null
}
```

Refusals use `"type": "refusal"` and a non-null `refusal_reason` (`advisory`, `performance`, `out_of_scope`, `pii`).

**Structured table** (only when the user asks for a table, tabular format, or “all funds” list):

```json
{
  "type": "structured",
  "answer": "plain-text fallback for accessibility",
  "structured": {
    "format": "table",
    "title": "Expense ratio by scheme",
    "columns": ["Scheme", "Direct plan TER"],
    "rows": [["ICICI Prudential Multi Asset Fund", "0.53% p.a."]],
    "summary": "Optional intro (max 2 sentences)."
  },
  "citation_url": "https://...",
  "last_updated": "2026-06-01",
  "refusal_reason": null
}
```

The UI renders `structured` as an HTML table. Normal one-scheme questions still use `type=answer` (3-sentence limit).

## Example fetch (browser)

```javascript
const base = process.env.NEXT_PUBLIC_API_BASE_URL;

const res = await fetch(`${base}/chat`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    message: "What is the expense ratio of Large Cap Fund?",
    scheme_id: "icici-large-cap",
  }),
});
const data = await res.json();
```

## UI requirements (Phase 4)

See [docs/implementation.md](../docs/implementation.md) §7 and [docs/architecture.md](../docs/architecture.md) §7.2:

- Persistent disclaimer: **Facts-only. No investment advice.** (sticky top banner)
- Three example questions: expense ratio (Large Cap), exit load (Multi Asset), fund manager (Technology)
- **Example click behavior:** fills the input, sets `scheme_id`, and **sends the message immediately**
- Scheme selector → optional `scheme_id` on every `POST /chat`
- Distinct amber styling for `type: "refusal"` (advisory, performance, OOS, PII)
- **`type: "structured"`** — HTML table when the user requests tabular / all-funds format
- Mobile-friendly responsive layout

## Local development

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with the API running at `NEXT_PUBLIC_API_BASE_URL`.

## Deploy to Vercel

1. Import this `frontend/` directory as a separate Vercel project (or monorepo root = `frontend`).
2. Set **Production** env: `NEXT_PUBLIC_API_BASE_URL` = your Railway public URL.
3. Set **Preview** env to the same Railway URL or a staging Railway service.
4. Add your Vercel URL(s) to Railway `CORS_ORIGINS` (see root README).
