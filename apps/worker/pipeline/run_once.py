"""Run all connectors once (manual / `make ingest-once`)."""

from pipeline.ingest import run_all_connectors

if __name__ == "__main__":
    result = run_all_connectors()
    print(result)
