import Link from "next/link";
import type { DigestSummary } from "@/lib/types";

export default function DigestCard({ digest }: { digest: DigestSummary }) {
  const formatted = new Date(digest.digest_date + "T00:00:00").toLocaleDateString(
    "en-US",
    { weekday: "long", year: "numeric", month: "long", day: "numeric" }
  );

  return (
    <Link
      href={`/digest/${digest.digest_date}`}
      className="block rounded-lg border border-gray-200 p-4 transition hover:border-blue-400 hover:bg-gray-50 dark:border-gray-800 dark:hover:border-blue-600 dark:hover:bg-gray-900"
    >
      <p className="text-sm text-gray-500 dark:text-gray-400">{formatted}</p>
      <h2 className="mt-1 font-medium">{digest.title}</h2>
    </Link>
  );
}
