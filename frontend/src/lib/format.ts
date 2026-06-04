const FOOTER_PREFIX = "Last updated from sources:";
const URL_IN_TEXT = /https?:\/\/[^\s)>"]+/g;

/** Strip embedded footer and any raw URLs from answer body (citation is shown separately). */
export function answerBody(text: string): string {
  const idx = text.indexOf(FOOTER_PREFIX);
  let body = idx === -1 ? text : text.slice(0, idx);
  body = body.replace(URL_IN_TEXT, "").replace(/\s+/g, " ").trim();
  return body;
}

export function formatLastUpdated(isoDate: string): string {
  try {
    const d = new Date(isoDate);
    if (Number.isNaN(d.getTime())) return isoDate;
    return d.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return isoDate;
  }
}

export function structuredSummary(text: string | null | undefined): string {
  if (!text) return "";
  return answerBody(text);
}

export function refusalLabel(reason: string | null): string {
  switch (reason) {
    case "advisory":
      return "Investment advice not provided";
    case "performance":
      return "Performance data not calculated";
    case "out_of_scope":
      return "Outside supported schemes";
    case "pii":
      return "Personal information blocked";
    default:
      return "Response limited";
  }
}
