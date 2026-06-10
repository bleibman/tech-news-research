import Link from "next/link";

export default function Header() {
  return (
    <header className="border-b border-gray-200 dark:border-gray-800">
      <nav className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
        <Link
          href="/"
          className="text-lg font-semibold tracking-tight hover:opacity-80"
        >
          Tech News Research
        </Link>
        <div className="flex gap-6 text-sm font-medium">
          <Link
            href="/digest"
            className="hover:text-blue-600 dark:hover:text-blue-400"
          >
            Digest
          </Link>
          <Link
            href="/chat"
            className="hover:text-blue-600 dark:hover:text-blue-400"
          >
            Chat
          </Link>
        </div>
      </nav>
    </header>
  );
}
