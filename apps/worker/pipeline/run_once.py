"""Run ingestion, technology tagging, then embedding once (manual / `make ingest-once`)."""

from pipeline.embed import embed_new_documents
from pipeline.ingest import run_all_connectors
from pipeline.tag import tag_documents

if __name__ == "__main__":
    ingest_result = run_all_connectors()
    print(ingest_result)
    tag_result = tag_documents()
    print(tag_result)
    embed_result = embed_new_documents()
    print(embed_result)
