"use client";

import { useEffect, useMemo, useState } from "react";

export type CommandAction = {
  id: string;
  title: string;
  description?: string;
  keywords?: string[];
  shortcut?: string;
  run: () => void;
};

function shortcutLabel(input: string): string {
  const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);
  if (!isMac) return input;
  return input
    .replace(/Ctrl/gi, "⌃")
    .replace(/Cmd/gi, "⌘")
    .replace(/Shift/gi, "⇧")
    .replace(/Alt/gi, "⌥");
}

function keyElement(key: string) {
  return (
    <kbd className="rounded border border-white/15 bg-white/5 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-neutral-300">
      {key}
    </kbd>
  );
}

function isTextInputTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select") return true;
  if (target.isContentEditable) return true;
  return false;
}

export function CommandPalette({
  open,
  onOpenChange,
  actions,
}: {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  actions: CommandAction[];
}) {
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setCursor(0);
    }
  }, [open]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const mod = event.metaKey || event.ctrlKey;
      if (mod && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onOpenChange(!open);
        return;
      }
      if (!open) return;

      if (event.key === "Escape") {
        event.preventDefault();
        onOpenChange(false);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onOpenChange]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return actions;
    return actions.filter((action) => {
      const text = [action.title, action.description || "", ...(action.keywords || [])]
        .join(" ")
        .toLowerCase();
      return text.includes(q);
    });
  }, [actions, query]);

  useEffect(() => {
    setCursor((prev) => Math.min(prev, Math.max(0, filtered.length - 1)));
  }, [filtered.length]);

  useEffect(() => {
    if (!open) return;

    function onPaletteNav(event: KeyboardEvent) {
      if (!open) return;
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setCursor((prev) => Math.min(prev + 1, Math.max(0, filtered.length - 1)));
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setCursor((prev) => Math.max(prev - 1, 0));
      } else if (event.key === "Enter") {
        event.preventDefault();
        const action = filtered[cursor];
        if (action) {
          action.run();
          onOpenChange(false);
        }
      }
    }

    window.addEventListener("keydown", onPaletteNav);
    return () => window.removeEventListener("keydown", onPaletteNav);
  }, [cursor, filtered, onOpenChange, open]);

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          onClick={() => onOpenChange(false)}
        >
          <div className="mx-auto mt-[12vh] w-full max-w-2xl px-4" onClick={(e) => e.stopPropagation()}>
            <div className="overflow-hidden rounded-2xl border border-white/10 bg-neutral-900/95 shadow-2xl shadow-black/50">
              <div className="border-b border-white/10 px-4 py-3">
                <input
                  autoFocus
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Type a command or search views..."
                  className="w-full bg-transparent text-sm text-neutral-100 outline-none placeholder:text-neutral-500"
                />
              </div>

              <div className="max-h-[52vh] overflow-auto p-2">
                {filtered.length === 0 ? (
                  <div className="rounded-lg px-3 py-5 text-center text-sm text-neutral-500">
                    No matching commands.
                  </div>
                ) : (
                  filtered.map((action, index) => (
                    <button
                      key={action.id}
                      onClick={() => {
                        action.run();
                        onOpenChange(false);
                      }}
                      className={`mb-1 flex w-full items-center justify-between rounded-xl px-3 py-2 text-left ${
                        index === cursor
                          ? "bg-emerald-500/15 text-emerald-100"
                          : "text-neutral-200 hover:bg-white/5"
                      }`}
                    >
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{action.title}</div>
                        {action.description && (
                          <div className="truncate text-xs text-neutral-400">{action.description}</div>
                        )}
                      </div>
                      {action.shortcut && (
                        <div className="ml-3 shrink-0 text-[10px] text-neutral-400">
                          {shortcutLabel(action.shortcut)
                            .split("+")
                            .map((key) => key.trim())
                            .filter(Boolean)
                            .map((key) => (
                              <span key={`${action.id}-${key}`} className="mr-1 inline-block">
                                {keyElement(key)}
                              </span>
                            ))}
                        </div>
                      )}
                    </button>
                  ))
                )}
              </div>

              <div className="flex items-center justify-between border-t border-white/10 px-4 py-2 text-[11px] text-neutral-500">
                <div className="flex items-center gap-2">
                  {keyElement("↑")}
                  {keyElement("↓")}
                  <span>Move</span>
                </div>
                <div className="flex items-center gap-2">
                  {keyElement("Enter")}
                  <span>Run</span>
                </div>
                <div className="flex items-center gap-2">
                  {keyElement("Esc")}
                  <span>Close</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function useGlobalShortcut(handler: (event: KeyboardEvent) => void) {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (isTextInputTarget(event.target)) return;
      handler(event);
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handler]);
}
