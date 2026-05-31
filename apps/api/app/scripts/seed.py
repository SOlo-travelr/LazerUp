"""Seed the source registry and a starter battery taxonomy."""

from sqlalchemy import select

from app.db.models import Source, Technology
from app.db.session import SessionLocal

SOURCES = [
    ("arxiv", "paper", "https://arxiv.org"),
    ("semantic_scholar", "paper", "https://www.semanticscholar.org"),
    ("chemrxiv", "paper", "https://chemrxiv.org"),
    ("uspto_patentsview", "patent", "https://patentsview.org"),
    ("google_patents", "patent", "https://patents.google.com"),
    ("doe", "grant", "https://www.energy.gov"),
    ("arpa_e", "grant", "https://arpa-e.energy.gov"),
    ("nsf", "grant", "https://www.nsf.gov"),
    ("sbir_sttr", "grant", "https://www.sbir.gov"),
    ("crunchbase", "funding", "https://www.crunchbase.com"),
    ("techcrunch", "funding", "https://techcrunch.com"),
    ("industry_rss", "news", ""),
]

TAXONOMY = [
    ("solid-state-electrolyte", "Solid-state electrolyte", "chemistry"),
    ("sulfide-electrolyte", "Sulfide solid electrolyte", "chemistry"),
    ("lithium-metal-anode", "Lithium metal anode", "component"),
    ("sodium-ion", "Sodium-ion battery", "chemistry"),
    ("lfp", "Lithium iron phosphate", "chemistry"),
    ("silicon-anode", "Silicon anode", "component"),
    ("battery-recycling", "Battery recycling", "process"),
    ("dry-electrode", "Dry electrode manufacturing", "process"),
]


def run() -> None:
    db = SessionLocal()
    try:
        for name, kind, url in SOURCES:
            exists = db.execute(select(Source).where(Source.name == name)).scalar_one_or_none()
            if not exists:
                db.add(Source(name=name, kind=kind, base_url=url or None))

        for slug, name, category in TAXONOMY:
            exists = db.execute(
                select(Technology).where(Technology.slug == slug)
            ).scalar_one_or_none()
            if not exists:
                db.add(Technology(slug=slug, name=name, category=category))

        db.commit()
        print(f"Seeded {len(SOURCES)} sources and {len(TAXONOMY)} technologies.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
