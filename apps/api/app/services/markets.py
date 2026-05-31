"""Global market headline and signal analysis by region."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas import (
    HeadlineItem,
    MarketCapitalMapOut,
    MarketHeadlinesOut,
    MarketRegionOut,
    RegionalCapitalItem,
    SectorCapitalItem,
)

_MAJOR_REGIONS: dict[str, tuple[str, ...]] = {
    "China": ("china", "chinese", "beijing", "shenzhen", "guangdong", "catl", "byd"),
    "South Korea": ("korea", "south korea", "korean", "seoul", "samsung sdi", "lg energy solution", "sk on"),
    "Japan": ("japan", "japanese", "tokyo", "panasonic", "toyota", "hitachi"),
    "Europe": (
        "europe",
        "eu",
        "european",
        "germany",
        "france",
        "uk",
        "sweden",
        "norway",
        "finland",
        "northvolt",
    ),
}

_MINOR_REGIONS: dict[str, tuple[str, ...]] = {
    "India": ("india", "indian", "new delhi", "mumbai"),
    "Southeast Asia": ("southeast asia", "asean", "indonesia", "vietnam", "thailand", "malaysia"),
    "Middle East": ("middle east", "saudi", "uae", "qatar", "oman", "israel"),
    "Latin America": ("latin america", "brazil", "chile", "argentina", "mexico", "peru"),
    "Africa": ("africa", "south africa", "morocco", "namibia", "zambia", "congo"),
    "Australia": ("australia", "australian", "queensland", "western australia"),
    "Canada": ("canada", "canadian", "ontario", "quebec"),
}

_SELECT_DOCS = text(
    """
    SELECT d.id, d.doc_type, d.title, d.abstract, d.url, d.published_at
    FROM document d
    WHERE d.published_at >= :start_date
    ORDER BY d.published_at DESC NULLS LAST, d.created_at DESC
    """
)

_SELECT_DOC_TECH = text(
    """
    SELECT dt.document_id, t.name
    FROM document_technology dt
    JOIN technology t ON t.id = dt.technology_id
    """
)

_SECTOR_METRICS = text(
        """
        WITH trend_latest AS (
            SELECT DISTINCT ON (technology_id) technology_id, composite_score
            FROM trend_score
            ORDER BY technology_id, window_end DESC
        ),
        sector_docs AS (
            SELECT
                t.category AS sector,
                d.id,
                d.doc_type,
                coalesce(tl.composite_score, 0) AS trend_score
            FROM document_technology dt
            JOIN technology t ON t.id = dt.technology_id
            JOIN document d ON d.id = dt.document_id
            LEFT JOIN trend_latest tl ON tl.technology_id = t.id
            WHERE d.published_at >= :start_date
        ),
        sector_orgs AS (
            SELECT
                t.category AS sector,
                COUNT(DISTINCT dorg.organization_id)::int AS company_presence
            FROM document_technology dt
            JOIN technology t ON t.id = dt.technology_id
            JOIN document d ON d.id = dt.document_id
            JOIN document_organization dorg ON dorg.document_id = d.id
            JOIN organization o ON o.id = dorg.organization_id
            WHERE d.published_at >= :start_date
                AND dorg.role IN ('assignee', 'awardee', 'company')
                AND coalesce(o.org_type, '') <> 'academic'
            GROUP BY t.category
        ),
        sector_funding AS (
            SELECT
                t.category AS sector,
                SUM(coalesce(ga.amount_usd, 0) + coalesce(fe.amount_usd, 0))::float AS funding_usd
            FROM document_technology dt
            JOIN technology t ON t.id = dt.technology_id
            JOIN document d ON d.id = dt.document_id
            LEFT JOIN grant_award ga ON ga.document_id = d.id
            LEFT JOIN funding_event fe ON fe.document_id = d.id
            WHERE d.published_at >= :start_date
            GROUP BY t.category
        )
        SELECT
            sd.sector,
            COUNT(DISTINCT sd.id)::int AS documents,
            COUNT(*) FILTER (WHERE sd.doc_type = 'paper')::int AS papers,
            COUNT(*) FILTER (WHERE sd.doc_type = 'patent')::int AS patents,
            COUNT(*) FILTER (WHERE sd.doc_type = 'grant')::int AS grants,
            coalesce(so.company_presence, 0)::int AS company_presence,
            coalesce(sf.funding_usd, 0)::float AS funding_usd,
            AVG(sd.trend_score)::float AS avg_trend_score
        FROM sector_docs sd
        LEFT JOIN sector_orgs so ON so.sector = sd.sector
        LEFT JOIN sector_funding sf ON sf.sector = sd.sector
        GROUP BY sd.sector, so.company_presence, sf.funding_usd
        ORDER BY documents DESC
        """
)


def _regions_for(text_blob: str) -> set[str]:
    text_lower = text_blob.lower()
    matched: set[str] = set()
    for region, keys in _MAJOR_REGIONS.items():
        if any(k in text_lower for k in keys):
            matched.add(region)
    for region, keys in _MINOR_REGIONS.items():
        if any(k in text_lower for k in keys):
            matched.add(region)
    if not matched:
        matched.add("Global")
    return matched


def _tier(region: str) -> str:
    if region in _MAJOR_REGIONS:
        return "major"
    if region in _MINOR_REGIONS:
        return "minor"
    return "global"


def get_market_headlines(db: Session, days: int = 90, per_region: int = 6) -> MarketHeadlinesOut:
    start_date = date.today() - timedelta(days=max(days, 1))
    docs = db.execute(_SELECT_DOCS, {"start_date": start_date}).mappings().all()
    doc_tech_rows = db.execute(_SELECT_DOC_TECH).mappings().all()

    tech_map: dict[str, list[str]] = {}
    for row in doc_tech_rows:
        did = str(row["document_id"])
        tech_map.setdefault(did, []).append(row["name"])

    regions: dict[str, dict] = {}
    for row in docs:
        text_blob = f"{row['title'] or ''} {row['abstract'] or ''}"
        doc_regions = _regions_for(text_blob)
        did = str(row["id"])
        techs = tech_map.get(did, [])
        for region in doc_regions:
            bucket = regions.setdefault(
                region,
                {
                    "counts": {},
                    "tech_counts": {},
                    "headlines": [],
                    "tier": _tier(region),
                },
            )
            doc_type = (row["doc_type"] or "unknown").strip()
            bucket["counts"][doc_type] = bucket["counts"].get(doc_type, 0) + 1
            for tech in techs:
                bucket["tech_counts"][tech] = bucket["tech_counts"].get(tech, 0) + 1
            if doc_type == "news" and len(bucket["headlines"]) < per_region:
                bucket["headlines"].append(
                    HeadlineItem(
                        title=row["title"],
                        url=row["url"],
                        published_at=row["published_at"],
                        doc_type=doc_type,
                        technologies=techs[:5],
                    )
                )

    major: list[MarketRegionOut] = []
    minor: list[MarketRegionOut] = []
    for region, payload in regions.items():
        top_tech = sorted(
            payload["tech_counts"].items(), key=lambda x: x[1], reverse=True
        )[:5]
        item = MarketRegionOut(
            region=region,
            market_tier=payload["tier"],
            counts_by_doc_type=payload["counts"],
            top_technologies=[name for name, _ in top_tech],
            headlines=payload["headlines"],
        )
        if payload["tier"] == "major":
            major.append(item)
        elif payload["tier"] == "minor":
            minor.append(item)

    major.sort(key=lambda x: sum(x.counts_by_doc_type.values()), reverse=True)
    minor.sort(key=lambda x: sum(x.counts_by_doc_type.values()), reverse=True)

    return MarketHeadlinesOut(major_markets=major, minor_markets=minor)


def _norm(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return value / max_value


def _wealth_thesis(sector: str, patents: int, grants: int, companies: int, trend: float) -> str:
    if patents >= grants and companies > 0:
        return f"{sector} shows commercialization pull with patent and company density."
    if grants > patents:
        return f"{sector} is grant-backed and suitable for early-positioning capital."
    if trend >= 0.55:
        return f"{sector} has strong momentum and can compound if scaled quickly."
    return f"{sector} is building signal; selective capital with partnerships is best."


def get_market_capital_map(
    db: Session,
    days: int = 180,
    sectors: int = 10,
    hotspots: int = 12,
) -> MarketCapitalMapOut:
    start_date = date.today() - timedelta(days=max(days, 1))
    rows = db.execute(_SECTOR_METRICS, {"start_date": start_date}).mappings().all()

    if not rows:
        return MarketCapitalMapOut(
            majority_sectors=[],
            major_market_hotspots=[],
            minor_market_hotspots=[],
        )

    max_docs = max(float(r["documents"] or 0) for r in rows)
    max_patents = max(float(r["patents"] or 0) for r in rows)
    max_grants = max(float(r["grants"] or 0) for r in rows)
    max_companies = max(float(r["company_presence"] or 0) for r in rows)
    max_funding = max(float(r["funding_usd"] or 0) for r in rows)
    max_trend = max(float(r["avg_trend_score"] or 0) for r in rows)

    sector_items: list[SectorCapitalItem] = []
    for r in rows:
        docs_v = float(r["documents"] or 0)
        patents_v = float(r["patents"] or 0)
        grants_v = float(r["grants"] or 0)
        companies_v = float(r["company_presence"] or 0)
        funding_v = float(r["funding_usd"] or 0)
        trend_v = float(r["avg_trend_score"] or 0)
        score = (
            0.23 * _norm(docs_v, max_docs)
            + 0.20 * _norm(patents_v, max_patents)
            + 0.14 * _norm(grants_v, max_grants)
            + 0.20 * _norm(companies_v, max_companies)
            + 0.13 * _norm(funding_v, max_funding)
            + 0.10 * _norm(trend_v, max_trend)
        )
        sector = r["sector"]
        sector_items.append(
            SectorCapitalItem(
                sector=sector,
                documents=int(docs_v),
                papers=int(r["papers"] or 0),
                patents=int(patents_v),
                grants=int(grants_v),
                company_presence=int(companies_v),
                funding_usd=round(funding_v, 2),
                avg_trend_score=round(trend_v, 6),
                capital_attractiveness=round(score, 6),
                wealth_thesis=_wealth_thesis(
                    sector,
                    patents=int(patents_v),
                    grants=int(grants_v),
                    companies=int(companies_v),
                    trend=trend_v,
                ),
            )
        )

    sector_items.sort(key=lambda x: x.capital_attractiveness, reverse=True)
    majority = sector_items[:sectors]

    by_region = get_market_headlines(db, days=days, per_region=3)
    sector_lookup = {s.sector: s for s in sector_items}

    def _region_hotspots(regions: list[MarketRegionOut]) -> list[RegionalCapitalItem]:
        out: list[RegionalCapitalItem] = []
        for region in regions:
            for sector_name in region.top_technologies[:3]:
                sector_key = None
                for s in sector_lookup:
                    if s.lower() in sector_name.lower() or sector_name.lower() in s.lower():
                        sector_key = s
                        break
                if sector_key is None:
                    continue
                sec = sector_lookup[sector_key]
                signal_count = sum(region.counts_by_doc_type.values())
                reg_score = (
                    0.55 * sec.capital_attractiveness
                    + 0.30 * min(signal_count / 50.0, 1.0)
                    + 0.15 * min(sec.company_presence / 15.0, 1.0)
                )
                out.append(
                    RegionalCapitalItem(
                        region=region.region,
                        market_tier=region.market_tier,
                        sector=sec.sector,
                        document_signals=signal_count,
                        company_presence=sec.company_presence,
                        funding_usd=sec.funding_usd,
                        capital_attractiveness=round(reg_score, 6),
                        wealth_thesis=f"{region.region}: {sec.wealth_thesis}",
                    )
                )
        out.sort(key=lambda x: x.capital_attractiveness, reverse=True)
        return out[:hotspots]

    return MarketCapitalMapOut(
        majority_sectors=majority,
        major_market_hotspots=_region_hotspots(by_region.major_markets),
        minor_market_hotspots=_region_hotspots(by_region.minor_markets),
    )
