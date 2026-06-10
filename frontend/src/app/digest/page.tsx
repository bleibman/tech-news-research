import { fetchDigests } from "@/lib/api";
import DigestCard from "@/components/DigestCard";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Digests — Tech News Research",
};

export default async function DigestsPage() {
  const digests = await fetchDigests();

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold tracking-tight text-foreground">
        Daily Digests
      </h1>
      {digests.length === 0 ? (
        <p className="text-text-secondary">
          No digests yet. Run the ingestion pipeline to generate one.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {digests.map((d) => (
            <DigestCard key={d.digest_date} digest={d} />
          ))}
        </div>
      )}
    </div>
  );
}
