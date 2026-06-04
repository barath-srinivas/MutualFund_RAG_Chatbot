export type StructuredTablePayload = {
  format: "table";
  title: string | null;
  columns: string[];
  rows: string[][];
  summary: string | null;
};

export type ChatResponse = {
  answer: string;
  citation_url: string | null;
  last_updated: string;
  type: "answer" | "refusal" | "structured";
  refusal_reason: string | null;
  structured: StructuredTablePayload | null;
};

export type ChatErrorKind = "network" | "server" | "config";

export class ChatApiError extends Error {
  kind: ChatErrorKind;

  constructor(message: string, kind: ChatErrorKind) {
    super(message);
    this.name = "ChatApiError";
    this.kind = kind;
  }
}

function apiBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!base) {
    throw new ChatApiError(
      "API URL is not configured. Set NEXT_PUBLIC_API_BASE_URL in .env.local.",
      "config",
    );
  }
  return base.replace(/\/$/, "");
}

export async function postChat(
  message: string,
  schemeId: string | null,
): Promise<ChatResponse> {
  const base = apiBaseUrl();
  let response: Response;

  try {
    response = await fetch(`${base}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        scheme_id: schemeId || undefined,
      }),
    });
  } catch (err) {
    const hint =
      err instanceof TypeError
        ? " Check that the backend is running, use http://localhost:3000 (not the network IP), and that CORS_ORIGINS includes your UI origin."
        : "";
    throw new ChatApiError(
      `Could not reach the assistant API.${hint}`,
      "network",
    );
  }

  if (!response.ok) {
    const detail =
      response.status >= 500
        ? "The server encountered an error (often missing Phase 1 deps or corpus). Run: pip install -r requirements-phase1.txt && python -m src.ingest"
        : `Request failed (${response.status}).`;
    throw new ChatApiError(detail, "server");
  }

  return (await response.json()) as ChatResponse;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const base = apiBaseUrl();
    const response = await fetch(`${base}/health`, { method: "GET" });
    if (!response.ok) return false;
    const data = (await response.json()) as { status?: string };
    return data.status === "ok";
  } catch {
    return false;
  }
}
