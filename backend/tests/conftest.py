import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import get_db

# 在导入 main 前替换 engine，避免 main.py 里的 create_all 连到真实数据库
from db import database as db_module

db_module.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_module.engine)

import db.models  # noqa: E402,F401 — 注册模型到 metadata
db_module.Base.metadata.create_all(bind=db_module.engine)
# 表创建完成后再运行列/索引迁移
db_module.run_migrations()

from main import app  # noqa: E402


@pytest.fixture
def db_session():
    """提供独立的数据库会话，每次测试后回滚"""
    connection = db_module.engine.connect()
    transaction = connection.begin()
    session = db_module.SessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """提供 FastAPI TestClient，并注入测试数据库会话"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
