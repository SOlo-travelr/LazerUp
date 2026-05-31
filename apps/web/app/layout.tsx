import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Battery Opportunity Scanner",
  description: "Emerging battery startup opportunities, before they're obvious.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="flex min-h-screen flex-col">
            <header className="sticky top-0 z-20 border-b border-white/5 bg-neutral-950/70 backdrop-blur">
              <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
                    <svg
                      viewBox="0 0 24 24"
                      className="h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" />
                    </svg>
                  </span>
                  <div className="leading-tight">
                    <p className="text-sm font-semibold tracking-tight">
                      Battery Opportunity Scanner
                    </p>
                    <p className="text-xs text-neutral-500">
                      Spot the next battery startup early
                    </p>
                  </div>
                </div>
                <a
                  href="http://localhost:8000/docs"
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-neutral-300 transition hover:border-white/20 hover:text-white"
                >
                  API
                </a>
              </div>
            </header>

            <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
              {children}
            </main>

            <footer className="border-t border-white/5">
              <div className="mx-auto max-w-6xl px-6 py-6 text-xs text-neutral-600">
                Battery Opportunity Scanner — data refreshes automatically.
              </div>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}
