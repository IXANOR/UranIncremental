from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables / .env file.

    Attributes:
        database_url: Async PostgreSQL connection string (asyncpg driver).
        snapshot_secret: HMAC key used to sign and verify player state snapshots.
        test_mode: When True, debug/admin endpoints are enabled.
    """

    database_url: str
    snapshot_secret: str
    test_mode: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()  # type: ignore[call-arg]
