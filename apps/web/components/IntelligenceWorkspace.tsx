"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Opportunity } from "@/lib/api";
import { Badge, EmptyState, ErrorState, ScoreBar, Spinner } from "@/components/ui";

type WorkspaceMode = "feed" | "briefing";

type ScoreWeights = {
  research: number;
  commercial: number;
  policy: number;
  ip: number;
  supply: number;
  execution: number;
};

type SavedView = {
  name: string;
  days: number;
  countries: string[];
  sectors: string[];
  minConfidence: number;
  weights: ScoreWeights;
};

type SignalType = "opportunity" | "risk" | "trend";

type SignalItem = {
  id: string;
  type: SignalType;
  title: string;
  sector: string;
  country: string;
  confidence: number;
  score: number;
  delta: number;
  evidenceCount: number;
  freshness: string;
  rationale: string;
  riskFactors: string[];
  topLinks: string[];
  decomposition: {
    research: number;
    commercial: number;
    policy: number;
    ip: number;
    supply: number;
    execution: number;
  };
};

const DEFAULT_WEIGHTS: ScoreWeights = {
  research: 0.21,
  commercial: 0.2,
  policy: 0.17,
  ip: 0.14,
  supply: 0.14,
  execution: 0.14,
};

const COUNTRIES = [
  "China",
  "South Korea",
  "Japan",
  "Europe",
  "India",
  "Southeast Asia",
  "Middle East",
  "Latin America",
  "Africa",
  "Australia",
  "Canada",
  "Global",
];

const SIGNAL_TYPE_STYLE: Record<SignalType, string> = {
  opportunity: "text-emerald-300 border-emerald-500/30 bg-emerald-500/10",
  risk: "text-rose-300 border-rose-500/30 bg-rose-500/10",
  trend: "text-cyan-300 border-cyan-500/30 bg-cyan-500/10",
};

