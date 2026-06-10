import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center gap-8 py-16">
      <h1 className="text-3xl font-bold tracking-tight">
        Tech News Research
      </h1>
      <p className="max-w-md text-center text-gray-600 dark:text-gray-400">
        Daily digest of top tech news and live Q&A — powered by RAG with
        citation discipline.
      </p>
      <div className="flex gap-4">
        <Link
          href="/digest"
          className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          Browse Digests
        </Link>
        <Link
          href="/chat"
          className="rounded-lg border border-gray-300 px-6 py-2.5 text-sm font-medium hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-900"
        >
          Ask a Question
        </Link>
      </div>
    </div>
  );
}
