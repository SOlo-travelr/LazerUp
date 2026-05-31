"use client";

import { useCallback, useMemo, useState } from "react";
import { AskHero } from "@/components/AskHero";
import { CLASSIC_TABS, type ClassicTabId, ClassicDashboard } from "@/components/ClassicDashboard";
import { CommandPalette, type CommandAction, useGlobalShortcut } from "@/components/CommandPalette";
import { IntelligenceWorkspace } from "@/components/IntelligenceWorkspace";

const MODES = [
  { id: "workspace", label: "Intelligence workspace", hint: "Analyst-grade signal operations" },
  { id: "classic", label: "Classic dashboard", hint: "Original panel view" },
] as const;

type ModeId = (typeof MODES)[number]["id"];

export default function HomePage() {
  const [mode, setMode] = useState<ModeId>("workspace");
  const [classicTab, setClassicTab] = useState<ClassicTabId>("health");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [pendingChord, setPendingChord] = useState<string | null>(null);
  const active = MODES.find((t) => t.id === mode)!;

  const focusAskInput = useCallback(() => {
    const input = document.querySelector<HTMLInputElement>("[data-command-target='ask-input']");
    if (!input) return;
    input.focus();
    input.select();
  }, []);

  const goClassic = useCallback((tab: ClassicTabId) => {
    setMode("classic");
    setClassicTab(tab);
  }, []);

  const actions = useMemo<CommandAction[]>(
    () => [
      {
        id: "mode-workspace",
        title: "Switch to Intelligence workspace",
        description: "Open the analyst-grade signal workspace",
        shortcut: "g+w",
        keywords: ["mode", "workspace", "analyst"],
        run: () => setMode("workspace"),
      },
      {
        id: "mode-classic",
        title: "Switch to Classic dashboard",
        description: "Open the original panel dashboard",
        shortcut: "g+c",
        keywords: ["mode", "classic", "tabs"],
        run: () => setMode("classic"),
      },
      {
        id: "focus-ask",
        title: "Focus Ask box",
        description: "Jump to the main question input",
        shortcut: "/",
        keywords: ["search", "ask", "question"],
        run: focusAskInput,
      },
      {
        id: "open-api-docs",
        title: "Open API documentation",
        description: "Open FastAPI docs in a new tab",
        shortcut: "g+a",
        keywords: ["api", "docs", "swagger"],
        run: () => window.open("http://localhost:8000/docs", "_blank", "noreferrer"),
      },
      ...CLASSIC_TABS.map((tab) => ({
        id: `classic-${tab.id}`,
        title: `Go to ${tab.label}`,
        description: tab.hint,
        shortcut:
          tab.id === "health"
            ? "g+h"
            : tab.id === "opportunities"
              ? "g+o"
              : tab.id === "trends"
                ? "g+t"
                : tab.id === "report"
                  ? "g+r"
                  : undefined,
        keywords: ["classic", "tab", tab.id, tab.label.toLowerCase()],
        run: () => goClassic(tab.id),
      })),
    ],
    [focusAskInput, goClassic],
  );

  useGlobalShortcut(
    useCallback(
      (event: KeyboardEvent) => {
        if (event.key === "/") {
          event.preventDefault();
          focusAskInput();
          return;
        }

        if (pendingChord === "g") {
          const key = event.key.toLowerCase();
          setPendingChord(null);
          if (key === "w") {
            event.preventDefault();
            setMode("workspace");
          } else if (key === "c") {
            event.preventDefault();
            setMode("classic");
          } else if (key === "h") {
            event.preventDefault();
            goClassic("health");
          } else if (key === "o") {
            event.preventDefault();
            goClassic("opportunities");
          } else if (key === "t") {
            event.preventDefault();
            goClassic("trends");
          } else if (key === "r") {
            event.preventDefault();
            goClassic("report");
          } else if (key === "a") {
            event.preventDefault();
            window.open("http://localhost:8000/docs", "_blank", "noreferrer");
          }
          return;
        }

        if (event.key.toLowerCase() === "g") {
          setPendingChord("g");
          window.setTimeout(() => setPendingChord((prev) => (prev === "g" ? null : prev)), 900);
        }
      },
      [focusAskInput, goClassic, pendingChord],
    ),
  );

  return (
    <div className="space-y-8">
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} actions={actions} />

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
          <div className="flex items-center gap-3">
            <span className="text-sm text-neutral-500">{active.hint}</span>
            <button
              onClick={() => setPaletteOpen(true)}
              className="rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-neutral-300 hover:border-white/20"
            >
              Command palette
            </button>
          </div>
        </div>

        <div>{mode === "workspace" ? <IntelligenceWorkspace /> : <ClassicDashboard tab={classicTab} onTabChange={setClassicTab} />}</div>

        <div className="flex flex-wrap gap-2 text-xs text-neutral-500">
          <span className="rounded border border-white/10 px-2 py-1">Ctrl/Cmd+K palette</span>
          <span className="rounded border border-white/10 px-2 py-1">g+w workspace</span>
          <span className="rounded border border-white/10 px-2 py-1">g+c classic</span>
          <span className="rounded border border-white/10 px-2 py-1">g+h health</span>
          <span className="rounded border border-white/10 px-2 py-1">g+o opportunities</span>
          <span className="rounded border border-white/10 px-2 py-1">/ focus ask</span>
        </div>
      </section>
    </div>
  );
}
