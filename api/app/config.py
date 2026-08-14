from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://helix:helix@db:5432/helix"

    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-3.5-flash"
    gemini_embed_model: str = "gemini-embedding-2"
    embedding_dim: int = 768

    jwt_secret: str = "change-me"
    jwt_expiry_minutes: int = 480

    seed_ticket_limit: int = 300

    retrieval_top_k: int = 5
    grounding_min_score: float = 0.020

    duplicate_threshold: float = 0.88
    storm_window_minutes: int = 30
    storm_min_incidents: int = 4

    @property
    def ai_enabled(self) -> bool:
        return bool(self.gemini_api_key)


settings = Settings()
