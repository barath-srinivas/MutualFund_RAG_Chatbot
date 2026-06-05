"use client";

import { useId } from "react";
import { Icon } from "@/components/Icon";
import { SchemeSelector } from "@/components/SchemeSelector";

type Props = {
  input: string;
  onInputChange: (value: string) => void;
  schemeId: string;
  onSchemeChange: (schemeId: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  loading: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  compact?: boolean;
};

export function ChatComposer({
  input,
  onInputChange,
  schemeId,
  onSchemeChange,
  onSubmit,
  loading,
  inputRef,
  compact = false,
}: Props) {
  const formId = useId();

  return (
    <div className="mf-composer">
      <form
        className="mf-composer-form"
        onSubmit={onSubmit}
        aria-labelledby={`${formId}-label`}
      >
        {!compact && (
          <SchemeSelector
            value={schemeId}
            onChange={onSchemeChange}
            disabled={loading}
          />
        )}

        {compact && (
          <div className="mf-mobile-scheme">
            <SchemeSelector
              value={schemeId}
              onChange={onSchemeChange}
              disabled={loading}
            />
          </div>
        )}

        <div className="mf-composer-box">
          <label id={`${formId}-label`} htmlFor={`${formId}-input`} className="sr-only">
            Your question
          </label>
          <textarea
            id={`${formId}-input`}
            ref={inputRef}
            className="mf-textarea"
            rows={compact ? 1 : 2}
            maxLength={4000}
            placeholder="Include the fund name (e.g. bank index fund AUM) or pick a scheme…"
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            disabled={loading}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSubmit(e);
              }
            }}
          />
          <button
            type="submit"
            className="mf-send-btn"
            disabled={loading || !input.trim()}
            aria-label="Send message"
          >
            <Icon name="send" size={20} />
          </button>
        </div>

        <p className="mf-composer-hint">
          {compact
            ? "Name the fund in each question, or keep the scheme selected in the sidebar — follow-ups like “AUM?” use the last answered fund."
            : "Name the fund in your question (e.g. “Large Cap expense ratio”) or select a scheme. No PAN, email, or account details."}
        </p>
      </form>
    </div>
  );
}
