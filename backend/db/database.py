import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

db_url = settings.sqlalchemy_database_url
is_sqlite = db_url.startswith("sqlite")

if is_sqlite:
    os.makedirs("data", exist_ok=True)
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(db_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def run_migrations():
    """添加新列：SQLite 需检查后添加，PostgreSQL 支持 IF NOT EXISTS"""
    with engine.connect() as conn:
        if is_sqlite:
            result = conn.execute(text("PRAGMA table_info(activities)"))
            existing_cols = {row[1] for row in result}
            new_cols = {
                "is_excluded": "ALTER TABLE activities ADD COLUMN is_excluded BOOLEAN DEFAULT 0",
                "exclude_reason": "ALTER TABLE activities ADD COLUMN exclude_reason VARCHAR",
                "tss_adjusted": "ALTER TABLE activities ADD COLUMN tss_adjusted FLOAT DEFAULT 0.0",
            }
            for col, sql in new_cols.items():
                if col not in existing_cols:
                    conn.execute(text(sql))
        else:
            # PostgreSQL 支持 IF NOT EXISTS
            migrations = [
                "ALTER TABLE activities ADD COLUMN IF NOT EXISTS is_excluded BOOLEAN DEFAULT false",
                "ALTER TABLE activities ADD COLUMN IF NOT EXISTS exclude_reason VARCHAR",
                "ALTER TABLE activities ADD COLUMN IF NOT EXISTS tss_adjusted FLOAT DEFAULT 0.0",
            ]
            for sql in migrations:
                conn.execute(text(sql))
        conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
