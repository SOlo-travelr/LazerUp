"""Worker database access.

The worker persists ingested documents directly via SQLAlchemy Core (raw SQL)
rather than importing the API's ORM models, keeping the two deployables
decoupled while sharing one schema.
"""

import os

from sqlalchemy import create_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://bos:bos@localhost:5432/bos"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
