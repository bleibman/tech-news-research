import Link from "next/link";

export default function Header() {
  return (
    <header className="border-b border-border">
      <nav className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
        <Link
          href="/"
          className="font-accent text-lg font-semibold tracking-tight text-foreground hover:text-accent-hover transition"
        >
          tech-news
        </Link>
        <div className="flex items-center gap-1 text-sm font-medium">
          <Link
            href="/digest"
            className="rounded-md px-3 py-1.5 text-text-secondary transition hover:bg-surface hover:text-foreground"
          >
            Digest
          </Link>
          <span className="text-border">/</span>
          <Link
            href="/chat"
            className="rounded-md px-3 py-1.5 text-text-secondary transition hover:bg-surface hover:text-foreground"
          >
            Chat
          </Link>
        </div>
      </nav>
    </header>
  );
}
