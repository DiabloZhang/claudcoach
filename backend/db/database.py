import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# 确保 data 目录存在
os.makedirs("data", exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}  # SQLite 需要
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def run_migrations():
    """手动添加新列（SQLite 不支持 ALTER TABLE ADD COLUMN IF NOT EXISTS，需检查后添加）"""
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
