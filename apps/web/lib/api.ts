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
  };
  rank: number;
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  trends: (window = "90d", limit = 20) =>
    getJson<TrendItem[]>(`/api/v1/trends?window=${window}&limit=${limit}`),
  ping: () => getJson<{ status: string; version: string }>(`/api/v1/ping`),
};
