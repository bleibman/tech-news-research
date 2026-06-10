export interface DigestSummary {
  digest_date: string;
  title: string;
}

export interface DigestFull {
  digest_date: string;
  title: string;
  content_md: string;
  citations: Citation[];
}

export interface Citation {
  title: string;
  url: string;
  score?: number;
  num_comments?: number;
  article_id?: number;
}

export interface AskResponse {
  answer: string;
  chunks_used: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
