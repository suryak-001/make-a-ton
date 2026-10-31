from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost:5432/brightloop_dev"
    session_secret: str = "dev-only-secret-change-me-at-least-32-characters-long"
    session_max_age_seconds: int = 60 * 60 * 24 * 7
    cookie_secure: bool = False  # set true behind HTTPS
    frontend_url: str = "http://localhost:5173"

    # Leave smtp_host empty in dev to print emails to the server console.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    mail_from: str = "Brightloop <no-reply@brightloop.test>"


settings = Settings()
