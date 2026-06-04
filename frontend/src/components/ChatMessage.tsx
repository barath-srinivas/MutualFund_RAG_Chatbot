import { Icon } from "@/components/Icon";
import { StructuredTable } from "@/components/StructuredTable";
import { APP_PRODUCT_LABEL } from "@/lib/app-config";
import type { ChatResponse } from "@/lib/api";
import {
  answerBody,
  formatLastUpdated,
  refusalLabel,
  structuredSummary,
} from "@/lib/format";

export type ChatMessageItem =
  | { id: string; role: "user"; text: string }
  | {
      id: string;
      role: "assistant";
      response: ChatResponse;
    }
  | { id: string; role: "error"; text: string };

type Props = {
  message: ChatMessageItem;
};

export function ChatMessage({ message }: Props) {
  if (message.role === "user") {
    return (
      <div className="mf-msg-user-wrap">
        <div className="mf-msg-user">
          <p>{message.text}</p>
        </div>
      </div>
    );
  }

  if (message.role === "error") {
    return (
      <div className="mf-msg-row" role="alert">
        <div className="mf-avatar mf-avatar--error">
          <Icon name="error" size={20} />
        </div>
        <div className="mf-msg-bubble mf-msg-bubble--error">
          <Icon name="cloud_off" size={20} />
          <p className="mf-msg-body">{message.text}</p>
        </div>
      </div>
    );
  }

  const { response } = message;
  const isRefusal = response.type === "refusal";
  const isStructured =
    response.type === "structured" && response.structured != null;

  return (
    <div className="mf-msg-row">
      <div className="mf-avatar">
        <Icon name="smart_toy" size={20} />
      </div>
      <div
        className={`mf-msg-bubble${isRefusal ? " mf-msg-bubble--refusal" : ""}`}
      >
        {isRefusal && (
          <div className="mf-msg-label">
            <Icon name="warning" size={18} />
            <span>{refusalLabel(response.refusal_reason)}</span>
          </div>
        )}

        {!isRefusal && !isStructured && (
          <div className="mf-msg-brand">
            <Icon name="neurology" size={18} />
            <span>{APP_PRODUCT_LABEL}</span>
          </div>
        )}

        {isStructured && response.structured?.summary && (
          <p className="mf-msg-body" style={{ marginBottom: "1rem" }}>
            {structuredSummary(response.structured.summary)}
          </p>
        )}

        {isStructured && response.structured && (
          <StructuredTable data={response.structured} />
        )}

        {!isStructured && (
          <p className="mf-msg-body">{answerBody(response.answer)}</p>
        )}

        {response.citation_url && (
          <div className="mf-msg-footer">
            <a
              href={response.citation_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mf-link"
            >
              <Icon name="open_in_new" size={14} />
              Official source
            </a>
            <span className="mf-meta">
              Last updated from sources:{" "}
              {formatLastUpdated(response.last_updated)}
            </span>
          </div>
        )}

        {!response.citation_url && response.last_updated && (
          <p className="mf-meta" style={{ marginTop: "0.5rem" }}>
            Last updated from sources:{" "}
            {formatLastUpdated(response.last_updated)}
          </p>
        )}
      </div>
    </div>
  );
}
