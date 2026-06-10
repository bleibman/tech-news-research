import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center gap-8 py-24">
      <h1 className="text-3xl font-bold tracking-tight text-foreground">
        Tech News Research
      </h1>
      <p className="font-accent text-sm text-text-secondary tracking-wide">
        RAG-powered digest & live Q&A
      </p>
      <p className="max-w-md text-center text-text-secondary">
        Daily digest of top tech news and live Q&amp;A — powered by RAG with
        citation discipline.
      </p>
      <div className="flex gap-4">
        <Link
          href="/digest"
          className="rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition hover:bg-accent-hover"
        >
          Browse Digests
        </Link>
        <Link
          href="/chat"
          className="rounded-lg border border-border px-6 py-2.5 text-sm font-medium text-foreground transition hover:border-accent hover:text-accent"
        >
          Ask a Question
        </Link>
      </div>
    </div>
  );
}
