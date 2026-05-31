"use client";

import { useState } from "react";
import { AskHero } from "@/components/AskHero";
import { ClassicDashboard } from "@/components/ClassicDashboard";
import { IntelligenceWorkspace } from "@/components/IntelligenceWorkspace";

const MODES = [
  { id: "workspace", label: "Intelligence workspace", hint: "Analyst-grade signal operations" },
  { id: "classic", label: "Classic dashboard", hint: "Original panel view" },
] as const;

type ModeId = (typeof MODES)[number]["id"];

export default function HomePage() {
  const [mode, setMode] = useState<ModeId>("workspace");
  const active = MODES.find((t) => t.id === mode)!;

  return (
    <div className="space-y-8">
      <AskHero />

      <section className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {MODES.map((t) => (
            <button
              key={t.id}
              onClick={() => setMode(t.id)}
              className={`rounded-xl px-3.5 py-2 text-sm font-medium transition ${
                mode === t.id
                  ? "bg-emerald-500/20 text-emerald-100"
                  : "text-neutral-400 hover:bg-white/5 hover:text-neutral-200"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold tracking-tight">{active.label}</h2>
          <span className="text-sm text-neutral-500">{active.hint}</span>
        </div>

        <div>{mode === "workspace" ? <IntelligenceWorkspace /> : <ClassicDashboard />}</div>
      </section>
    </div>
  );
}
