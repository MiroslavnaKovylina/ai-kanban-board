"use client";

import { useState } from "react";
import { type ChatHistoryMessage } from "@/lib/auth";

export type SidebarMessage = {
  role: "user" | "assistant";
  content: string;
};

type AiChatSidebarProps = {
  onSend: (prompt: string, history: ChatHistoryMessage[]) => Promise<{ message: string } | null>;
};

export const AiChatSidebar = ({ onSend }: AiChatSidebarProps) => {
  const [messages, setMessages] = useState<SidebarMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitPrompt = async () => {
    const prompt = draft.trim();
    if (!prompt || isSending) {
      return;
    }

    const nextUserMessage: SidebarMessage = {
      role: "user",
      content: prompt,
    };

    const nextMessages = [...messages, nextUserMessage];
    setMessages(nextMessages);
    setDraft("");
    setIsSending(true);
    setError(null);

    const result = await onSend(
      prompt,
      nextMessages.map((message) => ({ role: message.role, content: message.content }))
    );

    if (!result) {
      setError("AI request failed. Please try again.");
      setIsSending(false);
      return;
    }

    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: result.message,
      },
    ]);
    setIsSending(false);
  };

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await submitPrompt();
  };

  const handleDraftKeyDown = async (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      await submitPrompt();
    }
  };

  return (
    <aside className="flex h-full min-h-[520px] flex-col rounded-[28px] border border-[var(--stroke)] bg-white/85 p-5 shadow-[var(--shadow)] backdrop-blur">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">AI Assistant</p>
          <h2 className="mt-1 text-lg font-semibold text-[var(--navy-dark)]">Kanban Assistant</h2>
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] p-3">
        {messages.length === 0 ? (
          <p className="text-sm text-[var(--gray-text)]">
            Ask the AI to create, edit, move, or remove cards.
          </p>
        ) : (
          messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`rounded-2xl px-3 py-2 text-sm leading-6 ${
                message.role === "user"
                  ? "bg-[var(--primary-blue)] text-white"
                  : "bg-white text-[var(--navy-dark)]"
              }`}
            >
              {message.content}
            </div>
          ))
        )}
      </div>

      {error ? <p className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p> : null}

      <form className="mt-4 flex flex-col gap-3" onSubmit={submit}>
        <textarea
          className="min-h-[88px] resize-none rounded-2xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] focus:ring-2 focus:ring-[rgba(32,157,215,0.15)]"
          placeholder="Example: Move all cards from Review to Done, rename column Todo to To Do"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleDraftKeyDown}
          disabled={isSending}
          aria-label="AI prompt"
        />
        <button
          type="submit"
          className="rounded-2xl bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[var(--navy-dark)] disabled:cursor-not-allowed disabled:opacity-70"
          disabled={isSending || !draft.trim()}
        >
          {isSending ? "Sending..." : "Send to AI"}
        </button>
      </form>
    </aside>
  );
};
