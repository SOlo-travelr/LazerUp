"""Read services for entity-linkage and commercialization chain insights."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas import (
    CompanyInsightItem,
    LinkageChainSample,
    LinkageEntity,
    LinkageInsightsOut,
    PersonInsightItem,
    TechnologyGapItem,
    TechnologyLinkageOut,
    TechnologyLinkageSummary,
    TechnologyOut,
)

_TECH_BY_SLUG = text(
    """
    SELECT id, slug, name, category
    FROM technology
    WHERE slug = :slug
    """
)

_SUMMARY_COUNTS = text(
    """
    WITH base_docs AS (
        SELECT d.id, d.doc_type
        FROM document_technology dt
        JOIN document d ON d.id = dt.document_id
        WHERE dt.technology_id = :tech_id
    )
    SELECT
      COUNT(*) FILTER (WHERE doc_type = 'paper') AS papers,
      COUNT(*) FILTER (WHERE doc_type = 'patent') AS patents,
      COUNT(*) FILTER (WHERE doc_type = 'grant') AS grants,
      (SELECT COUNT(DISTINCT da.person_id)
       FROM document_author da
       JOIN base_docs bd ON bd.id = da.document_id
       JOIN document d2 ON d2.id = da.document_id
       WHERE d2.doc_type = 'paper') AS researchers,
      (SELECT COUNT(DISTINCT da.person_id)
       FROM document_author da
       JOIN base_docs bd ON bd.id = da.document_id
       JOIN document d2 ON d2.id = da.document_id
       WHERE d2.doc_type = 'patent') AS inventors,
      (SELECT COUNT(DISTINCT dorg.organization_id)
       FROM document_organization dorg
       JOIN base_docs bd ON bd.id = dorg.document_id
       JOIN document d2 ON d2.id = dorg.document_id
             JOIN organization o2 ON o2.id = dorg.organization_id
       WHERE d2.doc_type IN ('patent', 'grant', 'funding', 'news')
                 AND dorg.role IN ('assignee', 'awardee', 'company')
                 AND coalesce(o2.org_type, '') <> 'academic') AS companies
    FROM base_docs
    """
)

_TOP_INVENTORS = text(
    """
    SELECT p.id, p.full_name AS name, COUNT(*)::int AS count
    FROM document_author da
    JOIN person p ON p.id = da.person_id
    JOIN document d ON d.id = da.document_id
    JOIN document_technology dt ON dt.document_id = d.id
    WHERE dt.technology_id = :tech_id
      AND d.doc_type = 'patent'
    GROUP BY p.id, p.full_name
    ORDER BY count DESC, p.full_name
    LIMIT :limit
    """
)

_TOP_COMPANIES = text(
    """
    SELECT o.id, o.name, COUNT(*)::int AS count
    FROM document_organization dorg
    JOIN organization o ON o.id = dorg.organization_id
    JOIN document d ON d.id = dorg.document_id
    JOIN document_technology dt ON dt.document_id = d.id
    WHERE dt.technology_id = :tech_id
      AND d.doc_type IN ('patent', 'grant', 'funding', 'news')
      AND dorg.role IN ('assignee', 'awardee', 'company')
            AND coalesce(o.org_type, '') <> 'academic'
    GROUP BY o.id, o.name
    ORDER BY count DESC, o.name
    LIMIT :limit
    """
)

_TOP_LABS = text(
    """
    SELECT o.id, o.name, COUNT(*)::int AS count
    FROM document_organization dorg
    JOIN organization o ON o.id = dorg.organization_id
    JOIN document d ON d.id = dorg.document_id
    JOIN document_technology dt ON dt.document_id = d.id
    WHERE dt.technology_id = :tech_id
      AND d.doc_type IN ('paper', 'grant')
      AND (
           lower(o.name) LIKE '%university%'
        OR lower(o.name) LIKE '%institute%'
        OR lower(o.name) LIKE '%laboratory%'
        OR lower(o.name) LIKE '%college%'
      )
    GROUP BY o.id, o.name
    ORDER BY count DESC, o.name
    LIMIT :limit
    """
)

_CHAIN_SAMPLES = text(
    """
    SELECT DISTINCT
      dp.title AS paper_title,
      p.full_name AS inventor,
      dpat.title AS patent_title,
      o_assignee.name AS assignee,
      dgrant.title AS grant_title,
      o_company.name AS company
    FROM document dp
    JOIN document_author da_paper ON da_paper.document_id = dp.id
    JOIN person p ON p.id = da_paper.person_id
    JOIN document dpat ON dpat.doc_type = 'patent'
    JOIN document_author da_pat ON da_pat.document_id = dpat.id
        AND da_pat.person_id = p.id
    JOIN document_technology tp ON tp.document_id = dp.id
    JOIN document_technology tpat ON tpat.document_id = dpat.id
        AND tpat.technology_id = tp.technology_id
    LEFT JOIN patent pat ON pat.document_id = dpat.id
    LEFT JOIN organization o_assignee ON o_assignee.id = pat.assignee_org
    LEFT JOIN grant_award ga ON ga.awardee_org = pat.assignee_org
    LEFT JOIN document dgrant ON dgrant.id = ga.document_id
    LEFT JOIN organization o_company ON o_company.id = pat.assignee_org
    WHERE dp.doc_type = 'paper'
      AND tp.technology_id = :tech_id
    ORDER BY dp.title
    LIMIT :limit
    """
)

_INSIGHT_LAB_TO_COMMERCIAL = text(
    """
    WITH agg AS (
      SELECT
        t.slug,
        t.name,
        COUNT(*) FILTER (WHERE d.doc_type = 'paper')::int AS papers,
        COUNT(*) FILTER (WHERE d.doc_type = 'patent')::int AS patents,
        COUNT(*) FILTER (WHERE d.doc_type = 'grant')::int AS grants,
        COUNT(DISTINCT CASE
            WHEN d.doc_type IN ('patent', 'grant', 'funding', 'news')
             AND dorg.role IN ('assignee', 'awardee', 'company')
            THEN dorg.organization_id END
        )::int AS startups
      FROM technology t
      LEFT JOIN document_technology dt ON dt.technology_id = t.id
      LEFT JOIN document d ON d.id = dt.document_id
      LEFT JOIN document_organization dorg ON dorg.document_id = d.id
      GROUP BY t.slug, t.name
    )
    SELECT slug, name, papers, patents, grants, startups
    FROM agg
    WHERE papers > 0 AND patents > 0 AND startups > 0
    ORDER BY (patents + startups + grants) DESC, papers DESC
    LIMIT :limit
    """
)

_INSIGHT_PROFESSORS = text(
    """
    WITH person_rollup AS (
      SELECT
        p.full_name,
        p.affiliation,
        COUNT(*) FILTER (WHERE d.doc_type = 'paper')::int AS paper_docs,
        COUNT(*) FILTER (WHERE d.doc_type = 'patent')::int AS patent_docs
      FROM person p
      JOIN document_author da ON da.person_id = p.id
      JOIN document d ON d.id = da.document_id
      GROUP BY p.full_name, p.affiliation
    )
    SELECT full_name, affiliation, paper_docs, patent_docs
    FROM person_rollup
    WHERE paper_docs > 0 AND patent_docs > 0
    ORDER BY patent_docs DESC, paper_docs DESC, full_name
    LIMIT :limit
    """
)

_INSIGHT_QUIET_COMPANIES = text(
    """
    WITH org_rollup AS (
      SELECT
        o.name,
        COUNT(DISTINCT CASE WHEN d.doc_type = 'patent' THEN d.id END)::int AS patent_docs,
        COUNT(DISTINCT CASE WHEN d.doc_type <> 'patent' THEN d.id END)::int AS non_patent_mentions
      FROM organization o
      JOIN document_organization dorg ON dorg.organization_id = o.id
      JOIN document d ON d.id = dorg.document_id
      WHERE dorg.role IN ('assignee', 'awardee', 'company', 'publisher')
                AND coalesce(o.org_type, '') <> 'academic'
      GROUP BY o.name
    )
    SELECT name, patent_docs, non_patent_mentions
    FROM org_rollup
    WHERE patent_docs > 0 AND non_patent_mentions <= 1
    ORDER BY patent_docs DESC, name
    LIMIT :limit
    """
)

_INSIGHT_GRANT_FEW_STARTUPS = text(
    """
    WITH agg AS (
      SELECT
        t.slug,
        t.name,
        COUNT(*) FILTER (WHERE d.doc_type = 'paper')::int AS papers,
        COUNT(*) FILTER (WHERE d.doc_type = 'patent')::int AS patents,
        COUNT(*) FILTER (WHERE d.doc_type = 'grant')::int AS grants,
        COUNT(DISTINCT CASE
            WHEN coalesce(o.org_type, '') = 'startup' THEN o.id END
        )::int AS startups
      FROM technology t
      LEFT JOIN document_technology dt ON dt.technology_id = t.id
      LEFT JOIN document d ON d.id = dt.document_id
      LEFT JOIN document_organization dorg ON dorg.document_id = d.id
      LEFT JOIN organization o ON o.id = dorg.organization_id
      GROUP BY t.slug, t.name
    )
    SELECT slug, name, papers, patents, grants, startups
    FROM agg
    WHERE grants > 0 AND startups = 0
    ORDER BY grants DESC, papers DESC
    LIMIT :limit
    """
)

_INSIGHT_PATENT_LOW_ACADEMIC = text(
    """
    WITH agg AS (
      SELECT
        t.slug,
        t.name,
        COUNT(*) FILTER (WHERE d.doc_type = 'paper')::int AS papers,
        COUNT(*) FILTER (WHERE d.doc_type = 'patent')::int AS patents,
        COUNT(*) FILTER (WHERE d.doc_type = 'grant')::int AS grants,
        COUNT(DISTINCT CASE
            WHEN coalesce(o.org_type, '') = 'startup' THEN o.id END
        )::int AS startups
      FROM technology t
      LEFT JOIN document_technology dt ON dt.technology_id = t.id
      LEFT JOIN document d ON d.id = dt.document_id
      LEFT JOIN document_organization dorg ON dorg.document_id = d.id
      LEFT JOIN organization o ON o.id = dorg.organization_id
      GROUP BY t.slug, t.name
    )
    SELECT slug, name, papers, patents, grants, startups
    FROM agg
    WHERE patents > 0 AND papers <= 1
    ORDER BY patents DESC, grants DESC
    LIMIT :limit
    """
)


def _stage(papers: int, patents: int, grants: int, companies: int) -> str:
    if papers == 0 and patents == 0 and grants == 0:
        return "no_signal"
    if papers > 0 and patents == 0:
        return "research"
    if papers > 0 and patents > 0 and companies == 0:
        return "translation"
    if patents > 0 and companies > 0:
        return "commercialization"
    return "emerging"


def get_technology_linkage(db: Session, slug: str, limit: int = 10) -> TechnologyLinkageOut | None:
    tech = db.execute(_TECH_BY_SLUG, {"slug": slug}).mappings().first()
    if tech is None:
        return None

    summary_row = db.execute(_SUMMARY_COUNTS, {"tech_id": tech["id"]}).mappings().first() or {}
    papers = int(summary_row.get("papers") or 0)
    patents = int(summary_row.get("patents") or 0)
    grants = int(summary_row.get("grants") or 0)
    researchers = int(summary_row.get("researchers") or 0)
    inventors = int(summary_row.get("inventors") or 0)
    companies = int(summary_row.get("companies") or 0)

    top_inventors = db.execute(_TOP_INVENTORS, {"tech_id": tech["id"], "limit": limit}).mappings().all()
    top_companies = db.execute(_TOP_COMPANIES, {"tech_id": tech["id"], "limit": limit}).mappings().all()
    top_labs = db.execute(_TOP_LABS, {"tech_id": tech["id"], "limit": limit}).mappings().all()
    chains = db.execute(_CHAIN_SAMPLES, {"tech_id": tech["id"], "limit": limit}).mappings().all()

    return TechnologyLinkageOut(
        technology=TechnologyOut(
            id=tech["id"],
            slug=tech["slug"],
            name=tech["name"],
            category=tech["category"],
        ),
        summary=TechnologyLinkageSummary(
            papers=papers,
            patents=patents,
            grants=grants,
            researchers=researchers,
            inventors=inventors,
            companies=companies,
            commercialization_stage=_stage(papers, patents, grants, companies),
        ),
        top_inventors=[
            LinkageEntity(id=r["id"], name=r["name"], count=int(r["count"] or 0))
            for r in top_inventors
        ],
        top_companies=[
            LinkageEntity(id=r["id"], name=r["name"], count=int(r["count"] or 0))
            for r in top_companies
        ],
        top_labs=[
            LinkageEntity(id=r["id"], name=r["name"], count=int(r["count"] or 0))
            for r in top_labs
        ],
        chain_samples=[
            LinkageChainSample(
                paper_title=r["paper_title"],
                inventor=r["inventor"],
                patent_title=r["patent_title"],
                assignee=r["assignee"],
                grant_title=r["grant_title"],
                company=r["company"],
            )
            for r in chains
        ],
    )


def _to_tech_items(rows) -> list[TechnologyGapItem]:
    return [
        TechnologyGapItem(
            technology_slug=r["slug"],
            technology_name=r["name"],
            papers=int(r["papers"] or 0),
            patents=int(r["patents"] or 0),
            grants=int(r["grants"] or 0),
            startups=int(r["startups"] or 0),
        )
        for r in rows
    ]


def get_linkage_insights(db: Session, limit: int = 10) -> LinkageInsightsOut:
    moving = _to_tech_items(db.execute(_INSIGHT_LAB_TO_COMMERCIAL, {"limit": limit}).mappings().all())
    grant_gap = _to_tech_items(
        db.execute(_INSIGHT_GRANT_FEW_STARTUPS, {"limit": limit}).mappings().all()
    )
    patent_gap = _to_tech_items(
        db.execute(_INSIGHT_PATENT_LOW_ACADEMIC, {"limit": limit}).mappings().all()
    )

    professors = db.execute(_INSIGHT_PROFESSORS, {"limit": limit}).mappings().all()
    quiet = db.execute(_INSIGHT_QUIET_COMPANIES, {"limit": limit}).mappings().all()

    return LinkageInsightsOut(
        technologies_lab_to_commercialization=moving,
        professors_labs_with_patentable_work=[
            PersonInsightItem(
                person_name=r["full_name"],
                affiliation=r["affiliation"],
                paper_docs=int(r["paper_docs"] or 0),
                patent_docs=int(r["patent_docs"] or 0),
            )
            for r in professors
        ],
        quiet_patent_filers=[
            CompanyInsightItem(
                organization=r["name"],
                patent_docs=int(r["patent_docs"] or 0),
                non_patent_mentions=int(r["non_patent_mentions"] or 0),
            )
            for r in quiet
        ],
        grant_rich_startup_poor_areas=grant_gap,
        patent_rich_low_academic_areas=patent_gap,
    )
