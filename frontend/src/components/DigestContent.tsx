"use client";

import ReactMarkdown from "react-markdown";

export default function DigestContent({ markdown }: { markdown: string }) {
  return (
    <article className="prose prose-gray dark:prose-invert max-w-none">
      <ReactMarkdown>{markdown}</ReactMarkdown>
    </article>
  );
}
