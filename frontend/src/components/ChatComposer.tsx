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
            placeholder="Ask about expense ratio, exit load, SIP, fund manager…"
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
            ? "Information sourced from official Scheme Information Documents."
            : "No PAN, email, phone, or account details — chat only."}
        </p>
      </form>
    </div>
  );
}
