import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Groq Settings
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", validation_alias="GROQ_MODEL")
    groq_fast_model: str = Field(default="llama-3.1-8b-instant", validation_alias="GROQ_FAST_MODEL")

    # GitHub Settings
    github_token: str = Field(default="", validation_alias="GITHUB_TOKEN")
    github_webhook_secret: str = Field(default="", validation_alias="GITHUB_WEBHOOK_SECRET")
    github_app_id: str = Field(default="", validation_alias="GITHUB_APP_ID")
    github_app_private_key_path: str = Field(default="", validation_alias="GITHUB_APP_PRIVATE_KEY_PATH")

    # Storage & DBs
    qdrant_url: str = Field(default=":memory:", validation_alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", validation_alias="QDRANT_API_KEY")
    neo4j_uri: str = Field(default="bolt://localhost:7687", validation_alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", validation_alias="NEO4J_USER")
    neo4j_password: str = Field(default="prreviewpassword", validation_alias="NEO4J_PASSWORD")
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    database_url: str = Field(default="", validation_alias="DATABASE_URL")

    # Observability
    langfuse_public_key: str = Field(default="", validation_alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", validation_alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", validation_alias="LANGFUSE_HOST")


settings = Settings()
