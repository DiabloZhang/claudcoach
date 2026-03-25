from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    strava_client_id: str
    strava_client_secret: str
    strava_redirect_uri: str = "http://localhost:8000/auth/callback"

    anthropic_api_key: str = ""

    database_url: str = "sqlite:///./data/tricoach.db"
    secret_key: str = "change_this_to_a_random_secret"
    frontend_url: str = "http://localhost:3000"

    poll_interval_minutes: int = 60  # 定时轮询间隔，可在 .env 中设置 POLL_INTERVAL_MINUTES=30

    @property
    def sqlalchemy_database_url(self) -> str:
        """Railway 提供的 DATABASE_URL 是 postgresql:// 格式，SQLAlchemy 需要 postgresql+psycopg2://"""
        url = self.database_url
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg2://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    class Config:
        env_file = "../.env"


settings = Settings()
