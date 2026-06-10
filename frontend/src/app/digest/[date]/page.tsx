import { fetchDigest } from "@/lib/api";
import DigestContent from "@/components/DigestContent";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ date: string }>;
}) {
  const { date } = await params;
  return { title: `Digest ${date} — Tech News Research` };
}

export default async function DigestDatePage({
  params,
}: {
  params: Promise<{ date: string }>;
}) {
  const { date } = await params;

  let digest;
  try {
    digest = await fetchDigest(date);
  } catch {
    notFound();
  }

  const formatted = new Date(digest.digest_date + "T00:00:00").toLocaleDateString(
    "en-US",
    { weekday: "long", year: "numeric", month: "long", day: "numeric" }
  );

  return (
    <div>
      <Link
        href="/digest"
        className="mb-4 inline-block text-sm text-blue-600 hover:underline dark:text-blue-400"
      >
        &larr; All digests
      </Link>
      <p className="mb-1 text-sm text-gray-500 dark:text-gray-400">
        {formatted}
      </p>
      <h1 className="mb-6 text-2xl font-bold tracking-tight">
        {digest.title}
      </h1>
      <DigestContent markdown={digest.content_md} />
    </div>
  );
}
