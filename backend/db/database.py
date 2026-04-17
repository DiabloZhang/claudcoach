import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
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
            # activities 表
            result = conn.execute(text("PRAGMA table_info(activities)"))
            existing_cols = {row[1] for row in result}
            new_cols = {
                "is_excluded": "ALTER TABLE activities ADD COLUMN is_excluded BOOLEAN DEFAULT 0",
                "exclude_reason": "ALTER TABLE activities ADD COLUMN exclude_reason VARCHAR",
                "tss_adjusted": "ALTER TABLE activities ADD COLUMN tss_adjusted FLOAT DEFAULT 0.0",
                "start_date_local": "ALTER TABLE activities ADD COLUMN start_date_local DATETIME",
            }
            for col, sql in new_cols.items():
                if col not in existing_cols:
                    conn.execute(text(sql))

            # users 表
            result = conn.execute(text("PRAGMA table_info(users)"))
            existing_cols = {row[1] for row in result}
            user_cols = {
                "email": "ALTER TABLE users ADD COLUMN email VARCHAR",
                "password_hash": "ALTER TABLE users ADD COLUMN password_hash VARCHAR",
                "nickname": "ALTER TABLE users ADD COLUMN nickname VARCHAR",
                "is_active": "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1",
                "auth_provider": "ALTER TABLE users ADD COLUMN auth_provider VARCHAR DEFAULT 'password'",
                "timezone": "ALTER TABLE users ADD COLUMN timezone VARCHAR DEFAULT 'Asia/Shanghai'",
                "sleep_time": "ALTER TABLE users ADD COLUMN sleep_time VARCHAR DEFAULT '22:00'",
                "strava_athlete_id": "ALTER TABLE users ADD COLUMN strava_athlete_id INTEGER",
                "access_token": "ALTER TABLE users ADD COLUMN access_token VARCHAR",
                "refresh_token": "ALTER TABLE users ADD COLUMN refresh_token VARCHAR",
                "token_expires_at": "ALTER TABLE users ADD COLUMN token_expires_at INTEGER",
            }
            for col, sql in user_cols.items():
                if col not in existing_cols:
                    conn.execute(text(sql))
        else:
            # PostgreSQL 支持 IF NOT EXISTS
            migrations = [
                "ALTER TABLE activities ADD COLUMN IF NOT EXISTS is_excluded BOOLEAN DEFAULT false",
                "ALTER TABLE activities ADD COLUMN IF NOT EXISTS exclude_reason VARCHAR",
                "ALTER TABLE activities ADD COLUMN IF NOT EXISTS tss_adjusted FLOAT DEFAULT 0.0",
                "ALTER TABLE activities ADD COLUMN IF NOT EXISTS start_date_local TIMESTAMP",
                "ALTER TABLE coach_personas ADD COLUMN IF NOT EXISTS avatar_url VARCHAR",
                # users 表新列
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname VARCHAR",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider VARCHAR DEFAULT 'password'",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone VARCHAR DEFAULT 'Asia/Shanghai'",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS sleep_time VARCHAR DEFAULT '22:00'",
                # 注意：strava_athlete_id 等如果已存在则跳过
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS strava_athlete_id INTEGER",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS access_token VARCHAR",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS refresh_token VARCHAR",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS token_expires_at INTEGER",
            ]
            for sql in migrations:
                try:
                    conn.execute(text(sql))
                except Exception as e:
                    logging.warning(f"Migration skipped: {sql[:60]}... ({e})")
        conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