function normalizeWeights(weights: ScoreWeights): ScoreWeights {
  const total =
    weights.research +
    weights.commercial +
    weights.policy +
    weights.ip +
    weights.supply +
    weights.execution;
  if (total <= 0) {
    return DEFAULT_WEIGHTS;
  }
  return {
    research: weights.research / total,
    commercial: weights.commercial / total,
    policy: weights.policy / total,
    ip: weights.ip / total,
    supply: weights.supply / total,
    execution: weights.execution / total,
  };
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function riskToNumber(risk: string | null | undefined): number {
  const v = (risk || "").toLowerCase();
  if (v.includes("high")) return 0.85;
  if (v.includes("medium")) return 0.55;
  if (v.includes("low")) return 0.25;
  return 0.45;
}

function commercialToNumber(commercial: string | null | undefined): number {
  const v = (commercial || "").toLowerCase();
  if (v.includes("high")) return 0.85;
  if (v.includes("medium")) return 0.6;
  if (v.includes("low")) return 0.35;
  return 0.5;
}

function resolveCountry(text: string | null | undefined): string {
  const m = (text || "").toLowerCase();
  const found = COUNTRIES.find((country) =>
    m.includes(country.toLowerCase().replace(" ", "")) || m.includes(country.toLowerCase()),
  );
  return found ?? "Global";
}

function fmtPct(v: number): string {
  return `${Math.round(v * 100)}`;
}

function fmtAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const mins = Math.round(ms / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 48) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

function watchlistMatch(opportunity: Opportunity, tags: string[]): boolean {
  if (tags.length === 0) return true;
  const blob = [
    opportunity.title,
    opportunity.thesis,
    opportunity.technology || "",
    opportunity.market || "",
  ]
    .join(" ")
    .toLowerCase();
  return tags.some((tag) => blob.includes(tag.toLowerCase()));
}

export function IntelligenceWorkspace() {
  const [mode, setMode] = useState<WorkspaceMode>("feed");
  const [days, setDays] = useState(180);
  const [minConfidence, setMinConfidence] = useState(0.45);
  const [weights, setWeights] = useState<ScoreWeights>(DEFAULT_WEIGHTS);
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  const [selectedSectors, setSelectedSectors] = useState<string[]>([]);
  const [watchlistInput, setWatchlistInput] = useState("");
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [savedViews, setSavedViews] = useState<SavedView[]>([]);
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null);

  const qTrends = useQuery({ queryKey: ["workspace-trends"], queryFn: () => api.trends(40) });
  const qOpportunities = useQuery({ queryKey: ["workspace-opps"], queryFn: () => api.opportunities(80) });
  const qGeo = useQuery({ queryKey: ["workspace-geo", days], queryFn: () => api.geoIndustryMap(days, 40) });
  const qHeadlines = useQuery({ queryKey: ["workspace-headlines", days], queryFn: () => api.marketHeadlines(days, 6) });
  const qHealth = useQuery({ queryKey: ["workspace-health"], queryFn: () => api.healthStatus() });

  const loading = qTrends.isLoading || qOpportunities.isLoading || qGeo.isLoading || qHeadlines.isLoading || qHealth.isLoading;
  const error = qTrends.isError || qOpportunities.isError || qGeo.isError || qHeadlines.isError || qHealth.isError;

  const normalized = useMemo(() => normalizeWeights(weights), [weights]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("lazerup_workspace_saved_views");
      if (raw) {
        const parsed = JSON.parse(raw) as SavedView[];
        setSavedViews(parsed);
      }
      const wl = localStorage.getItem("lazerup_workspace_watchlist");
      if (wl) {
        setWatchlist(JSON.parse(wl) as string[]);
      }
    } catch {
      // ignore malformed local state
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("lazerup_workspace_saved_views", JSON.stringify(savedViews));
  }, [savedViews]);

  useEffect(() => {
    localStorage.setItem("lazerup_workspace_watchlist", JSON.stringify(watchlist));
  }, [watchlist]);

  const trendByTechName = useMemo(() => {
    const map = new Map<string, { score: number; sector: string }>();
    for (const t of qTrends.data ?? []) {
      map.set(t.technology.name.toLowerCase(), {
        score: t.composite_score,
        sector: t.technology.category,
      });
    }
    return map;
  }, [qTrends.data]);

  const sectorRisk = useMemo(() => {
    const map = new Map<string, number>();
    for (const row of qGeo.data?.industry_risks ?? []) {
      map.set(row.sector.toLowerCase(), row.risk_score);
    }
    return map;
  }, [qGeo.data]);

  const countryRisk = useMemo(() => {
    const map = new Map<string, number>();
    for (const row of qGeo.data?.country_risks ?? []) {
      const key = row.country.toLowerCase();
      map.set(key, Math.max(map.get(key) ?? 0, row.risk_score));
    }
    return map;
  }, [qGeo.data]);

  const latestEventAt = qHealth.data?.recent_activity.events[0]?.created_at ?? new Date().toISOString();

  const rawSignals = useMemo<SignalItem[]>(() => {
    const items: SignalItem[] = [];

    for (const o of qOpportunities.data ?? []) {
      if (!watchlistMatch(o, watchlist)) continue;

      const trendMeta = o.technology
        ? trendByTechName.get(o.technology.toLowerCase())
        : undefined;
      const sector = trendMeta?.sector ?? "Unknown";
      const country = resolveCountry(o.market);
      const policyRisk = Math.max(
        countryRisk.get(country.toLowerCase()) ?? 0.45,
        sectorRisk.get(sector.toLowerCase()) ?? 0.45,
      );
      const executionRisk = riskToNumber(o.technical_risk);
      const commercial = commercialToNumber(o.commercial_potential);
      const decomposition = {
        research: clamp01(trendMeta?.score ?? 0.5),
        commercial: clamp01(commercial),
        policy: clamp01(1 - policyRisk),
        ip: clamp01((sectorRisk.get(sector.toLowerCase()) ?? 0.5) < 0.6 ? 0.7 : 0.45),
        supply: clamp01((sector.toLowerCase().includes("supply") || sector.toLowerCase().includes("raw")) ? 0.48 : 0.62),
        execution: clamp01(1 - executionRisk),
      };

      const weighted =
        normalized.research * decomposition.research +
        normalized.commercial * decomposition.commercial +
        normalized.policy * decomposition.policy +
        normalized.ip * decomposition.ip +
        normalized.supply * decomposition.supply +
        normalized.execution * decomposition.execution;

      items.push({
        id: `opp-${o.id}`,
        type: "opportunity",
        title: o.title,
        sector,
        country,
        confidence: o.confidence,
        score: weighted,
        delta: weighted - o.score,
        evidenceCount: Object.keys(o.evidence || {}).length,
        freshness: latestEventAt,
        rationale: o.thesis,
        riskFactors: [o.technical_risk || "execution risk"].filter(Boolean),
        topLinks: [],
        decomposition,
      });
    }

    for (const t of qTrends.data?.slice(0, 12) ?? []) {
      const decomposition = {
        research: clamp01(t.components.paper_growth),
        commercial: clamp01(t.components.funding_momentum),
        policy: 0.55,
        ip: clamp01(t.components.patent_growth),
        supply: 0.55,
        execution: 0.6,
      };
      const weighted =
        normalized.research * decomposition.research +
        normalized.commercial * decomposition.commercial +
        normalized.policy * decomposition.policy +
        normalized.ip * decomposition.ip +
        normalized.supply * decomposition.supply +
        normalized.execution * decomposition.execution;

      items.push({
        id: `trend-${t.technology.id}`,
        type: "trend",
        title: `${t.technology.name} accelerating`,
        sector: t.technology.category,
        country: "Global",
        confidence: 0.68,
        score: weighted,
        delta: clamp01(t.components.funding_momentum) - clamp01(t.components.patent_growth),
        evidenceCount: 3,
        freshness: latestEventAt,
        rationale: `Momentum from research (${fmtPct(t.components.paper_growth)}), patents (${fmtPct(t.components.patent_growth)}), and funding (${fmtPct(t.components.funding_momentum)}).`,
        riskFactors: [],
        topLinks: [],
        decomposition,
      });
    }

    for (const r of qGeo.data?.country_risks.slice(0, 16) ?? []) {
      const decomposition = {
        research: 0.4,
        commercial: 0.35,
        policy: clamp01(1 - r.risk_score),
        ip: r.risk_factors.some((x) => x.toLowerCase().includes("ip")) ? 0.35 : 0.55,
        supply: r.risk_factors.some((x) => x.toLowerCase().includes("density")) ? 0.4 : 0.55,
        execution: clamp01(1 - Math.min(0.95, r.risk_score)),
      };
      items.push({
        id: `risk-${r.country}-${r.sector}`,
        type: "risk",
        title: `${r.country} ${r.sector} concentration risk`,
        sector: r.sector,
        country: r.country,
        confidence: 0.72,
        score: clamp01(r.risk_score),
        delta: 0,
        evidenceCount: Math.max(1, r.risk_factors.length),
        freshness: latestEventAt,
        rationale: `Risk is elevated due to ${r.risk_factors.join(", ") || "execution pressure"}.`,
        riskFactors: r.risk_factors,
        topLinks: r.top_opportunities,
        decomposition,
      });
    }

    return items;
  }, [
    qOpportunities.data,
    qTrends.data,
    qGeo.data,
    latestEventAt,
    normalized,
    trendByTechName,
    watchlist,
    countryRisk,
    sectorRisk,
  ]);

  const availableCountries = useMemo(() => {
    const fromGeo = new Set((qGeo.data?.country_industry ?? []).map((x) => x.country));
    return Array.from(fromGeo).sort();
  }, [qGeo.data]);

  const availableSectors = useMemo(() => {
    const fromSignals = new Set(rawSignals.map((x) => x.sector));
    return Array.from(fromSignals).sort();
  }, [rawSignals]);

  const signals = useMemo(() => {
    return rawSignals
      .filter((x) => x.confidence >= minConfidence)
      .filter((x) => (selectedCountries.length === 0 ? true : selectedCountries.includes(x.country)))
      .filter((x) => (selectedSectors.length === 0 ? true : selectedSectors.includes(x.sector)))
      .sort((a, b) => b.score - a.score);
  }, [rawSignals, minConfidence, selectedCountries, selectedSectors]);

  const selectedSignal = useMemo(() => {
    if (signals.length === 0) return null;
    if (!selectedSignalId) return signals[0];
    return signals.find((x) => x.id === selectedSignalId) ?? signals[0];
  }, [signals, selectedSignalId]);

  const matrix = useMemo(() => {
    const countries = Array.from(
      new Set((qGeo.data?.country_industry ?? []).map((x) => x.country)),
    ).slice(0, 8);
    const sectors = Array.from(
      new Set((qGeo.data?.country_industry ?? []).map((x) => x.sector)),
    ).slice(0, 8);
    const cell = new Map<string, number>();
    for (const row of qGeo.data?.country_industry ?? []) {
      cell.set(`${row.country}||${row.sector}`, row.risk_score);
    }
    return { countries, sectors, cell };
  }, [qGeo.data]);

  const briefing = useMemo(() => {
    const topSignals = signals.slice(0, 5);
    const topRisks = signals.filter((s) => s.type === "risk").slice(0, 3);
    const avgConfidence =
      signals.length > 0
        ? signals.reduce((acc, s) => acc + s.confidence, 0) / signals.length
        : 0;
    const headlineCount =
      (qHeadlines.data?.major_markets ?? []).reduce(
        (acc, market) => acc + market.headlines.length,
        0,
      ) +
      (qHeadlines.data?.minor_markets ?? []).reduce(
        (acc, market) => acc + market.headlines.length,
        0,
      );

    const lead =
      topSignals.length > 0
        ? `Top live signal: ${topSignals[0].title} (${fmtPct(topSignals[0].score)} / confidence ${fmtPct(topSignals[0].confidence)}).`
        : "No high-confidence signals meet the current filters.";

    const riskLine =
      topRisks.length > 0
        ? `Key risks this cycle: ${topRisks.map((r) => `${r.country} ${r.sector}`).join(", ")}.`
        : "No elevated country/industry risks in the current selection.";

    return {
      lead,
      riskLine,
      narrative: `Coverage window ${days} days with ${signals.length} ranked signals, average confidence ${fmtPct(avgConfidence)}, and ${headlineCount} recent market headlines.`,
      topSignals,
      topRisks,
    };
  }, [days, qHeadlines.data, signals]);

  if (loading) return <Spinner />;
  if (error) return <ErrorState message="Couldn't load intelligence workspace data." />;
  if (!qOpportunities.data || !qGeo.data) {
    return <EmptyState message="Workspace has no data yet." />;
  }

  return (
    <section className="space-y-4">
      <div className="card p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wider text-neutral-500">Intelligence Workspace</p>
            <h2 className="text-xl font-semibold tracking-tight text-neutral-100">Signal Command Center</h2>
            <p className="text-sm text-neutral-400">Prioritized signals with explainability, confidence, and country-industry linkage.</p>
          </div>
          <div className="flex gap-2">
            <button
              className={`rounded-lg px-3 py-1.5 text-xs ${mode === "feed" ? "bg-white/10 text-white" : "bg-white/5 text-neutral-300"}`}
              onClick={() => setMode("feed")}
            >
              Analyst Feed
            </button>
            <button
              className={`rounded-lg px-3 py-1.5 text-xs ${mode === "briefing" ? "bg-white/10 text-white" : "bg-white/5 text-neutral-300"}`}
              onClick={() => setMode("briefing")}
            >
              Briefing Mode
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)_360px]">
        <aside className="space-y-3">
          <div className="card p-4 space-y-3">
            <p className="text-xs uppercase tracking-wide text-neutral-500">Time horizon</p>
            <div className="flex flex-wrap gap-2">
              {[30, 90, 180, 365].map((value) => (
                <button
                  key={value}
                  className={`rounded-full border px-2.5 py-1 text-xs ${days === value ? "border-emerald-400/40 bg-emerald-500/10 text-emerald-200" : "border-white/10 bg-white/5 text-neutral-300"}`}
                  onClick={() => setDays(value)}
                >
                  {value}d
                </button>
              ))}
            </div>
          </div>

          <div className="card p-4 space-y-3">
            <p className="text-xs uppercase tracking-wide text-neutral-500">Weight controls</p>
            <WeightSlider label="Research" value={weights.research} onChange={(v) => setWeights((w) => ({ ...w, research: v }))} />
            <WeightSlider label="Commercial" value={weights.commercial} onChange={(v) => setWeights((w) => ({ ...w, commercial: v }))} />
            <WeightSlider label="Policy" value={weights.policy} onChange={(v) => setWeights((w) => ({ ...w, policy: v }))} />
            <WeightSlider label="IP" value={weights.ip} onChange={(v) => setWeights((w) => ({ ...w, ip: v }))} />
            <WeightSlider label="Supply" value={weights.supply} onChange={(v) => setWeights((w) => ({ ...w, supply: v }))} />
            <WeightSlider label="Execution" value={weights.execution} onChange={(v) => setWeights((w) => ({ ...w, execution: v }))} />
            <div className="text-xs text-neutral-500">Normalized automatically to keep scoring stable.</div>
          </div>

          <div className="card p-4 space-y-3">
            <p className="text-xs uppercase tracking-wide text-neutral-500">Filters</p>
            <div>
              <label className="text-xs text-neutral-400">Min confidence: {fmtPct(minConfidence)}</label>
              <input
                className="mt-1 w-full"
                type="range"
                min={0.2}
                max={0.95}
                step={0.01}
                value={minConfidence}
                onChange={(e) => setMinConfidence(Number(e.target.value))}
              />
            </div>
            <SelectorGroup
              title="Countries"
              values={availableCountries}
              selected={selectedCountries}
              onToggle={(value) =>
                setSelectedCountries((prev) =>
                  prev.includes(value) ? prev.filter((x) => x !== value) : [...prev, value],
                )
              }
            />
            <SelectorGroup
              title="Sectors"
              values={availableSectors}
              selected={selectedSectors}
              onToggle={(value) =>
                setSelectedSectors((prev) =>
                  prev.includes(value) ? prev.filter((x) => x !== value) : [...prev, value],
                )
              }
            />
          </div>

          <div className="card p-4 space-y-3">
            <p className="text-xs uppercase tracking-wide text-neutral-500">Watchlist and saved views</p>
            <div className="flex gap-2">
              <input
                value={watchlistInput}
                onChange={(e) => setWatchlistInput(e.target.value)}
                placeholder="Add keyword"
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm outline-none focus:border-emerald-400/40"
              />
              <button
                onClick={() => {
                  const token = watchlistInput.trim();
                  if (!token) return;
                  if (!watchlist.includes(token)) setWatchlist((prev) => [...prev, token]);
                  setWatchlistInput("");
                }}
                className="rounded-lg bg-white/10 px-2.5 text-xs text-white"
              >
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {watchlist.map((tag) => (
                <button
                  key={tag}
                  onClick={() => setWatchlist((prev) => prev.filter((x) => x !== tag))}
                  className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-neutral-300"
                >
                  {tag} ×
                </button>
              ))}
            </div>
            <button
              className="w-full rounded-lg bg-emerald-500/20 px-3 py-1.5 text-xs text-emerald-200"
              onClick={() => {
                const name = `View ${savedViews.length + 1}`;
                setSavedViews((prev) => [
                  ...prev,
                  {
                    name,
                    days,
                    countries: selectedCountries,
                    sectors: selectedSectors,
                    minConfidence,
                    weights,
                  },
                ]);
              }}
            >
              Save current view
            </button>
            <div className="space-y-1">
              {savedViews.slice(-4).map((view) => (
                <button
                  key={view.name}
                  className="flex w-full items-center justify-between rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.5 text-xs text-neutral-300"
                  onClick={() => {
                    setDays(view.days);
                    setSelectedCountries(view.countries);
                    setSelectedSectors(view.sectors);
                    setMinConfidence(view.minConfidence);
                    setWeights(view.weights);
                  }}
                >
                  <span>{view.name}</span>
                  <span className="text-neutral-500">load</span>
                </button>
              ))}
            </div>
          </div>
        </aside>

        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label="Signals" value={`${signals.length}`} />
            <Stat
              label="Avg confidence"
              value={`${fmtPct(signals.reduce((acc, s) => acc + s.confidence, 0) / Math.max(1, signals.length))}`}
            />
            <Stat
              label="High-risk alerts"
              value={`${signals.filter((s) => s.type === "risk" && s.score >= 0.75).length}`}
            />
            <Stat label="Freshness" value={fmtAgo(latestEventAt)} />
          </div>

          {mode === "briefing" ? (
            <div className="card p-4 space-y-4">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-base font-semibold">Analyst briefing</h3>
                <button
                  className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-neutral-200"
                  onClick={async () => {
                    const body = [
                      briefing.lead,
                      briefing.riskLine,
                      briefing.narrative,
                      "Top signals:",
                      ...briefing.topSignals.map((s, i) => `${i + 1}. ${s.title} (${fmtPct(s.score)})`),
                    ].join("\n");
                    await navigator.clipboard.writeText(body);
                  }}
                >
                  Copy briefing
                </button>
              </div>
              <p className="text-sm text-neutral-200">{briefing.lead}</p>
              <p className="text-sm text-neutral-300">{briefing.riskLine}</p>
              <p className="text-sm text-neutral-400">{briefing.narrative}</p>
              <div className="grid gap-3 lg:grid-cols-2">
                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <h4 className="mb-2 text-xs uppercase tracking-wide text-neutral-500">Top ranked signals</h4>
                  <ol className="space-y-1 text-sm text-neutral-200">
                    {briefing.topSignals.map((s, i) => (
                      <li key={s.id}>{i + 1}. {s.title}</li>
                    ))}
                  </ol>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <h4 className="mb-2 text-xs uppercase tracking-wide text-neutral-500">Elevated risks</h4>
                  <ol className="space-y-1 text-sm text-neutral-200">
                    {briefing.topRisks.map((s, i) => (
                      <li key={s.id}>{i + 1}. {s.title}</li>
                    ))}
                  </ol>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="card p-4">
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">Prioritized signal feed</h3>
                {signals.length === 0 ? (
                  <EmptyState message="No signals match the current filters." />
                ) : (
                  <div className="space-y-2">
                    {signals.slice(0, 24).map((signal) => (
                      <button
                        key={signal.id}
                        onClick={() => setSelectedSignalId(signal.id)}
                        className={`w-full rounded-xl border p-3 text-left transition ${selectedSignal?.id === signal.id ? "border-emerald-400/35 bg-emerald-500/10" : "border-white/10 bg-white/5 hover:border-white/20"}`}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className={`rounded-full border px-2 py-0.5 text-[11px] ${SIGNAL_TYPE_STYLE[signal.type]}`}>
                                {signal.type}
                              </span>
                              <Badge>{signal.country}</Badge>
                              <Badge>{signal.sector}</Badge>
                            </div>
                            <h4 className="mt-2 text-sm font-medium text-neutral-100">{signal.title}</h4>
                            <p className="mt-1 line-clamp-2 text-xs text-neutral-400">{signal.rationale}</p>
                          </div>
                          <div className="text-right text-xs text-neutral-400">
                            <div>Score {fmtPct(signal.score)}</div>
                            <div className={signal.delta >= 0 ? "text-emerald-300" : "text-rose-300"}>
                              Δ {signal.delta >= 0 ? "+" : ""}{fmtPct(Math.abs(signal.delta))}
                            </div>
                          </div>
                        </div>
                        <div className="mt-3 grid grid-cols-3 gap-3 text-xs text-neutral-500">
                          <span>confidence {fmtPct(signal.confidence)}</span>
                          <span>evidence {signal.evidenceCount}</span>
                          <span>freshness {fmtAgo(signal.freshness)}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="card p-4">
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">Country x industry matrix</h3>
                <div className="overflow-auto">
                  <table className="min-w-full border-separate border-spacing-1">
                    <thead>
                      <tr>
                        <th className="px-2 py-1 text-left text-xs text-neutral-500">Country</th>
                        {matrix.sectors.map((sector) => (
                          <th key={sector} className="px-2 py-1 text-xs text-neutral-500">{sector}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {matrix.countries.map((country) => (
                        <tr key={country}>
                          <td className="px-2 py-1 text-xs text-neutral-300">{country}</td>
                          {matrix.sectors.map((sector) => {
                            const value = matrix.cell.get(`${country}||${sector}`) ?? 0;
                            const opacity = Math.max(0.08, Math.min(0.92, value));
                            return (
                              <td key={`${country}-${sector}`} className="px-1 py-1">
                                <button
                                  className="w-full rounded-md px-2 py-1 text-center text-[11px]"
                                  style={{
                                    backgroundColor: `rgba(34, 211, 238, ${opacity * 0.35})`,
                                    border: "1px solid rgba(255,255,255,0.08)",
                                  }}
                                  onClick={() => {
                                    setSelectedCountries([country]);
                                    setSelectedSectors([sector]);
                                  }}
                                >
                                  {fmtPct(value)}
                                </button>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        <aside className="space-y-3">
          <div className="card p-4">
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">Explainability</h3>
            {!selectedSignal ? (
              <EmptyState message="Select a signal to inspect decomposition." />
            ) : (
              <div className="space-y-3">
                <div>
                  <div className="text-sm font-medium text-neutral-100">{selectedSignal.title}</div>
                  <div className="mt-1 flex flex-wrap gap-2">
                    <Badge>{selectedSignal.country}</Badge>
                    <Badge>{selectedSignal.sector}</Badge>
                    <Badge>{selectedSignal.type}</Badge>
                  </div>
                </div>

                <div className="space-y-2">
                  <BreakdownRow label="Research" value={selectedSignal.decomposition.research} weight={normalized.research} />
                  <BreakdownRow label="Commercial" value={selectedSignal.decomposition.commercial} weight={normalized.commercial} />
                  <BreakdownRow label="Policy" value={selectedSignal.decomposition.policy} weight={normalized.policy} />
                  <BreakdownRow label="IP" value={selectedSignal.decomposition.ip} weight={normalized.ip} />
                  <BreakdownRow label="Supply" value={selectedSignal.decomposition.supply} weight={normalized.supply} />
                  <BreakdownRow label="Execution" value={selectedSignal.decomposition.execution} weight={normalized.execution} />
                </div>

                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <p className="text-xs uppercase tracking-wide text-neutral-500">Rationale</p>
                  <p className="mt-1 text-sm text-neutral-300">{selectedSignal.rationale}</p>
                </div>

                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <p className="text-xs uppercase tracking-wide text-neutral-500">Risk factors</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {selectedSignal.riskFactors.length === 0 ? (
                      <span className="text-xs text-neutral-500">No explicit risk factors.</span>
                    ) : (
                      selectedSignal.riskFactors.map((risk) => <Badge key={risk}>{risk}</Badge>)
                    )}
                  </div>
                </div>

                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <p className="text-xs uppercase tracking-wide text-neutral-500">Evidence and linked opportunities</p>
                  <ul className="mt-2 space-y-1 text-xs text-neutral-300">
                    {selectedSignal.topLinks.length === 0 ? (
                      <li>No direct opportunity links.</li>
                    ) : (
                      selectedSignal.topLinks.slice(0, 4).map((item) => <li key={item}>• {item}</li>)
                    )}
                  </ul>
                </div>
              </div>
            )}
          </div>

          <div className="card p-4">
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">What changed</h3>
            <ul className="space-y-2 text-sm text-neutral-300">
              {signals.slice(0, 4).map((signal) => (
                <li key={`delta-${signal.id}`}>
                  <span className="font-medium text-neutral-100">{signal.title}</span>
                  <span className="text-neutral-500"> · Δ {signal.delta >= 0 ? "+" : ""}{fmtPct(Math.abs(signal.delta))}</span>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="card p-3">
      <div className="text-xs uppercase tracking-wide text-neutral-500">{label}</div>
      <div className="mt-1 text-lg font-semibold text-neutral-100">{value}</div>
    </div>
  );
}

function WeightSlider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (next: number) => void;
}) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs text-neutral-400">
        <span>{label}</span>
        <span>{fmtPct(value)}</span>
      </div>
      <input
        type="range"
        min={0}
        max={1}
        step={0.01}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full"
      />
    </div>
  );
}

function SelectorGroup({
  title,
  values,
  selected,
  onToggle,
}: {
  title: string;
  values: string[];
  selected: string[];
  onToggle: (value: string) => void;
}) {
  return (
    <div>
      <p className="mb-2 text-xs text-neutral-500">{title}</p>
      <div className="max-h-32 space-y-1 overflow-auto pr-1">
        {values.slice(0, 16).map((value) => (
          <label key={value} className="flex items-center gap-2 text-xs text-neutral-300">
            <input
              type="checkbox"
              checked={selected.includes(value)}
              onChange={() => onToggle(value)}
              className="rounded border-white/20 bg-transparent"
            />
            <span>{value}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

function BreakdownRow({
  label,
  value,
  weight,
}: {
  label: string;
  value: number;
  weight: number;
}) {
  const contribution = value * weight;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-neutral-400">
        <span>{label}</span>
        <span>{fmtPct(contribution)} contribution</span>
      </div>
      <ScoreBar value={contribution} />
    </div>
  );
}
