"""Build cross-entity linkage graph from ingested documents.

Creates/updates person, organization, patent, grant_award, document_author,
document_organization and graph_edge rows so downstream analytics can follow the
chain: paper -> inventor -> patent -> assignee -> grant -> company.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text

from db import engine
from telemetry import log_event

_SELECT_DOCS = text(
    """
    SELECT id, doc_type, external_id, title, abstract, published_at, metadata
    FROM document
    """
)

_SELECT_ORG = text(
    """
    SELECT id FROM organization
    WHERE lower(name) = lower(:name)
    LIMIT 1
    """
)

_INSERT_ORG = text(
    """
    INSERT INTO organization (name, org_type, country, metadata)
    VALUES (:name, :org_type, :country, CAST(:metadata AS jsonb))
    RETURNING id
    """
)

_SELECT_PERSON = text(
    """
    SELECT id FROM person
    WHERE lower(full_name) = lower(:full_name)
      AND coalesce(lower(affiliation), '') = coalesce(lower(:affiliation), '')
    LIMIT 1
    """
)

_INSERT_PERSON = text(
    """
    INSERT INTO person (full_name, affiliation, metadata)
    VALUES (:full_name, :affiliation, CAST(:metadata AS jsonb))
    RETURNING id
    """
)

_INSERT_DOC_AUTHOR = text(
    """
    INSERT INTO document_author (document_id, person_id, position)
    VALUES (:document_id, :person_id, :position)
    ON CONFLICT DO NOTHING
    """
)

_INSERT_DOC_ORG = text(
    """
    INSERT INTO document_organization (document_id, organization_id, role)
    VALUES (:document_id, :organization_id, :role)
    ON CONFLICT DO NOTHING
    """
)

_UPSERT_PATENT = text(
    """
    INSERT INTO patent (document_id, patent_number, assignee_org, filing_date, grant_date, cpc_codes)
    VALUES (:document_id, :patent_number, :assignee_org, :filing_date, :grant_date, :cpc_codes)
    ON CONFLICT (document_id) DO UPDATE SET
      patent_number = excluded.patent_number,
      assignee_org = excluded.assignee_org,
      filing_date = coalesce(excluded.filing_date, patent.filing_date),
      grant_date = coalesce(excluded.grant_date, patent.grant_date),
      cpc_codes = coalesce(excluded.cpc_codes, patent.cpc_codes)
    """
)

_UPSERT_GRANT = text(
    """
    INSERT INTO grant_award (document_id, program, amount_usd, awardee_org, start_date, end_date)
    VALUES (:document_id, :program, :amount_usd, :awardee_org, :start_date, :end_date)
    ON CONFLICT (document_id) DO UPDATE SET
      program = coalesce(excluded.program, grant_award.program),
      amount_usd = coalesce(excluded.amount_usd, grant_award.amount_usd),
      awardee_org = coalesce(excluded.awardee_org, grant_award.awardee_org),
      start_date = coalesce(excluded.start_date, grant_award.start_date),
      end_date = coalesce(excluded.end_date, grant_award.end_date)
    """
)

_INSERT_EDGE = text(
    """
    INSERT INTO graph_edge (src_type, src_id, edge_type, dst_type, dst_id, weight, metadata)
    VALUES (:src_type, :src_id, :edge_type, :dst_type, :dst_id, :weight, CAST(:metadata AS jsonb))
    ON CONFLICT DO NOTHING
    """
)

_INFER_RESEARCH_TO_PATENT = text(
    """
    INSERT INTO graph_edge (src_type, src_id, edge_type, dst_type, dst_id, weight, metadata)
    SELECT DISTINCT
        'document', dp.id, 'research_to_patent', 'document', dpat.id,
        1.0,
        jsonb_build_object('via', 'shared_author+technology')
    FROM document dp
    JOIN document_author dap ON dap.document_id = dp.id
    JOIN document dpat ON dpat.doc_type = 'patent'
    JOIN document_author dapt ON dapt.document_id = dpat.id
        AND dapt.person_id = dap.person_id
    JOIN document_technology tp ON tp.document_id = dp.id
    JOIN document_technology tpat ON tpat.document_id = dpat.id
        AND tpat.technology_id = tp.technology_id
    WHERE dp.doc_type = 'paper'
      AND dp.id <> dpat.id
    ON CONFLICT DO NOTHING
    """
)

_INFER_TECH_TO_COMPANY = text(
    """
    INSERT INTO graph_edge (src_type, src_id, edge_type, dst_type, dst_id, weight, metadata)
    SELECT
        'technology', dt.technology_id, 'commercialized_by', 'organization', dorg.organization_id,
        COUNT(*)::real,
        jsonb_build_object('evidence_docs', COUNT(*))
    FROM document_technology dt
    JOIN document d ON d.id = dt.document_id
    JOIN document_organization dorg ON dorg.document_id = d.id
    WHERE d.doc_type IN ('patent', 'grant', 'funding', 'news')
      AND dorg.role IN ('assignee', 'awardee', 'company')
    GROUP BY dt.technology_id, dorg.organization_id
    ON CONFLICT DO NOTHING
    """
)

_INFER_TECH_TO_RESEARCHER = text(
    """
    INSERT INTO graph_edge (src_type, src_id, edge_type, dst_type, dst_id, weight, metadata)
    SELECT
        'technology', dt.technology_id, 'researched_by', 'person', da.person_id,
        COUNT(*)::real,
        jsonb_build_object('paper_docs', COUNT(*))
    FROM document_technology dt
    JOIN document d ON d.id = dt.document_id
    JOIN document_author da ON da.document_id = d.id
    WHERE d.doc_type = 'paper'
    GROUP BY dt.technology_id, da.person_id
    ON CONFLICT DO NOTHING
    """
)


def _safe_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(",", "").strip())
    except Exception:
        return None


def _infer_org_type(name: str, source: str | None = None) -> str:
    lower = name.lower()
    if source == "sbir_sttr":
        return "startup"
    if any(k in lower for k in ("university", "institute", "laboratory", "college")):
        return "academic"
    if any(k in lower for k in ("inc", "corp", "ltd", "gmbh", "llc", "co.", "company")):
        return "company"
    return "organization"


def _infer_country(name: str) -> str | None:
    lower = name.lower()
    country_map = {
        "China": ("china", "beijing", "shenzhen", "guangzhou", "hong kong"),
        "South Korea": ("korea", "seoul", "samsung", "lg energy solution", "sk on"),
        "Japan": ("japan", "tokyo", "kyoto", "osaka", "panasonic", "toyota"),
        "Germany": ("germany", "berlin", "munich", "fraunhofer", "bosch"),
        "France": ("france", "paris", "saft"),
        "United States": ("united states", "u.s.", "usa", "california", "mit", "stanford", "berkeley"),
        "Canada": ("canada", "toronto", "waterloo", "ontario"),
        "India": ("india", "iit", "bangalore", "mumbai", "new delhi"),
        "Australia": ("australia", "melbourne", "sydney", "queensland"),
        "United Kingdom": ("uk", "united kingdom", "oxford", "cambridge", "london"),
    }
    for country, keys in country_map.items():
        if any(k in lower for k in keys):
            return country
    return None


def _get_or_create_org(conn, name: str, *, source: str | None = None) -> str:
    row = conn.execute(_SELECT_ORG, {"name": name}).first()
    if row:
        return str(row[0])
    created = conn.execute(
        _INSERT_ORG,
        {
            "name": name,
            "org_type": _infer_org_type(name, source=source),
            "country": _infer_country(name),
            "metadata": "{}",
        },
    ).first()
    return str(created[0])


def _get_or_create_person(conn, full_name: str, affiliation: str | None = None) -> str:
    row = conn.execute(
        _SELECT_PERSON,
        {"full_name": full_name, "affiliation": affiliation},
    ).first()
    if row:
        return str(row[0])
    created = conn.execute(
        _INSERT_PERSON,
        {
            "full_name": full_name,
            "affiliation": affiliation,
            "metadata": "{}",
        },
    ).first()
    return str(created[0])


def _insert_edge(conn, src_type: str, src_id: str, edge_type: str, dst_type: str, dst_id: str) -> None:
    conn.execute(
        _INSERT_EDGE,
        {
            "src_type": src_type,
            "src_id": src_id,
            "edge_type": edge_type,
            "dst_type": dst_type,
            "dst_id": dst_id,
            "weight": 1.0,
            "metadata": "{}",
        },
    )


def build_linkage_graph() -> dict:
    people = 0
    orgs = 0
    doc_author_links = 0
    doc_org_links = 0
    patents = 0
    grants = 0

    with engine.begin() as conn:
        docs = conn.execute(_SELECT_DOCS).mappings().all()
        for doc in docs:
            doc_id = str(doc["id"])
            doc_type = (doc["doc_type"] or "").strip().lower()
            metadata = doc["metadata"] or {}
            source = metadata.get("source")

            authors = metadata.get("authors") or []
            for position, author in enumerate(authors):
                name = str(author).strip()
                if not name:
                    continue
                person_id = _get_or_create_person(conn, name)
                people += 1
                conn.execute(
                    _INSERT_DOC_AUTHOR,
                    {"document_id": doc_id, "person_id": person_id, "position": position},
                )
                doc_author_links += 1
                _insert_edge(conn, "document", doc_id, "authored_by", "person", person_id)

            inventors = metadata.get("inventors") or []
            for inventor in inventors:
                name = str(inventor).strip()
                if not name:
                    continue
                person_id = _get_or_create_person(conn, name)
                people += 1
                conn.execute(
                    _INSERT_DOC_AUTHOR,
                    {"document_id": doc_id, "person_id": person_id, "position": None},
                )
                doc_author_links += 1
                _insert_edge(conn, "document", doc_id, "invented_by", "person", person_id)

            assignee_names = metadata.get("assignees") or []
            primary_assignee_id = None
            for assignee_name in assignee_names:
                name = str(assignee_name).strip()
                if not name:
                    continue
                org_id = _get_or_create_org(conn, name, source=source)
                orgs += 1
                conn.execute(
                    _INSERT_DOC_ORG,
                    {"document_id": doc_id, "organization_id": org_id, "role": "assignee"},
                )
                doc_org_links += 1
                _insert_edge(conn, "document", doc_id, "assigned_to", "organization", org_id)
                if primary_assignee_id is None:
                    primary_assignee_id = org_id

            awardee = (metadata.get("awardee") or "").strip()
            awardee_org_id = None
            if awardee:
                awardee_org_id = _get_or_create_org(conn, awardee, source=source)
                orgs += 1
                conn.execute(
                    _INSERT_DOC_ORG,
                    {
                        "document_id": doc_id,
                        "organization_id": awardee_org_id,
                        "role": "awardee",
                    },
                )
                doc_org_links += 1
                _insert_edge(conn, "document", doc_id, "awarded_to", "organization", awardee_org_id)

            publisher = (metadata.get("publisher") or "").strip()
            if publisher:
                publisher_id = _get_or_create_org(conn, publisher, source=source)
                orgs += 1
                conn.execute(
                    _INSERT_DOC_ORG,
                    {
                        "document_id": doc_id,
                        "organization_id": publisher_id,
                        "role": "publisher",
                    },
                )
                doc_org_links += 1

            if doc_type == "patent":
                conn.execute(
                    _UPSERT_PATENT,
                    {
                        "document_id": doc_id,
                        "patent_number": metadata.get("patent_number") or doc.get("external_id"),
                        "assignee_org": primary_assignee_id,
                        "filing_date": doc.get("published_at"),
                        "grant_date": doc.get("published_at"),
                        "cpc_codes": metadata.get("cpc_codes"),
                    },
                )
                patents += 1

            if doc_type == "grant":
                conn.execute(
                    _UPSERT_GRANT,
                    {
                        "document_id": doc_id,
                        "program": metadata.get("program") or metadata.get("agency"),
                        "amount_usd": _safe_decimal(metadata.get("amount_usd")),
                        "awardee_org": awardee_org_id,
                        "start_date": doc.get("published_at"),
                        "end_date": None,
                    },
                )
                grants += 1

        conn.execute(_INFER_RESEARCH_TO_PATENT)
        conn.execute(_INFER_TECH_TO_COMPANY)
        conn.execute(_INFER_TECH_TO_RESEARCHER)

    result = {
        "status": "ok",
        "documents": len(docs),
        "people_processed": people,
        "organizations_processed": orgs,
        "document_author_links": doc_author_links,
        "document_org_links": doc_org_links,
        "patent_rows": patents,
        "grant_rows": grants,
    }
    log_event("processing", "linkage", "ok", "linkage graph refreshed", result)
    return result


if __name__ == "__main__":
    print(build_linkage_graph())
