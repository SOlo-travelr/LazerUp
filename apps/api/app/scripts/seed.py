"""Seed the source registry and a starter battery taxonomy."""

from sqlalchemy import select

from app.db.models import Source, Technology
from app.db.session import SessionLocal

SOURCES = [
    ("arxiv", "paper", "https://arxiv.org"),
    ("google_scholar", "paper", "https://scholar.google.com"),
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
    ("company_rss", "news", ""),
]

# Full battery value-chain taxonomy: raw-material mining -> refining ->
# materials (cathode/anode/electrolyte/separator) -> cell chemistries & formats
# -> manufacturing -> recycling/second-life -> supply chain -> applications ->
# grid storage -> management/software -> safety. Each entry carries `aliases`
# (lowercase keywords) used by the tagging stage to link documents.
# (slug, name, category, [aliases])
TAXONOMY = [
    # --- Raw materials & mining ---
    ("lithium-mining", "Lithium mining & extraction", "raw-material",
     ["lithium mining", "lithium brine", "spodumene", "lithium carbonate",
      "lithium hydroxide", "direct lithium extraction", "dle", "lithium resource"]),
    ("cobalt-supply", "Cobalt supply", "raw-material",
     ["cobalt mining", "cobalt supply", "cobalt sulfate", "drc cobalt", "cobalt sourcing"]),
    ("nickel-supply", "Nickel supply", "raw-material",
     ["nickel mining", "nickel sulfate", "class 1 nickel", "laterite nickel", "nickel supply"]),
    ("graphite-supply", "Graphite supply", "raw-material",
     ["graphite mining", "natural graphite", "synthetic graphite", "spherical graphite", "graphite supply"]),
    ("manganese-supply", "Manganese supply", "raw-material",
     ["manganese sulfate", "electrolytic manganese", "manganese supply"]),
    # --- Refining & precursors ---
    ("cathode-precursor", "Cathode active material & precursors", "refining",
     ["cathode active material", "precursor", "pcam", "cam production", "cathode powder"]),
    ("lithium-refining", "Lithium refining & conversion", "refining",
     ["lithium refining", "lithium conversion", "lithium processing", "battery-grade lithium"]),
    # --- Cathode chemistries ---
    ("nmc", "NMC cathode", "cathode",
     ["nmc", "ncm", "nickel manganese cobalt", "high-nickel cathode", "nmc811"]),
    ("nca", "NCA cathode", "cathode",
     ["nca", "nickel cobalt aluminum"]),
    ("lfp", "Lithium iron phosphate (LFP)", "cathode",
     ["lfp", "lithium iron phosphate", "lifepo4"]),
    ("lmfp", "Manganese iron phosphate (LMFP)", "cathode",
     ["lmfp", "manganese iron phosphate"]),
    ("lithium-manganese-rich", "Lithium/manganese-rich cathode", "cathode",
     ["lithium-rich", "manganese-rich", "lmr cathode", "li-rich"]),
    ("high-voltage-spinel", "High-voltage spinel (LNMO)", "cathode",
     ["lnmo", "high-voltage spinel", "5v cathode"]),
    # --- Anode materials ---
    ("silicon-anode", "Silicon anode", "anode",
     ["silicon anode", "silicon-carbon", "siox", "silicon oxide anode", "si anode"]),
    ("lithium-metal-anode", "Lithium metal anode", "anode",
     ["lithium metal anode", "li metal anode", "lithium metal battery", "anode-free"]),
    ("graphite-anode", "Graphite anode", "anode",
     ["graphite anode", "graphite electrode"]),
    ("hard-carbon-anode", "Hard carbon anode", "anode",
     ["hard carbon"]),
    ("lto-anode", "Lithium titanate (LTO) anode", "anode",
     ["lithium titanate", "lto anode"]),
    # --- Electrolytes ---
    ("solid-state-electrolyte", "Solid-state electrolyte", "electrolyte",
     ["solid-state electrolyte", "solid electrolyte", "all-solid-state"]),
    ("sulfide-electrolyte", "Sulfide solid electrolyte", "electrolyte",
     ["sulfide electrolyte", "argyrodite", "li6ps5cl", "lpscl"]),
    ("oxide-electrolyte", "Oxide solid electrolyte", "electrolyte",
     ["garnet electrolyte", "llzo", "oxide electrolyte", "nasicon"]),
    ("polymer-electrolyte", "Polymer electrolyte", "electrolyte",
     ["polymer electrolyte", "peo electrolyte"]),
    ("liquid-electrolyte", "Liquid electrolyte & additives", "electrolyte",
     ["liquid electrolyte", "carbonate electrolyte", "electrolyte additive", "fec additive"]),
    ("semi-solid-electrolyte", "Semi-solid / gel electrolyte", "electrolyte",
     ["semi-solid", "gel electrolyte", "semi solid-state"]),
    # --- Separator ---
    ("separator", "Separator", "component",
     ["battery separator", "ceramic-coated separator", "polyolefin separator"]),
    # --- Cell chemistries ---
    ("lithium-ion", "Lithium-ion battery", "chemistry",
     ["lithium-ion", "li-ion", "lithium ion battery"]),
    ("sodium-ion", "Sodium-ion battery", "chemistry",
     ["sodium-ion", "na-ion", "sodium battery"]),
    ("solid-state-battery", "Solid-state battery", "chemistry",
     ["solid-state battery", "all-solid-state battery", "assb"]),
    ("lithium-sulfur", "Lithium-sulfur battery", "chemistry",
     ["lithium-sulfur", "li-s battery", "lithium sulfur"]),
    ("lithium-air", "Lithium-air / metal-air", "chemistry",
     ["lithium-air", "li-o2", "metal-air battery"]),
    ("zinc-battery", "Zinc battery", "chemistry",
     ["zinc-ion", "zinc battery", "aqueous zinc"]),
    ("flow-battery", "Flow battery", "chemistry",
     ["flow battery", "vanadium redox", "redox flow"]),
    ("potassium-ion", "Potassium-ion battery", "chemistry",
     ["potassium-ion", "k-ion"]),
    ("magnesium-battery", "Magnesium battery", "chemistry",
     ["magnesium battery", "mg battery"]),
    ("iron-air", "Iron-air battery", "chemistry",
     ["iron-air"]),
    ("supercapacitor", "Supercapacitor", "chemistry",
     ["supercapacitor", "ultracapacitor"]),
    # --- Cell formats ---
    ("cylindrical-cell", "Cylindrical cell (4680/21700)", "cell-format",
     ["4680", "21700", "18650", "cylindrical cell"]),
    ("prismatic-cell", "Prismatic cell", "cell-format",
     ["prismatic cell", "blade battery"]),
    ("pouch-cell", "Pouch cell", "cell-format",
     ["pouch cell"]),
    # --- Manufacturing ---
    ("dry-electrode", "Dry electrode manufacturing", "manufacturing",
     ["dry electrode", "dry coating", "solvent-free electrode"]),
    ("electrode-coating", "Electrode coating & calendering", "manufacturing",
     ["slurry coating", "electrode coating", "calendering"]),
    ("cell-manufacturing", "Cell manufacturing & gigafactories", "manufacturing",
     ["gigafactory", "cell manufacturing", "battery plant", "battery factory"]),
    ("formation-aging", "Formation & aging", "manufacturing",
     ["formation process", "cell formation", "aging process"]),
    # --- Recycling & second life ---
    ("battery-recycling", "Battery recycling", "recycling",
     ["battery recycling", "black mass", "hydrometallurgy", "pyrometallurgy", "direct recycling"]),
    ("second-life", "Second-life batteries", "recycling",
     ["second-life", "second life battery", "battery repurposing"]),
    # --- Supply chain ---
    ("battery-supply-chain", "Battery supply chain", "supply-chain",
     ["battery supply chain", "critical minerals", "battery materials supply",
      "onshoring", "localization", "battery sourcing"]),
    ("battery-passport", "Battery passport & traceability", "supply-chain",
     ["battery passport", "battery traceability"]),
    # --- Applications ---
    ("ev-battery", "EV battery", "application",
     ["ev battery", "electric vehicle battery", "traction battery"]),
    ("e-mobility", "E-mobility (e-bike/scooter)", "application",
     ["e-bike battery", "e-scooter", "micromobility battery"]),
    ("aviation-battery", "Aviation & eVTOL battery", "application",
     ["electric aircraft battery", "evtol battery", "aviation battery"]),
    # --- Grid storage ---
    ("grid-storage", "Grid / stationary storage", "grid",
     ["grid storage", "bess", "energy storage system", "utility-scale storage",
      "stationary storage", "grid-scale battery"]),
    ("long-duration-storage", "Long-duration energy storage", "grid",
     ["long-duration energy storage", "ldes"]),
    # --- Management & software ---
    ("bms", "Battery management system (BMS)", "management",
     ["battery management system", "bms"]),
    ("battery-analytics", "Battery analytics & diagnostics", "management",
     ["battery analytics", "state of health", "soh estimation", "battery diagnostics"]),
    ("fast-charging", "Fast charging", "management",
     ["fast charging", "extreme fast charging", "xfc"]),
    # --- Safety ---
    ("thermal-runaway", "Thermal runaway & safety", "safety",
     ["thermal runaway", "battery fire", "battery safety", "thermal management"]),
]


def run() -> None:
    db = SessionLocal()
    try:
        for name, kind, url in SOURCES:
            exists = db.execute(select(Source).where(Source.name == name)).scalar_one_or_none()
            if not exists:
                db.add(Source(name=name, kind=kind, base_url=url or None))

        for slug, name, category, aliases in TAXONOMY:
            existing = db.execute(
                select(Technology).where(Technology.slug == slug)
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    Technology(
                        slug=slug, name=name, category=category, aliases=list(aliases)
                    )
                )
            else:
                # Keep names/categories/aliases in sync as the taxonomy evolves.
                existing.name = name
                existing.category = category
                existing.aliases = list(aliases)

        db.commit()
        print(f"Seeded {len(SOURCES)} sources and {len(TAXONOMY)} technologies.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
