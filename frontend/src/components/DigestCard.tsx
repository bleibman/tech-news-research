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
      className="block rounded-lg border border-border bg-surface p-4 transition hover:border-accent"
    >
      <p className="font-accent text-xs text-text-secondary">{formatted}</p>
      <h2 className="mt-1.5 font-medium text-foreground">{digest.title}</h2>
    </Link>
  );
}
