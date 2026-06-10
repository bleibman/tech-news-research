import type { DigestSummary, DigestFull, AskResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchDigests(
  limit = 30,
  offset = 0
): Promise<DigestSummary[]> {
  const res = await fetch(
    `${API_URL}/digests?limit=${limit}&offset=${offset}`,
    { next: { revalidate: 300 } }
  );
  if (!res.ok) throw new Error(`Failed to fetch digests: ${res.status}`);
  return res.json();
}

export async function fetchDigest(date: string): Promise<DigestFull> {
  const res = await fetch(`${API_URL}/digests/${date}`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) throw new Error(`Failed to fetch digest: ${res.status}`);
  return res.json();
}

export async function askQuestion(
  question: string,
  topK = 8
): Promise<AskResponse> {
  const res = await fetch(`${API_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });
  if (!res.ok) throw new Error(`Ask failed: ${res.status}`);
  return res.json();
}
