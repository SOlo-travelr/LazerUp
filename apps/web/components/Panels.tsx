"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Badge, EmptyState, ErrorState, Rank, ScoreBar, Spinner } from "./ui";

function PanelState({
  loading,
  error,
  empty,
  emptyMessage,
  children,
}: {
  loading: boolean;
  error: boolean;
  empty: boolean;
  emptyMessage: string;
  children: React.ReactNode;
}) {
  if (loading) return <Spinner />;
  if (error)
    return <ErrorState message="Couldn't load data. Is the API running?" />;
  if (empty) return <EmptyState message={emptyMessage} />;
  return <>{children}</>;
}

export function TrendsPanel() {
  const q = useQuery({ queryKey: ["trends"], queryFn: () => api.trends() });
  return (
    <PanelState
      loading={q.isLoading}
      error={q.isError}
      empty={(q.data ?? []).length === 0}
      emptyMessage="No trend data yet. Run analytics to populate trends."
    >
      <ul className="space-y-2">
        {(q.data ?? []).map((t) => (
          <li key={t.technology.id} className="card px-4 py-3">
            <div className="flex items-center gap-3">
              <Rank n={t.rank} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate font-medium">
                    {t.technology.name}
                  </span>
                  <Badge>{t.technology.category}</Badge>
                </div>
              </div>
              <div className="w-40 sm:w-56">
                <ScoreBar value={t.composite_score} />
              </div>
            </div>
          </li>
        ))}
      </ul>
    </PanelState>
  );
}

export function OpportunitiesPanel() {
  const q = useQuery({
    queryKey: ["opportunities"],
    queryFn: () => api.opportunities(),
  });
  return (
    <PanelState
      loading={q.isLoading}
      error={q.isError}
      empty={(q.data ?? []).length === 0}
      emptyMessage="No opportunities surfaced yet. They appear as evidence accumulates."
    >
      <div className="grid gap-3 sm:grid-cols-2">
        {(q.data ?? []).map((o) => (
          <article key={o.id} className="card flex flex-col gap-3 p-4">
            <div className="flex items-start justify-between gap-3">
              <h3 className="font-medium leading-snug">{o.title}</h3>
              {o.technology && <Badge>{o.technology}</Badge>}
            </div>
            <p className="line-clamp-3 text-sm text-neutral-400">{o.thesis}</p>
            <div className="mt-auto space-y-2">
              <ScoreBar value={o.score} />
              <div className="flex flex-wrap gap-2 text-xs text-neutral-500">
                {o.market && <span>Market: {o.market}</span>}
                {o.technical_risk && <span>· Risk: {o.technical_risk}</span>}
              </div>
            </div>
          </article>
        ))}
      </div>
    </PanelState>
  );
}

export function WhiteSpacePanel() {
  const q = useQuery({
    queryKey: ["white-spaces"],
    queryFn: () => api.whiteSpaces(),
  });
  return (
    <PanelState
      loading={q.isLoading}
      error={q.isError}
      empty={(q.data ?? []).length === 0}
      emptyMessage="No white spaces detected yet."
    >
      <ul className="space-y-2">
        {(q.data ?? []).map((w) => (
          <li key={w.id} className="card p-4">
            <div className="flex items-center justify-between gap-3">
              <span className="font-medium">{w.technology ?? "Unknown"}</span>
              <div className="w-40 sm:w-56">
                <ScoreBar value={w.whitespace_score} />
              </div>
            </div>
            {w.rationale && (
              <p className="mt-2 text-sm text-neutral-400">{w.rationale}</p>
            )}
            <div className="mt-3 grid grid-cols-3 gap-3 text-center">
              <Metric label="Research" value={w.research_activity} />
              <Metric label="Funding" value={w.funding_present} />
              <Metric label="Startups" value={w.startup_density} />
            </div>
          </li>
        ))}
      </ul>
    </PanelState>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-white/5 px-2 py-2">
      <div className="text-sm font-semibold tabular-nums">
        {Math.round(value * 100)}
      </div>
      <div className="text-[11px] uppercase tracking-wide text-neutral-500">
        {label}
      </div>
    </div>
  );
}

