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
  priority_score?: number | null;
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

export interface HealthStatus {
  overall_status: string;
  storage: {
    db_size_gb: number;
    storage_limit_gb: number;
    within_budget: boolean;
  };
  components: {
    component: string;
    status: string;
    ok_count: number;
    error_count: number;
    last_event_at: string | null;
  }[];
  recent_activity: {
    events: {
      component: string;
      phase: string;
      status: string;
      message: string | null;
      payload: Record<string, unknown>;
      created_at: string;
    }[];
  };
  source_recommendations: {
    name: string;
    kind: string;
    url: string;
    score: number;
    reason: string;
    matched_sectors: string[];
  }[];
}

export interface CapitalSector {
  sector: string;
  documents: number;
  papers: number;
  patents: number;
  grants: number;
  company_presence: number;
  funding_usd: number;
  avg_trend_score: number;
  capital_attractiveness: number;
  wealth_thesis: string;
}

export interface CapitalHotspot {
  region: string;
  market_tier: string;
  sector: string;
  document_signals: number;
  company_presence: number;
  funding_usd: number;
  capital_attractiveness: number;
  wealth_thesis: string;
}

export interface CapitalMap {
  majority_sectors: CapitalSector[];
  major_market_hotspots: CapitalHotspot[];
  minor_market_hotspots: CapitalHotspot[];
}

export interface GeoCountryIndustry {
  country: string;
  sector: string;
  documents: number;
  papers: number;
  patents: number;
  grants: number;
  organizations: number;
  opportunities: number;
  risk_score: number;
  risk_factors: string[];
  top_opportunities: string[];
}

export interface GeoCountryRisk {
  country: string;
  sector: string;
  risk_score: number;
  risk_factors: string[];
  top_opportunities: string[];
}

export interface GeoIndustryRisk {
  sector: string;
  countries: number;
  documents: number;
  opportunities: number;
  risk_score: number;
  risk_factors: string[];
}

export interface GeoIndustryMap {
  country_industry: GeoCountryIndustry[];
  country_risks: GeoCountryRisk[];
  industry_risks: GeoIndustryRisk[];
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
  healthStatus: () => getJson<HealthStatus>(`/api/v1/health/status`),
  investorMap: (days = 180, sectors = 10, hotspots = 12) =>
    getJson<CapitalMap>(
      `/api/v1/investor/map?days=${days}&sectors=${sectors}&hotspots=${hotspots}`,
    ),
  marketCapitalMap: (days = 180, sectors = 10, hotspots = 12) =>
    getJson<CapitalMap>(
      `/api/v1/markets/capital-map?days=${days}&sectors=${sectors}&hotspots=${hotspots}`,
    ),
  geoIndustryMap: (days = 180, limit = 12) =>
    getJson<GeoIndustryMap>(
      `/api/v1/markets/geo-industry-map?days=${days}&limit=${limit}`,
    ),
  search: (query: string, limit = 10) =>
    postJson<{ items: SearchItem[] }>(`/api/v1/search`, {
      query,
      limit,
      mode: "hybrid",
    }),
  ask: (question: string, limit = 6) =>
    postJson<AskResponse>(`/api/v1/ask`, { question, limit }),
};
