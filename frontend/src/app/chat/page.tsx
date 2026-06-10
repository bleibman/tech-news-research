"use client";

import { useState } from "react";
import { askQuestion } from "@/lib/api";
import type { ChatMessage as ChatMessageType } from "@/lib/types";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [loading, setLoading] = useState(false);

  async function handleSend(question: string) {
    const userMsg: ChatMessageType = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await askQuestion(question);
      const assistantMsg: ChatMessageType = {
        role: "assistant",
        content: res.answer,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: ChatMessageType = {
        role: "assistant",
        content:
          "Sorry, something went wrong. Please check that the API is running and try again.",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-10rem)]">
      <h1 className="mb-4 text-2xl font-bold tracking-tight">
        Ask about Tech News
      </h1>

      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.length === 0 && (
          <p className="text-center text-gray-400 dark:text-gray-500 pt-16">
            Ask a question about recent tech news. Answers are backed by
            retrieved sources with citations.
          </p>
        )}
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-lg bg-gray-100 px-4 py-3 text-sm text-gray-500 dark:bg-gray-800 dark:text-gray-400">
              Searching sources and generating answer...
            </div>
          </div>
        )}
      </div>

      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  );
}
