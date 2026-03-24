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

    class Config:
        env_file = "../.env"


settings = Settings()
