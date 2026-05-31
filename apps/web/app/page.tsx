"use client";

import { useState } from "react";
import { AskHero } from "@/components/AskHero";
import {
  BottlenecksPanel,
  GeoIndustryPanel,
  HealthPanel,
  InvestorPanel,
  OpportunitiesPanel,
  ReportPanel,
  TrendsPanel,
  WhiteSpacePanel,
} from "@/components/Panels";

const TABS = [
  { id: "health", label: "Health", hint: "Live activity and status" },
  { id: "investors", label: "Investor map", hint: "Capital and wealth" },
  { id: "geo", label: "Countries + industries", hint: "Risk and opportunity links" },
  { id: "trends", label: "Trends", hint: "What's heating up" },
  { id: "opportunities", label: "Opportunities", hint: "Startup angles" },
  { id: "whitespace", label: "White space", hint: "Underserved areas" },
  { id: "bottlenecks", label: "Bottlenecks", hint: "Recurring problems" },
  { id: "report", label: "Weekly report", hint: "The briefing" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function HomePage() {
  const [tab, setTab] = useState<TabId>("health");
  const active = TABS.find((t) => t.id === tab)!;

  return (
    <div className="space-y-8">
      <AskHero />

      <section className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`rounded-xl px-3.5 py-2 text-sm font-medium transition ${
                tab === t.id
                  ? "bg-white/10 text-white"
                  : "text-neutral-400 hover:bg-white/5 hover:text-neutral-200"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold tracking-tight">
            {active.label}
          </h2>
          <span className="text-sm text-neutral-500">{active.hint}</span>
        </div>

        <div>
          {tab === "health" && <HealthPanel />}
          {tab === "investors" && <InvestorPanel />}
          {tab === "geo" && <GeoIndustryPanel />}
          {tab === "trends" && <TrendsPanel />}
          {tab === "opportunities" && <OpportunitiesPanel />}
          {tab === "whitespace" && <WhiteSpacePanel />}
          {tab === "bottlenecks" && <BottlenecksPanel />}
          {tab === "report" && <ReportPanel />}
        </div>
      </section>
    </div>
  );
}
