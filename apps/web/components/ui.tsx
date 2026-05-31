"use client";

import type { ReactNode } from "react";

export function ScoreBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/5">
        <div
          className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-9 shrink-0 text-right text-xs tabular-nums text-neutral-400">
        {pct}
      </span>
    </div>
  );
}

export function Badge({ children }: { children: ReactNode }) {
  return (
    <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] font-medium text-neutral-300">
      {children}
    </span>
  );
}

export function Rank({ n }: { n: number }) {
  return (
    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-white/5 text-xs font-semibold tabular-nums text-neutral-400">
      {n}
    </span>
  );
}

export function Spinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/15 border-t-emerald-400" />
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-dashed border-white/10 px-4 py-10 text-center text-sm text-neutral-500">
      {message}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-6 text-center text-sm text-red-300">
      {message}
    </div>
  );
}
