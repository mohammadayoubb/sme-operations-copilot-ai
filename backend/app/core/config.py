from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    secret_key: str = "change-me"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # OpenAI
    openai_api_key: str
    openai_llm_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_stt_model: str = "whisper-1"
    openai_tts_model: str = "tts-1"
    openai_tts_voice: str = "alloy"

    # Chroma
    chroma_host: str = "chromadb"
    chroma_port: int = 8000

    # Uploads
    upload_dir: str = "/app/uploads"
    max_upload_size_mb: int = 20

    # JWT Auth (single hardcoded admin — demo only)
    admin_username: str = "admin"
    admin_password: str = "soukpilot2024"
    jwt_expire_hours: int = 8

    # Twilio WhatsApp webhook (optional — leave blank to disable signature validation in dev)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = "whatsapp:+14155238886"  # Twilio sandbox default

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()
