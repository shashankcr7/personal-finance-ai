"use client";

import { useEffect, useState } from "react";

import { apiGet, apiPostJson, ApiError } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    let active = true;
    apiGet("/chat/history")
      .then((data: ChatMessage[]) => {
        if (active) setMessages(data);
      })
      .catch(() => {
        // history failed to load — start with an empty chat rather than blocking input
      })
      .finally(() => {
        if (active) setLoadingHistory(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleSend(event: React.FormEvent) {
    event.preventDefault();
    const message = input.trim();
    if (!message) return;

    const history = messages;
    const nextMessages: ChatMessage[] = [...history, { role: "user", content: message }];
    setMessages(nextMessages);
    setInput("");
    setSending(true);

    try {
      const result = await apiPostJson("/chat", { message, history });
      setMessages([...nextMessages, { role: "assistant", content: result.response }]);
    } catch (err) {
      const detail =
        err instanceof ApiError && err.status === 404
          ? "The chat agent isn't available yet."
          : err instanceof ApiError
            ? err.message
            : "Something went wrong reaching the chat agent.";
      setMessages([...nextMessages, { role: "assistant", content: detail }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-full max-w-3xl flex-col">
      <h1 className="text-xl font-semibold text-gray-900">Chat</h1>

      <div className="mt-4 flex-1 space-y-3 overflow-y-auto rounded-lg border border-gray-200 bg-white p-4">
        {loadingHistory && (
          <p className="text-sm text-gray-500">Loading conversation…</p>
        )}
        {!loadingHistory && messages.length === 0 && (
          <p className="text-sm text-gray-500">
            Ask about your spending, leaks, or goal progress.
          </p>
        )}
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                message.role === "user"
                  ? "bg-gray-900 text-white"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              {message.content}
            </div>
          </div>
        ))}
        {sending && <p className="text-sm text-gray-400">Thinking…</p>}
      </div>

      <form onSubmit={handleSend} className="mt-3 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Where am I losing money?"
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={sending}
          className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>

      <p className="mt-2 text-xs text-gray-500">
        Answers are grounded in your actual numbers. No buy/sell recommendations.
      </p>
      <p className="text-xs text-gray-500">
        The agent reads pre-computed numbers — it never does the math itself.
      </p>
    </div>
  );
}
