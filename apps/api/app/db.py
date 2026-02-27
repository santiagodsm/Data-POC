import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{os.environ['PGUSER']}:{os.environ['PGPASSWORD']}"
    f"@{os.environ.get('PGHOST', 'db')}:{os.environ.get('PGPORT', '5432')}"
    f"/{os.environ['PGDATABASE']}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
