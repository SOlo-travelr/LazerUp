// Typed client for the Battery Opportunity Scanner API.
// All calls run from the browser, so they target the public API URL.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Technology {
  id: string;
  slug: string;
  name: string;
  category: string;
}

export interface TrendItem {
  technology: Technology;
  composite_score: number;
  components: {
    paper_growth: number;
    patent_growth: number;
    funding_momentum: number;
    grant_momentum?: number;
  };
  rank: number;
}

export interface Opportunity {
  id: string;
  title: string;
  thesis: string;
  technology: string | null;
  market: string | null;
  technical_risk: string | null;
  commercial_potential: string | null;
  score: number;
  confidence: number;
  evidence: Record<string, unknown>;
}

export interface WhiteSpace {
  id: string;
  technology: string | null;
  research_activity: number;
  funding_present: number;
  startup_density: number;
  whitespace_score: number;
  rationale: string | null;
}

export interface Bottleneck {
  id: string;
  technology: string | null;
  problem_statement: string;
  frequency: number;
  severity: number;
}

export interface SearchItem {
  id: string;
  doc_type: string;
  title: string;
  score: number;
  snippet: string | null;
  url: string | null;
}

export interface AskResponse {
  answer: string;
  citations: { id: string; title: string; url: string | null }[];
  grounded: boolean;
}

export interface WeeklyReport {
  week_start: string;
  generated_at: string | null;
  payload: {
    summary?: string;
    top_technologies?: { name: string; score: number }[];
    top_opportunities?: { title: string; score: number }[];
    top_grants?: { title: string; program: string | null; amount_usd: number }[];
    top_patents?: { title: string; patent_number: string | null }[];
    top_funding?: { org: string | null; round: string | null; amount_usd: number }[];
    [key: string]: unknown;
  };
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  trends: (limit = 20) => getJson<TrendItem[]>(`/api/v1/trends?limit=${limit}`),
  opportunities: (limit = 20) =>
    getJson<Opportunity[]>(`/api/v1/opportunities?limit=${limit}`),
  whiteSpaces: (limit = 20) =>
    getJson<WhiteSpace[]>(`/api/v1/white-spaces?limit=${limit}`),
  bottlenecks: (limit = 20) =>
    getJson<Bottleneck[]>(`/api/v1/bottlenecks?limit=${limit}`),
  latestReport: () => getJson<WeeklyReport>(`/api/v1/reports/latest`),
  search: (query: string, limit = 10) =>
    postJson<{ items: SearchItem[] }>(`/api/v1/search`, {
      query,
      limit,
      mode: "hybrid",
    }),
  ask: (question: string, limit = 6) =>
    postJson<AskResponse>(`/api/v1/ask`, { question, limit }),
};
