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
    """手动添加新列（仅 SQLite 需要，PostgreSQL 由 create_all 处理）"""
    if not is_sqlite:
        return
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(activities)"))
        existing_cols = {row[1] for row in result}
        new_cols = {
            "is_excluded": "ALTER TABLE activities ADD COLUMN is_excluded BOOLEAN DEFAULT 0",
            "exclude_reason": "ALTER TABLE activities ADD COLUMN exclude_reason VARCHAR",
        }
        for col, sql in new_cols.items():
            if col not in existing_cols:
                conn.execute(text(sql))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
