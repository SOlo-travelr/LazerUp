import { api, type TrendItem } from "@/lib/api";

async function fetchTrends(): Promise<TrendItem[]> {
  try {
    return await api.trends();
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const trends = await fetchTrends();

  return (
    <main className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">
          Battery Opportunity Scanner
        </h1>
        <p className="text-neutral-400">
          Emerging battery startup opportunities, technology white spaces, and
          funding trends — before they become obvious.
        </p>
      </header>

      <section>
        <h2 className="mb-4 text-xl font-medium">Trending technologies</h2>
        {trends.length === 0 ? (
          <p className="rounded-lg border border-neutral-800 bg-neutral-900 p-4 text-neutral-400">
            No trend data yet. Run <code className="text-neutral-200">make migrate</code>,
            <code className="text-neutral-200"> make seed</code>, then start the API.
          </p>
        ) : (
          <ul className="divide-y divide-neutral-800 rounded-lg border border-neutral-800 bg-neutral-900">
            {trends.map((t) => (
              <li
                key={t.technology.id}
                className="flex items-center justify-between px-4 py-3"
              >
                <div>
                  <span className="mr-3 text-neutral-500">#{t.rank}</span>
                  <span className="font-medium">{t.technology.name}</span>
                  <span className="ml-2 text-sm text-neutral-500">
                    {t.technology.category}
                  </span>
                </div>
                <span className="tabular-nums text-neutral-300">
                  {t.composite_score.toFixed(2)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
