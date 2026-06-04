"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AppFooter } from "@/components/AppFooter";
import { AppHeader } from "@/components/AppHeader";
import { ChatComposer } from "@/components/ChatComposer";
import { ChatMessage, type ChatMessageItem } from "@/components/ChatMessage";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { FundsSidebar } from "@/components/FundsSidebar";
import { LoadingBubble } from "@/components/LoadingBubble";
import { WelcomePanel } from "@/components/WelcomePanel";
import type { ExampleQuestion } from "@/data/examples";
import {
  ChatApiError,
  checkHealth,
  postChat,
  type ChatResponse,
} from "@/lib/api";

function nextId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function ChatApp() {
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const disclaimerRef = useRef<HTMLDivElement>(null);

  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [input, setInput] = useState("");
  const [schemeId, setSchemeId] = useState("");
  const [loading, setLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    checkHealth().then((ok) => {
      if (!cancelled) setApiOnline(ok);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  const sendMessage = useCallback(
    async (text: string, scheme: string | null) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;

      const userMsg: ChatMessageItem = {
        id: nextId(),
        role: "user",
        text: trimmed,
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setLoading(true);

      try {
        const response: ChatResponse = await postChat(trimmed, scheme);
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: "assistant", response },
        ]);
        setApiOnline(true);
      } catch (err) {
        const text =
          err instanceof ChatApiError
            ? err.message
            : "Something went wrong. Please try again.";
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: "error", text },
        ]);
        if (err instanceof ChatApiError && err.kind === "network") {
          setApiOnline(false);
        }
      } finally {
        setLoading(false);
        inputRef.current?.focus();
      }
    },
    [loading],
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void sendMessage(input, schemeId || null);
  };

  const handleExample = (example: ExampleQuestion) => {
    setSchemeId(example.scheme_id);
    setInput(example.message);
    void sendMessage(example.message, example.scheme_id);
  };

  const showWelcome = messages.length === 0 && !loading;
  const inChat = messages.length > 0 || loading;

  const scrollToDisclaimer = () => {
    disclaimerRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="mf-app">
      <div className="mf-sticky-top">
        <AppHeader onShowDisclaimer={scrollToDisclaimer} />
        <div ref={disclaimerRef}>
          <DisclaimerBanner />
        </div>
      </div>

      {apiOnline === false && (
        <div className="mf-alert" role="status">
          <p className="mf-alert-box">
            API unreachable — start the backend (
            <code>uvicorn src.main:app</code>) or check{" "}
            <code>NEXT_PUBLIC_API_BASE_URL</code>.
          </p>
        </div>
      )}

      <div className="mf-layout">
        <FundsSidebar
          schemeId={schemeId}
          onSchemeSelect={setSchemeId}
          onClearScheme={() => setSchemeId("")}
        />

        <div className="mf-main">
          <div
            ref={listRef}
            className="mf-chat-scroll"
            aria-live="polite"
            aria-relevant="additions"
          >
            {showWelcome && (
              <WelcomePanel
                onSelectExample={handleExample}
                disabled={loading}
              />
            )}

            {inChat && (
              <div className="mf-content mf-chat-thread">
                {messages.length > 0 && (
                  <span className="mf-date-pill">Today</span>
                )}

                {messages.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} />
                ))}

                {loading && <LoadingBubble />}
              </div>
            )}
          </div>

          <ChatComposer
            input={input}
            onInputChange={setInput}
            schemeId={schemeId}
            onSchemeChange={setSchemeId}
            onSubmit={handleSubmit}
            loading={loading}
            inputRef={inputRef}
            compact={inChat}
          />
        </div>
      </div>

      <AppFooter />
    </div>
  );
}
