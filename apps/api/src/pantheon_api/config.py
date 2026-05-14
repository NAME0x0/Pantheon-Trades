from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = ""
    polymarket_api_key: str = ""
    database_url: str = "postgresql+asyncpg://pantheon:pantheon@localhost:5432/pantheon"
    redis_url: str = "redis://localhost:6379"
    ipfs_api_url: str = "http://localhost:5001"
    irys_key: str = ""
    private_key: str = ""
    rpc_url: str = "https://rpc.testnet.arc.network"
    arc_chain_id: int = 5042002
    cors_origins: str = "http://localhost:3000"
    secret_key: str = "change-me-in-production"
    debug: bool = False


settings = Settings()
