from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALLOWLIST_PATH = PROJECT_ROOT / "config" / "allowlist.yaml"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    llm_provider: str = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_temperature: float = 0.1

    embedding_provider: str = "local"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_device: str = "cpu"
    embedding_dimensions: int = 384
    embedding_batch_size: int = 32
    chroma_collection_name: str = "mf_corpus"

    allowed_domains: str = Field(
        default=(
            "icicipruamc.com,www.icicipruamc.com,digitalfactsheet.icicipruamc.com,"
            "amfiindia.com,www.amfiindia.com,sebi.gov.in,www.sebi.gov.in,investor.sebi.gov.in"
        )
    )
    allowlist_path: Path = Field(default=DEFAULT_ALLOWLIST_PATH)

    corpus_schemes_path: Path = Field(default=PROJECT_ROOT / "corpus" / "schemes.yaml")
    vector_db_path: Path = Field(default=PROJECT_ROOT / "data" / "chroma")
    corpus_urls_path: Path = Field(default=PROJECT_ROOT / "corpus" / "urls.yaml")
    corpus_raw_path: Path = Field(default=PROJECT_ROOT / "corpus" / "raw")
    fetch_timeout_seconds: float = 60.0
    fetch_retries: int = 3
    fetch_rate_limit_seconds: float = 1.0
    # True = verify TLS (uses certifi CA bundle when installed). Set false only for local debugging.
    fetch_ssl_verify: bool = True

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    log_level: str = "INFO"

    retrieval_top_k: int = 6
    retrieval_candidate_k: int = 12
    # Calibrated for local BGE + Chroma cosine distance (typical good hits: 0.30–0.55).
    retrieval_min_score: float = 0.30
    retrieval_max_context_chars: int = 8000
    llm_max_retries: int = 2

    # Standard factual answers (type=answer)
    answer_max_sentences: int = 3
    answer_max_sentences_fund_management: int = 6
    answer_max_sentences_holdings: int = 4
    # Structured table responses (type=structured) — only when user asks for table/list-all
    structured_summary_max_sentences: int = 2
    structured_max_rows: int = 12

    # Comma-separated browser origins allowed to call the API (Vercel + local dev).
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173"
    )

    # Phase 5 — ops & security
    chat_rate_limit_per_minute: int = 30
    metrics_enabled: bool = True

    # Railway Option A — cron trigger hits POST /internal/ingest on the API (shared Chroma volume)
    enable_internal_ingest: bool = False
    ingest_trigger_secret: str = ""

    @field_validator(
        "corpus_schemes_path",
        "vector_db_path",
        "corpus_urls_path",
        "corpus_raw_path",
        "allowlist_path",
        mode="before",
    )
    @classmethod
    def resolve_path(cls, value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            return PROJECT_ROOT / path
        return path

    def allowed_domain_list(self) -> list[str]:
        env_domains = [d.strip().lower() for d in self.allowed_domains.split(",") if d.strip()]
        if env_domains:
            return sorted(set(env_domains))
        if self.allowlist_path.is_file():
            with self.allowlist_path.open(encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            domains = data.get("domains") or []
            return sorted({str(d).lower() for d in domains})
        return []

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
