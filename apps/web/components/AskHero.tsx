"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, type AskResponse } from "@/lib/api";

const SUGGESTIONS = [
  "What's the most promising solid-state battery startup angle?",
  "Where is funding outpacing research in battery tech?",
  "What recurring problems show up in lithium-metal anodes?",
];

export function AskHero() {
  const [question, setQuestion] = useState("");

  const ask = useMutation<AskResponse, Error, string>({
    mutationFn: (q) => api.ask(q),
  });

  function submit(q: string) {
    const text = q.trim();
    if (!text) return;
    setQuestion(text);
    ask.mutate(text);
  }

  return (
    <section className="card overflow-hidden">
      <div className="border-b border-white/5 bg-gradient-to-br from-emerald-500/10 via-transparent to-transparent px-6 py-6">
        <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">
          Ask anything about the battery landscape
        </h1>
        <p className="mt-1 text-sm text-neutral-400">
          Get grounded answers backed by papers, patents, grants, and funding
          activity.
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit(question);
          }}
          className="mt-4 flex gap-2"
        >
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. Which technologies have research but little startup activity?"
            className="w-full rounded-xl border border-white/10 bg-neutral-950/60 px-4 py-3 text-sm text-neutral-100 outline-none transition placeholder:text-neutral-600 focus:border-emerald-500/50"
          />
          <button
            type="submit"
            disabled={ask.isPending || !question.trim()}
            className="shrink-0 rounded-xl bg-emerald-500 px-4 py-3 text-sm font-medium text-neutral-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {ask.isPending ? "Thinking…" : "Ask"}
          </button>
        </form>

        {!ask.data && !ask.isPending && (
          <div className="mt-3 flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => submit(s)}
                className="rounded-full border border-white/10 px-3 py-1 text-xs text-neutral-400 transition hover:border-white/20 hover:text-neutral-200"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {(ask.isPending || ask.data || ask.isError) && (
        <div className="px-6 py-5">
          {ask.isPending && (
            <p className="animate-pulse text-sm text-neutral-500">
              Searching the corpus and composing an answer…
            </p>
          )}
          {ask.isError && (
            <p className="text-sm text-red-300">
              Couldn&apos;t reach the API. Make sure the backend is running.
            </p>
          )}
          {ask.data && (
            <div className="space-y-4">
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-neutral-200">
                {ask.data.answer}
              </p>
              {ask.data.citations.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">
                    Sources
                  </p>
                  <ul className="space-y-1.5">
                    {ask.data.citations.map((c, i) => (
                      <li key={c.id} className="text-sm">
                        <span className="mr-2 text-neutral-600">[{i + 1}]</span>
                        {c.url ? (
                          <a
                            href={c.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-emerald-400 hover:underline"
                          >
                            {c.title}
                          </a>
                        ) : (
                          <span className="text-neutral-300">{c.title}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {!ask.data.grounded && (
                <p className="text-xs text-amber-400/80">
                  Limited evidence found — treat this answer as a starting point.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