export function BottlenecksPanel() {
  const q = useQuery({
    queryKey: ["bottlenecks"],
    queryFn: () => api.bottlenecks(),
  });
  return (
    <PanelState
      loading={q.isLoading}
      error={q.isError}
      empty={(q.data ?? []).length === 0}
      emptyMessage="No bottlenecks detected yet."
    >
      <ul className="space-y-2">
        {(q.data ?? []).map((b) => (
          <li key={b.id} className="card flex items-start gap-3 p-4">
            <div className="min-w-0 flex-1">
              <p className="text-sm text-neutral-200">{b.problem_statement}</p>
              {b.technology && (
                <span className="mt-2 inline-block">
                  <Badge>{b.technology}</Badge>
                </span>
              )}
            </div>
            <div className="shrink-0 text-right">
              <div className="text-xs text-neutral-500">Severity</div>
              <div className="text-lg font-semibold tabular-nums text-amber-400">
                {Math.round(b.severity * 100)}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </PanelState>
  );
}

export function ReportPanel() {
  const q = useQuery({
    queryKey: ["report"],
    queryFn: () => api.latestReport(),
  });

  if (q.isLoading) return <Spinner />;
  if (q.isError)
    return <ErrorState message="Couldn't load the weekly report." />;
  if (!q.data) return <EmptyState message="No report generated yet." />;

  const { payload, week_start } = q.data;
  return (
    <div className="space-y-4">
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <h3 className="font-medium">Weekly briefing</h3>
          <Badge>Week of {week_start}</Badge>
        </div>
        {payload.summary && (
          <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-neutral-300">
            {payload.summary}
          </p>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <ReportList
          title="Top technologies"
          items={(payload.top_technologies ?? []).map((t) => t.name)}
        />
        <ReportList
          title="Top opportunities"
          items={(payload.top_opportunities ?? []).map((o) => o.title)}
        />
      </div>
    </div>
  );
}

export function HealthPanel() {
  const q = useQuery({ queryKey: ["health-status"], queryFn: () => api.healthStatus() });

  if (q.isLoading) return <Spinner />;
  if (q.isError) return <ErrorState message="Couldn't load system health." />;
  if (!q.data) return <EmptyState message="No health status available." />;

  const { overall_status, storage, components, recent_activity, source_recommendations } = q.data;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-4">
        <StatCard label="Overall" value={overall_status} tone={overall_status === "ok" ? "emerald" : "amber"} />
        <StatCard label="DB size" value={`${storage.db_size_gb.toFixed(2)} GB`} />
        <StatCard label="Budget" value={storage.within_budget ? "within" : "exceeded"} tone={storage.within_budget ? "emerald" : "red"} />
        <StatCard label="Sources" value={`${source_recommendations.length} recs`} />
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">Pipeline status</h3>
          <div className="space-y-2">
            {components.map((c) => (
              <div key={c.component} className="flex items-center justify-between rounded-xl bg-white/5 px-3 py-2">
                <div>
                  <div className="font-medium capitalize text-neutral-100">{c.component.replace(/_/g, " ")}</div>
                  <div className="text-xs text-neutral-500">ok {c.ok_count} · errors {c.error_count}</div>
                </div>
                <Badge>{c.status}</Badge>
              </div>
            ))}
          </div>
        </div>

        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">Source discovery</h3>
          {source_recommendations.length === 0 ? (
            <EmptyState message="No new source recommendations right now." />
          ) : (
            <ul className="space-y-2">
              {source_recommendations.map((s) => (
                <li key={s.name} className="rounded-xl bg-white/5 px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-neutral-100">{s.name}</span>
                    <Badge>{Math.round(s.score * 100)}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-neutral-400">{s.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">Recent activity</h3>
        <div className="space-y-2">
          {recent_activity.events.slice(0, 10).map((e) => (
            <div key={`${e.component}-${e.created_at}`} className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white/5 px-3 py-2 text-sm">
              <div className="min-w-0">
                <span className="font-medium text-neutral-100">{e.component}</span>
                <span className="text-neutral-500"> · {e.phase}</span>
                {e.message && <span className="text-neutral-500"> · {e.message}</span>}
              </div>
              <Badge>{e.status}</Badge>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function InvestorPanel() {
  const q = useQuery({ queryKey: ["investor-map"], queryFn: () => api.investorMap() });
  if (q.isLoading) return <Spinner />;
  if (q.isError) return <ErrorState message="Couldn't load investor map." />;
  if (!q.data) return <EmptyState message="No investor map yet." />;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 lg:grid-cols-2">
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">Majority sectors</h3>
          <div className="space-y-2">
            {q.data.majority_sectors.map((s) => (
              <div key={s.sector} className="rounded-xl bg-white/5 px-3 py-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium text-neutral-100">{s.sector}</span>
                  <Badge>{Math.round(s.capital_attractiveness * 100)}</Badge>
                </div>
                <p className="mt-2 text-sm text-neutral-400">{s.wealth_thesis}</p>
                <div className="mt-3 grid grid-cols-4 gap-2 text-xs text-neutral-500">
                  <span>Papers {s.papers}</span>
                  <span>Patents {s.patents}</span>
                  <span>Grants {s.grants}</span>
                  <span>Orgs {s.company_presence}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">Hotspots</h3>
          <div className="space-y-2">
            {q.data.major_market_hotspots.slice(0, 6).map((h) => (
              <div key={`${h.region}-${h.sector}`} className="rounded-xl bg-white/5 px-3 py-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium text-neutral-100">{h.region}</span>
                  <Badge>{h.sector}</Badge>
                </div>
                <p className="mt-2 text-sm text-neutral-400">{h.wealth_thesis}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, tone }: { label: string; value: string; tone?: "emerald" | "amber" | "red" }) {
  const toneClass =
    tone === "emerald"
      ? "text-emerald-300"
      : tone === "amber"
        ? "text-amber-300"
        : tone === "red"
          ? "text-red-300"
          : "text-neutral-100";
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wide text-neutral-500">{label}</div>
      <div className={`mt-2 text-xl font-semibold ${toneClass}`}>{value}</div>
    </div>
  );
}

function ReportList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="card p-4">
      <h4 className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">
        {title}
      </h4>
      {items.length === 0 ? (
        <p className="text-sm text-neutral-600">Nothing yet.</p>
      ) : (
        <ol className="space-y-1.5">
          {items.map((it, i) => (
            <li key={i} className="flex gap-2 text-sm text-neutral-300">
              <span className="text-neutral-600">{i + 1}.</span>
              <span className="truncate">{it}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
