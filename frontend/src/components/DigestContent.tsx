"use client";

import ReactMarkdown from "react-markdown";

export default function DigestContent({ markdown }: { markdown: string }) {
  return (
    <article className="prose prose-invert max-w-none prose-headings:text-foreground prose-p:text-foreground prose-a:text-accent prose-a:no-underline hover:prose-a:text-accent-hover prose-strong:text-foreground prose-code:text-accent-hover">
      <ReactMarkdown>{markdown}</ReactMarkdown>
    </article>
  );
}
